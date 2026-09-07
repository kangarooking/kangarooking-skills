"""WeChat Channels provider backed by a wx_channels_download-compatible API."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import sys
import tempfile
from pathlib import Path
from time import monotonic, strftime, time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

from media_probe import probe_video
from .safety import artifact_basename, sanitize_url


PLATFORM = "wechat_channels"
YUANBAO_PARSE_URL = "https://yuanbao.tencent.com/api/weixin/get_parse_result"
YUANBAO_HOME_URL = "https://yuanbao.tencent.com/"
CHANNELS_FEED_URL = "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
SUPPORTED_HOSTS = (
    "weixin.qq.com",
    "channels.weixin.qq.com",
    "video.weixin.qq.com",
)
AUTH_COOKIE_NAMES = frozenset({"hy_user", "hy_token", "hy_source"})
REQUIRED_AUTH_COOKIE_NAMES = frozenset({"hy_user", "hy_token"})


class YuanbaoAuthenticationError(RuntimeError):
    """Raised when Yuanbao requires a fresh user authorization."""


def supports(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return any(host == domain or host.endswith(f".{domain}") for domain in SUPPORTED_HOSTS)


def fetch(url: str, output_root: Path, *, metadata_only: bool = False, **options) -> dict:
    api_url = options.get("wechat_api_url") or os.environ.get("WX_CHANNELS_API_URL")
    api_token = options.get("wechat_api_token") or os.environ.get("WX_CHANNELS_API_TOKEN")
    cookie_path = _cookie_file_path(options.get("wechat_cookie_file"))
    auto_login = options.get("wechat_auto_login", True)
    force_login = options.get("wechat_force_login", False)
    force_download = bool(options.get("force_download", False))
    login_timeout = float(options.get("wechat_login_timeout", 300))
    cookie = "" if force_login else (os.environ.get("WX_CHANNELS_COOKIE") or "")
    if not cookie and not force_login:
        cookie = _load_cookie(cookie_path)

    if api_url:
        profile, api_method = _fetch_profile(url, api_url, api_token=api_token)
    elif cookie:
        try:
            profile = _fetch_profile_direct(url, cookie)
        except YuanbaoAuthenticationError:
            if not auto_login:
                raise
            cookie, profile, browser_cookies = _authorize_interactively(
                url,
                cookie_path,
                timeout=login_timeout,
            )
            _save_cookie(cookie_path, browser_cookies)
        api_url = YUANBAO_PARSE_URL
        api_method = "DIRECT"
    elif auto_login:
        cookie, profile, browser_cookies = _authorize_interactively(
            url,
            cookie_path,
            timeout=login_timeout,
            reset_session=force_login,
        )
        _save_cookie(cookie_path, browser_cookies)
        api_url = YUANBAO_PARSE_URL
        api_method = "DIRECT"
    else:
        raise YuanbaoAuthenticationError(
            "WeChat Channels needs Yuanbao authorization. Re-run without "
            "--no-wechat-auto-login, set WX_CHANNELS_COOKIE, or configure "
            "--wechat-api-url / WX_CHANNELS_API_URL."
        )
    feed = profile["feedInfo"]
    author_info = profile.get("authorInfo") or {}
    item_id = _item_id(url, profile)

    folder = output_root / f"wechat-channels-{item_id}"
    folder.mkdir(parents=True, exist_ok=True)

    caption = (feed.get("description") or "").strip()
    post_caption_path = folder / "post_caption.txt"
    post_caption_path.write_text(caption + ("\n" if caption else ""), encoding="utf-8")

    video_url = _select_video_url(feed)
    video_path = None
    media_probe = None
    download_method = "wx_channels_api"
    download_reused = False
    if not metadata_only:
        if not video_url:
            raise RuntimeError("WeChat Channels API response did not contain a playable video URL.")
        filename = _safe_filename(caption, author_info.get("nickname"), item_id)
        destination = folder / filename
        if not force_download:
            media_probe = _probe_reusable_video(destination)
        if media_probe:
            video_path = destination
            download_method = "wx_channels_cache"
            download_reused = True
        else:
            video_path = _download_video(video_url, destination)
            media_probe = probe_video(video_path)

    normalized = _normalize_metadata(
        source_url=url,
        api_url=api_url,
        api_method=api_method,
        profile=profile,
        item_id=item_id,
        caption=caption,
        video_url=video_url,
        video_path=video_path,
        media_probe=media_probe,
        metadata_only=metadata_only,
        download_method=download_method,
        download_reused=download_reused,
    )
    metadata_path = folder / "metadata.json"
    metadata_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "platform": PLATFORM,
        "id": item_id,
        "output_dir": str(folder),
        "video_path": str(video_path) if video_path else None,
        "post_caption_path": str(post_caption_path),
        "caption_path": str(post_caption_path),
        "metadata_path": str(metadata_path),
        "post_caption": caption,
        "caption": caption,
        "author": author_info.get("nickname"),
        "duration_seconds": (media_probe or {}).get("duration_seconds"),
        "resolution": (media_probe or {}).get("resolution"),
        "download_method": download_method,
    }


def _fetch_profile(
    share_url: str,
    api_url: str,
    *,
    api_token: str | None = None,
) -> tuple[dict, str]:
    endpoint = api_url.strip()
    if not endpoint:
        raise RuntimeError("WeChat Channels API URL cannot be empty.")

    parsed = urlparse(endpoint)
    if parsed.scheme not in ("http", "https"):
        raise RuntimeError("WeChat Channels API URL must use http or https.")

    if "{url}" in endpoint:
        request = Request(
            endpoint.replace("{url}", quote(share_url, safe="")),
            headers=_api_headers(api_token),
        )
        method = "GET"
    elif parsed.path.rstrip("/").endswith("/api/fetch_video_profile"):
        payload = json.dumps({"url": share_url}).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            headers={**_api_headers(api_token), "Content-Type": "application/json"},
            method="POST",
        )
        method = "POST"
    else:
        separator = "&" if parsed.query else "?"
        request = Request(
            f"{endpoint}{separator}{urlencode({'url': share_url})}",
            headers=_api_headers(api_token),
        )
        method = "GET"

    try:
        with urlopen(request, timeout=45) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"WeChat Channels API returned HTTP {exc.code}: {detail}"
        ) from exc
    except URLError as exc:
        hint = (
            "Start wx_channels_download with cloudflare.sphCookie configured, "
            "or set --wechat-api-url / WX_CHANNELS_API_URL to a compatible endpoint."
        )
        raise RuntimeError(
            f"Could not reach WeChat Channels API at {endpoint}. {hint}"
        ) from exc

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"WeChat Channels API returned non-JSON data: {response_text[:200]}"
        ) from exc

    profile = _unwrap_profile(payload)
    return profile, method


def _fetch_profile_direct(share_url: str, cookie: str) -> dict:
    parse_request = Request(
        YUANBAO_PARSE_URL,
        data=json.dumps(
            {"type": "video_channel_url", "url": share_url, "scene": 1}
        ).encode("utf-8"),
        headers={**_yuanbao_headers(), "Cookie": cookie},
        method="POST",
    )
    parse_payload = _request_json(parse_request, "Yuanbao share-link parser")
    if parse_payload.get("code") not in (None, 0, 200):
        code = parse_payload.get("code")
        message = str(parse_payload.get("msg") or "unknown error")
        error_type = (
            YuanbaoAuthenticationError
            if code in (401, 403) or _looks_like_auth_error(message)
            else RuntimeError
        )
        raise error_type(f"Yuanbao parser error {code}: {message}")
    parse_data = parse_payload.get("data") or {}
    playable_url = parse_data.get("playable_url")
    if not playable_url:
        raise YuanbaoAuthenticationError(
            "Yuanbao parser did not return playable_url. "
            "The Yuanbao authorization may be missing or expired."
        )

    playable_query = parse_qs(urlparse(playable_url).query)
    general_token = (playable_query.get("token") or [""])[0]
    export_id = (playable_query.get("eid") or [""])[0]
    if not export_id:
        export_id = parse_data.get("wx_export_id") or ""
    if not general_token or not export_id:
        raise RuntimeError("Yuanbao parser response is missing token or export ID.")

    rid = f"{int(time()):x}-{secrets.token_hex(4)}"
    feed_url = (
        f"{CHANNELS_FEED_URL}?_rid={rid}"
        "&_pageUrl=https:%2F%2Fchannels.weixin.qq.com%2Ffinder-preview%2Fpages%2Ffeed"
    )
    referer = (
        "https://channels.weixin.qq.com/finder-preview/pages/feed"
        "?entry_card_type=48&comment_scene=39&appid=0"
        f"&token={quote(general_token, safe='')}&entry_scene=0"
        f"&eid={quote(export_id, safe='')}"
    )
    feed_request = Request(
        feed_url,
        data=json.dumps(
            {"baseReq": {"generalToken": general_token}, "exportId": export_id}
        ).encode("utf-8"),
        headers={
            **_api_headers(),
            "Content-Type": "application/json",
            "Origin": "https://channels.weixin.qq.com",
            "Referer": referer,
        },
        method="POST",
    )
    return _unwrap_profile(_request_json(feed_request, "WeChat Channels feed API"))


def _request_json(request: Request, label: str) -> dict:
    try:
        with urlopen(request, timeout=45) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if label.startswith("Yuanbao") and exc.code in (401, 403):
            raise YuanbaoAuthenticationError(
                f"{label} requires a fresh authorization (HTTP {exc.code})."
            ) from exc
        raise RuntimeError(f"{label} returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach {label}: {exc}") from exc

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} returned non-JSON data: {response_text[:200]}") from exc


def _authorize_interactively(
    share_url: str,
    cookie_path: Path,
    *,
    timeout: float,
    reset_session: bool = False,
) -> tuple[str, dict, list[dict]]:
    if timeout <= 0:
        raise RuntimeError("Yuanbao login timeout must be greater than zero.")
    if not sys.stdin.isatty():
        raise YuanbaoAuthenticationError(
            "Interactive Yuanbao authorization requires a terminal. Run this command "
            "in Terminal, or configure WX_CHANNELS_COOKIE / WX_CHANNELS_API_URL."
        )

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Automatic Yuanbao authorization requires Playwright. Install it with "
            "`python3 -m pip install playwright`; an installed Google Chrome can be reused."
        ) from exc

    profile_dir = _browser_profile_path(cookie_path)
    profile_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    _restrict_permissions(profile_dir, 0o700)
    print(
        "No valid Yuanbao authorization was found. Opening an isolated Chrome window; "
        "finish WeChat login there and keep this command running...",
        file=sys.stderr,
    )

    deadline = monotonic() + timeout
    last_error: Exception | None = None
    last_cookie = ""
    last_probe_at = 0.0
    with sync_playwright() as playwright:
        context = None
        launch_errors = []
        for launch_options in (
            {"channel": "chrome"},
            {},
        ):
            try:
                context = playwright.chromium.launch_persistent_context(
                    str(profile_dir),
                    headless=False,
                    **launch_options,
                )
                break
            except PlaywrightError as exc:
                launch_errors.append(str(exc).splitlines()[0])
        if context is None:
            detail = "; ".join(launch_errors)
            raise RuntimeError(
                "Could not launch Chrome for Yuanbao authorization. "
                "Install Google Chrome or run `python3 -m playwright install chromium`. "
                f"Details: {detail}"
            )

        try:
            if reset_session:
                context.clear_cookies()
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(
                    YUANBAO_HOME_URL,
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
            except PlaywrightTimeoutError:
                pass
            while monotonic() < deadline:
                browser_cookies = context.cookies([YUANBAO_HOME_URL])
                auth_cookies = _authorization_cookies(browser_cookies)
                cookie = _cookie_header(auth_cookies)
                auth_names = {item["name"] for item in auth_cookies}
                now = monotonic()
                should_probe = REQUIRED_AUTH_COOKIE_NAMES <= auth_names and (
                    cookie != last_cookie or now - last_probe_at >= 10
                )
                if should_probe:
                    last_cookie = cookie
                    last_probe_at = now
                    try:
                        profile = _fetch_profile_direct(share_url, cookie)
                        print(
                            "Yuanbao authorization detected. Continuing the download...",
                            file=sys.stderr,
                        )
                        return cookie, profile, auth_cookies
                    except YuanbaoAuthenticationError as exc:
                        last_error = exc
                    except RuntimeError as exc:
                        last_error = exc
                page.wait_for_timeout(2_000)
        except KeyboardInterrupt as exc:
            raise RuntimeError("Yuanbao authorization was cancelled by the user.") from exc
        except PlaywrightError as exc:
            raise RuntimeError(
                "The Yuanbao authorization window was closed or became unavailable "
                "before login completed."
            ) from exc
        finally:
            try:
                context.close()
            except PlaywrightError:
                pass

    detail = f" Last check: {last_error}" if last_error else ""
    raise YuanbaoAuthenticationError(
        f"Timed out after {int(timeout)} seconds waiting for Yuanbao authorization.{detail}"
    )


def _cookie_file_path(configured_path: str | None = None) -> Path:
    value = configured_path or os.environ.get("WX_CHANNELS_COOKIE_FILE")
    if value:
        return Path(value).expanduser().resolve()
    config_root = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_root).expanduser() if config_root else Path.home() / ".config"
    return base / "kangarooking-skills" / "video-downloader" / "yuanbao-cookies.json"


def _browser_profile_path(cookie_path: Path) -> Path:
    configured = os.environ.get("WX_CHANNELS_BROWSER_PROFILE")
    if configured:
        return Path(configured).expanduser().resolve()
    return cookie_path.parent / "yuanbao-browser-profile"


def _load_cookie(cookie_path: Path) -> str:
    try:
        payload = json.loads(cookie_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return ""
    cookies = payload.get("cookies") if isinstance(payload, dict) else None
    return _cookie_header(cookies if isinstance(cookies, list) else [])


def _save_cookie(cookie_path: Path, cookies: list[dict]) -> None:
    cookie_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _restrict_permissions(cookie_path.parent, 0o700)
    payload = {
        "version": 1,
        "saved_at": strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cookies": _authorization_cookies(cookies),
    }
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(cookie_path.parent),
            prefix=".yuanbao-cookies-",
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
        _restrict_permissions(temp_path, 0o600)
        temp_path.replace(cookie_path)
        _restrict_permissions(cookie_path, 0o600)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _cookie_header(cookies: list[dict]) -> str:
    now = time()
    values = []
    for cookie in _authorization_cookies(cookies):
        expires = cookie.get("expires")
        if isinstance(expires, (int, float)) and expires > 0 and expires <= now:
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "")
        if name and value and all(char not in name + value for char in "\r\n;"):
            values.append(f"{name}={value}")
    return "; ".join(values)


def _authorization_cookies(cookies: list[dict]) -> list[dict]:
    selected = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        domain = str(cookie.get("domain") or "").lstrip(".").lower()
        name = str(cookie.get("name") or "")
        if domain in {"yuanbao.tencent.com", "tencent.com"} and name in AUTH_COOKIE_NAMES:
            selected.append(cookie)
    return selected


def _restrict_permissions(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        pass


def _looks_like_auth_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in ("cookie", "login", "log in", "登录", "登陆", "授权", "未登录")
    )


def _unwrap_profile(payload: dict) -> dict:
    current = payload
    for _ in range(4):
        if not isinstance(current, dict):
            break
        if isinstance(current.get("feedInfo"), dict):
            error = current.get("errMsg")
            if isinstance(error, dict) and error.get("type") not in (None, 0):
                raise RuntimeError(f"WeChat Channels feed API error: {error}")
            return current
        if current.get("code") not in (None, 0, 200):
            raise RuntimeError(
                f"WeChat Channels API error {current.get('code')}: "
                f"{current.get('msg') or current.get('error') or 'unknown error'}"
            )
        if current.get("errCode") not in (None, 0):
            raise RuntimeError(
                f"WeChat Channels feed API error {current.get('errCode')}: "
                f"{current.get('errMsg') or 'unknown error'}"
            )
        current = current.get("data")

    message = payload.get("msg") or payload.get("error") or "missing feedInfo"
    raise RuntimeError(f"Invalid WeChat Channels API response: {message}")


def _select_video_url(feed: dict) -> str | None:
    for value in (
        (feed.get("h264VideoInfo") or {}).get("videoUrl"),
        feed.get("videoUrl"),
        (feed.get("h265VideoInfo") or {}).get("videoUrl"),
        feed.get("originVideoUrl"),
    ):
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return None


def _download_video(video_url: str, destination: Path) -> Path:
    request = Request(
        video_url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://channels.weixin.qq.com/",
        },
    )
    temp_path = None
    try:
        with urlopen(request, timeout=900) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if content_type.startswith("text/") or "json" in content_type or "html" in content_type:
                raise RuntimeError(
                    f"WeChat Channels media URL returned {content_type or 'non-video content'}."
                )
            with tempfile.NamedTemporaryFile(
                "wb",
                delete=False,
                dir=str(destination.parent),
                suffix=destination.suffix,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                shutil.copyfileobj(response, temp_file)
        temp_path.replace(destination)
        if destination.stat().st_size <= 0:
            destination.unlink(missing_ok=True)
            raise RuntimeError("WeChat Channels media download produced an empty file.")
    except (HTTPError, URLError, RuntimeError) as exc:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to download WeChat Channels video: {exc}") from exc
    return destination


def _probe_reusable_video(destination: Path) -> dict | None:
    if not destination.is_file() or destination.stat().st_size <= 0:
        return None
    try:
        result = probe_video(destination)
        duration = float(result.get("duration_seconds") or 0)
    except (OSError, RuntimeError, ValueError):
        return None
    return result if duration > 0 else None


def _normalize_metadata(
    *,
    source_url: str,
    api_url: str,
    api_method: str,
    profile: dict,
    item_id: str,
    caption: str,
    video_url: str | None,
    video_path: Path | None,
    media_probe: dict | None,
    metadata_only: bool,
    download_method: str = "wx_channels_api",
    download_reused: bool = False,
) -> dict:
    feed = profile["feedInfo"]
    author = profile.get("authorInfo") or {}
    scene = profile.get("sceneInfo") or {}
    return {
        "platform": PLATFORM,
        "source_url": sanitize_url(source_url),
        "fetched_at": strftime("%Y-%m-%dT%H:%M:%S%z"),
        "id": item_id,
        "caption": caption,
        "create_time": feed.get("createtime"),
        "author": {
            "nickname": author.get("nickname"),
            "avatar": sanitize_url(author.get("headImgUrl")),
            "auth_icon": sanitize_url(author.get("authIconUrl")),
        },
        "engagement": {
            "favorites": feed.get("favCountFmt"),
            "likes": feed.get("likeCountFmt"),
            "forwards": feed.get("forwardCountFmt"),
            "comments": feed.get("commentCountFmt"),
        },
        "video": {
            "media_type": feed.get("mediaType"),
            "cover_url": sanitize_url(feed.get("coverUrl")),
            "has_playable_url": bool(video_url),
            "expired_time": scene.get("expiredTime"),
            "probe": media_probe,
        },
        "download": {
            "method": download_method,
            "reused": download_reused,
            "api_url": _redact_api_url(api_url),
            "api_method": api_method,
            "video_path": artifact_basename(video_path),
            "metadata_only": metadata_only,
        },
    }


def _item_id(source_url: str, profile: dict) -> str:
    parsed = urlparse(source_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if "sph" in path_parts:
        index = path_parts.index("sph")
        if index + 1 < len(path_parts):
            return _safe_id(path_parts[index + 1])

    query = parse_qs(parsed.query)
    for key in ("id", "nid", "eid"):
        if query.get(key):
            return _safe_id(query[key][0])

    dynamic_id = (profile.get("sceneInfo") or {}).get("dynamicExportId")
    return _safe_id(dynamic_id or "unknown")


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "unknown"


def _safe_filename(caption: str, author: str | None, item_id: str) -> str:
    first_line = caption.splitlines()[0] if caption else ""
    stem = first_line or author or item_id
    stem = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    stem = stem[:80].strip() or item_id
    return f"{stem}-{item_id}.mp4"


def _api_headers(api_token: str | None = None) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    return headers


def _yuanbao_headers() -> dict[str, str]:
    return {
        **_api_headers(),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://yuanbao.tencent.com",
        "Referer": "https://yuanbao.tencent.com/",
        "X-Requested-With": "XMLHttpRequest",
        "X-Language": "zh-CN",
        "X-Platform": "mac",
        "X-Source": "web",
        "X-Web-Third-Source": "main",
    }


def _redact_api_url(api_url: str) -> str:
    return sanitize_url(api_url) or ""


def _redact_url(value: str | None) -> str | None:
    return sanitize_url(value)

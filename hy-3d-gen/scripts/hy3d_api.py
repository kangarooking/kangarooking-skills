# -*- coding: utf-8 -*-
"""Shared helpers for HunYuan 3D generation backends."""

import json
import os
import sys
import time
from urllib import error as urlerror
from urllib import request as urlrequest


SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(SKILL_DIR, ".env")

TOKENHUB_SUBMIT_URL = "https://tokenhub.tencentmaas.com/v1/api/3d/submit"
TOKENHUB_QUERY_URL = "https://tokenhub.tencentmaas.com/v1/api/3d/query"

ALLOWED_ENV_KEYS = {
    "HY3D_OPENAI_API_KEY",
    "TENCENT_MAAS_API_KEY",
    "TOKENHUB_API_KEY",
    "TENCENTCLOUD_SECRET_ID",
    "TENCENTCLOUD_SECRET_KEY",
    "TENCENTCLOUD_TOKEN",
}

VALID_GENERATE_TYPES = ("Normal", "LowPoly", "Geometry", "Sketch")
VALID_POLYGON_TYPES = ("triangle", "quadrilateral")
VALID_RESULT_FORMATS = ("STL", "USDZ", "FBX")
VALID_MODELS = ("3.0", "3.1", "hy-3d-3.0", "hy-3d-3.1")
VALID_VIEW_TYPES = ("left", "right", "back", "top", "bottom", "left_front", "right_front")

MIN_FACE_COUNT = 3000
MAX_FACE_COUNT = 1500000
PROMPT_MAX_LENGTH = 1024

TOKENHUB_DONE = "completed"
TOKENHUB_FAILED = {"failed", "error", "cancelled", "canceled"}
TENCENT_DONE = "DONE"
TENCENT_FAILED = "FAIL"


def load_local_env():
    """Load optional skill-local credentials without overriding process env."""
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in ALLOWED_ENV_KEYS or os.getenv(key):
                continue
            os.environ[key] = value.strip().strip('"').strip("'")


def tokenhub_api_key():
    return (
        os.getenv("HY3D_OPENAI_API_KEY")
        or os.getenv("TENCENT_MAAS_API_KEY")
        or os.getenv("TOKENHUB_API_KEY")
    )


def select_provider(provider):
    if provider != "auto":
        return provider
    if tokenhub_api_key():
        return "tokenhub"
    return "tencent"


def normalize_tokenhub_model(model):
    if not model:
        return "hy-3d-3.0"
    if model == "3.0":
        return "hy-3d-3.0"
    if model == "3.1":
        return "hy-3d-3.1"
    return model


def normalize_tencent_model(model):
    if model == "hy-3d-3.0":
        return "3.0"
    if model == "hy-3d-3.1":
        return "3.1"
    return model


def _view_key_for_tokenhub(key):
    mapping = {
        "ViewType": "viewType",
        "ViewImageUrl": "viewImageUrl",
        "ViewImageBase64": "viewImageBase64",
        "view_type": "viewType",
        "view_image_url": "viewImageUrl",
        "view_image_base64": "viewImageBase64",
    }
    return mapping.get(key, key)


def _normalize_multiview_for_tokenhub(views):
    normalized = []
    for view in views:
        normalized.append({_view_key_for_tokenhub(k): v for k, v in view.items()})
    return normalized


def validate_inputs(args, for_query=False):
    if for_query:
        if args.model and args.model not in VALID_MODELS:
            return False, f"Invalid model: {args.model}, must be one of {VALID_MODELS}"
        return True, ""

    has_prompt = bool(args.prompt)
    has_image = bool(args.image_url or args.image_base64)

    if not has_prompt and not has_image:
        return False, "Must provide either --prompt or --image-url/--image-base64"
    if has_prompt and has_image and args.generate_type != "Sketch":
        return False, "Prompt and ImageUrl/ImageBase64 cannot be used together (except in Sketch mode)"
    if args.prompt and len(args.prompt) > PROMPT_MAX_LENGTH:
        return False, f"Prompt too long: {len(args.prompt)} chars, max {PROMPT_MAX_LENGTH}"
    if args.model and args.model not in VALID_MODELS:
        return False, f"Invalid model: {args.model}, must be one of {VALID_MODELS}"
    if args.generate_type and args.generate_type not in VALID_GENERATE_TYPES:
        return False, f"Invalid generate type: {args.generate_type}, must be one of {VALID_GENERATE_TYPES}"
    if normalize_tencent_model(args.model) == "3.1" and args.generate_type == "LowPoly":
        return False, "Model 3.1 does not support LowPoly generate type"
    if args.polygon_type:
        if args.polygon_type not in VALID_POLYGON_TYPES:
            return False, f"Invalid polygon type: {args.polygon_type}, must be one of {VALID_POLYGON_TYPES}"
        if args.generate_type != "LowPoly":
            return False, "PolygonType is only effective in LowPoly generate type"
    if args.face_count is not None:
        if args.face_count < MIN_FACE_COUNT or args.face_count > MAX_FACE_COUNT:
            return False, f"Face count {args.face_count} out of range [{MIN_FACE_COUNT}, {MAX_FACE_COUNT}]"
    if args.result_format and args.result_format not in VALID_RESULT_FORMATS:
        return False, f"Invalid result format: {args.result_format}, must be one of {VALID_RESULT_FORMATS}"
    if args.multi_view:
        try:
            views = json.loads(args.multi_view)
            if not isinstance(views, list):
                return False, "MultiViewImages must be a JSON array"
            for view in views:
                vt = view.get("ViewType") or view.get("view_type") or ""
                if vt not in VALID_VIEW_TYPES:
                    return False, f"Invalid ViewType: {vt}, must be one of {VALID_VIEW_TYPES}"
                if not (
                    view.get("ViewImageUrl")
                    or view.get("view_image_url")
                    or view.get("ViewImageBase64")
                    or view.get("view_image_base64")
                ):
                    return False, f"ViewImage for {vt} must have ViewImageUrl or ViewImageBase64"
        except json.JSONDecodeError:
            return False, "MultiViewImages must be valid JSON"
    return True, ""


def tokenhub_payload_from_args(args):
    payload = {"model": normalize_tokenhub_model(args.model)}
    if args.prompt:
        payload["prompt"] = args.prompt
    if args.image_url:
        payload["imageUrl"] = args.image_url
    if args.image_base64:
        payload["imageBase64"] = args.image_base64
    if args.enable_pbr:
        payload["enablePBR"] = True
    if args.face_count is not None:
        payload["faceCount"] = args.face_count
    if args.generate_type:
        payload["generateType"] = args.generate_type
    if args.polygon_type:
        payload["polygonType"] = args.polygon_type
    if args.result_format:
        payload["resultFormat"] = args.result_format
    if args.multi_view:
        views = json.loads(args.multi_view)
        payload["multiViewImages"] = _normalize_multiview_for_tokenhub(views)
    return payload


def http_post_json(url, payload, api_key):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urlerror.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = {"raw": body}
        raise RuntimeError(json.dumps({
            "provider": "tokenhub",
            "http_status": err.code,
            "detail": detail,
        }, ensure_ascii=False))
    except urlerror.URLError as err:
        raise RuntimeError(json.dumps({
            "provider": "tokenhub",
            "message": str(err),
        }, ensure_ascii=False))

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError(json.dumps({
            "provider": "tokenhub",
            "message": "Non-JSON response from TokenHub",
            "raw": body,
        }, ensure_ascii=False))


def tokenhub_submit(args):
    key = tokenhub_api_key()
    if not key:
        raise RuntimeError(json.dumps({
            "error": "CREDENTIALS_NOT_CONFIGURED",
            "message": "Set HY3D_OPENAI_API_KEY, TENCENT_MAAS_API_KEY, or TOKENHUB_API_KEY.",
        }, ensure_ascii=False))
    return http_post_json(TOKENHUB_SUBMIT_URL, tokenhub_payload_from_args(args), key)


def tokenhub_query(job_id, model):
    key = tokenhub_api_key()
    if not key:
        raise RuntimeError(json.dumps({
            "error": "CREDENTIALS_NOT_CONFIGURED",
            "message": "Set HY3D_OPENAI_API_KEY, TENCENT_MAAS_API_KEY, or TOKENHUB_API_KEY.",
        }, ensure_ascii=False))
    payload = {"model": normalize_tokenhub_model(model), "id": job_id}
    return http_post_json(TOKENHUB_QUERY_URL, payload, key)


def ensure_tencent_dependencies():
    try:
        import tencentcloud.ai3d  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        print(json.dumps({
            "error": "DEPENDENCY_NOT_INSTALLED",
            "message": (
                "tencentcloud-sdk-python is required for --provider tencent. "
                "Install it explicitly in your chosen Python environment first."
            ),
            "dependency": "tencentcloud-sdk-python",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


def tencent_client(region):
    ensure_tencent_dependencies()
    from tencentcloud.ai3d.v20250513 import ai3d_client
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile

    secret_id = os.getenv("TENCENTCLOUD_SECRET_ID")
    secret_key = os.getenv("TENCENTCLOUD_SECRET_KEY")
    token = os.getenv("TENCENTCLOUD_TOKEN")
    if not secret_id or not secret_key:
        print(json.dumps({
            "error": "CREDENTIALS_NOT_CONFIGURED",
            "message": "Set TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY for --provider tencent.",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    cred = credential.Credential(secret_id, secret_key, token) if token else credential.Credential(secret_id, secret_key)
    http_profile = HttpProfile()
    http_profile.endpoint = "ai3d.tencentcloudapi.com"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    return ai3d_client.Ai3dClient(cred, region, client_profile)


def tencent_params_from_args(args):
    params = {}
    if args.prompt:
        params["Prompt"] = args.prompt
    if args.image_url:
        params["ImageUrl"] = args.image_url
    if args.image_base64:
        params["ImageBase64"] = args.image_base64
    model = normalize_tencent_model(args.model)
    if model:
        params["Model"] = model
    if args.enable_pbr:
        params["EnablePBR"] = True
    if args.face_count is not None:
        params["FaceCount"] = args.face_count
    if args.generate_type:
        params["GenerateType"] = args.generate_type
    if args.polygon_type:
        params["PolygonType"] = args.polygon_type
    if args.result_format:
        params["ResultFormat"] = args.result_format
    if args.multi_view:
        params["MultiViewImages"] = json.loads(args.multi_view)
    return params


def tencent_submit(args):
    from tencentcloud.ai3d.v20250513 import models

    client = tencent_client(args.region)
    req = models.SubmitHunyuanTo3DProJobRequest()
    req.from_json_string(json.dumps(tencent_params_from_args(args)))
    resp = client.SubmitHunyuanTo3DProJob(req)
    return json.loads(resp.to_json_string())


def tencent_query(job_id, region):
    from tencentcloud.ai3d.v20250513 import models

    client = tencent_client(region)
    req = models.QueryHunyuanTo3DProJobRequest()
    req.from_json_string(json.dumps({"JobId": job_id}))
    resp = client.QueryHunyuanTo3DProJob(req)
    return json.loads(resp.to_json_string())


def submit(args):
    provider = select_provider(args.provider)
    if provider == "tokenhub":
        response = tokenhub_submit(args)
        return {
            "provider": provider,
            "job_id": response.get("id", ""),
            "request_id": response.get("request_id", ""),
            "model": normalize_tokenhub_model(args.model),
            "raw_status": response.get("status", ""),
            "raw": response,
        }
    response = tencent_submit(args)
    return {
        "provider": provider,
        "job_id": response.get("JobId", ""),
        "request_id": response.get("RequestId", ""),
        "model": normalize_tencent_model(args.model) or "3.0",
        "raw_status": response.get("Status", ""),
        "raw": response,
    }


def query(job_id, provider, model, region):
    provider = select_provider(provider)
    if provider == "tokenhub":
        response = tokenhub_query(job_id, model)
        return {
            "provider": provider,
            "job_id": job_id,
            "status": response.get("status", ""),
            "request_id": response.get("request_id", ""),
            "result_files": format_tokenhub_files(response.get("data")),
            "error_code": response.get("error_code") or response.get("code"),
            "error_message": response.get("error_message") or response.get("message"),
            "raw": response,
        }
    response = tencent_query(job_id, region)
    return {
        "provider": provider,
        "job_id": job_id,
        "status": response.get("Status", ""),
        "request_id": response.get("RequestId", ""),
        "result_files": format_tencent_files(response.get("ResultFile3Ds")),
        "error_code": response.get("ErrorCode"),
        "error_message": response.get("ErrorMessage"),
        "raw": response,
    }


def format_tokenhub_files(files):
    result = []
    for item in files or []:
        formatted = {
            "type": item.get("type", ""),
            "url": item.get("url", ""),
        }
        if item.get("preview_image_url"):
            formatted["preview_image_url"] = item["preview_image_url"]
        result.append(formatted)
    return result


def format_tencent_files(files):
    result = []
    for item in files or []:
        formatted = {
            "type": item.get("Type", ""),
            "url": item.get("Url", ""),
        }
        if item.get("PreviewImageUrl"):
            formatted["preview_image_url"] = item["PreviewImageUrl"]
        result.append(formatted)
    return result


def poll(job_id, provider, model, region, poll_interval, max_poll_time):
    start_time = time.time()
    provider = select_provider(provider)
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_poll_time:
            print(json.dumps({
                "error": "POLL_TIMEOUT",
                "message": f"Task {job_id} did not complete within {max_poll_time}s.",
                "provider": provider,
                "job_id": job_id,
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

        response = query(job_id, provider, model, region)
        status = response.get("status", "")
        if provider == "tokenhub":
            if status == TOKENHUB_DONE:
                return response
            if status in TOKENHUB_FAILED:
                print(json.dumps({
                    "error": "TASK_FAILED",
                    "provider": provider,
                    "job_id": job_id,
                    "status": status,
                    "error_code": response.get("error_code") or "",
                    "error_message": response.get("error_message") or "",
                    "raw": response.get("raw"),
                }, ensure_ascii=False, indent=2))
                sys.exit(1)
        else:
            if status == TENCENT_DONE:
                return response
            if status == TENCENT_FAILED:
                print(json.dumps({
                    "error": "TASK_FAILED",
                    "provider": provider,
                    "job_id": job_id,
                    "status": status,
                    "error_code": response.get("error_code") or "",
                    "error_message": response.get("error_message") or "",
                }, ensure_ascii=False, indent=2))
                sys.exit(1)

        print(
            f"[INFO] Job {job_id} provider={provider} status={status}, "
            f"elapsed={int(elapsed)}s, next poll in {poll_interval}s...",
            file=sys.stderr,
        )
        time.sleep(poll_interval)


def print_error(error, code="UNEXPECTED_ERROR"):
    message = str(error)
    try:
        detail = json.loads(message)
    except json.JSONDecodeError:
        detail = message
    print(json.dumps({
        "error": code,
        "message": detail,
    }, ensure_ascii=False, indent=2))
    sys.exit(1)

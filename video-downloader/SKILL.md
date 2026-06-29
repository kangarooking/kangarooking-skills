---
name: video-downloader
description: Download videos and extract original post captions, audio transcripts, and metadata from video platform links. Use when the user provides Douyin, Bilibili, WeChat Channels, Xiaohongshu, or YouTube links and asks to save the original video, capture the post text/caption, transcribe the spoken in-video script/copy, archive source material, or prepare video material for downstream analysis or skill creation. Douyin is implemented with an H5 primary route and yt-dlp fallback; Bilibili, YouTube, and Xiaohongshu are implemented through yt-dlp; WeChat Channels is not implemented yet and should currently be handled via the WeChat mini program kg百宝箱.
---

# Video Downloader

## Overview

Use this skill to turn a video-platform URL into a local source-material folder containing the video file, `post_caption.txt`, `audio.m4a` or `audio.mp3`, `transcript.txt`, and `metadata.json`.

Terminology:

- `post_caption.txt`: platform publish text, title, description, and hashtags.
- `transcript.txt`: spoken in-video script generated from audio ASR.
- `metadata.json`: normalized platform metadata plus download and ASR status.

The current implemented providers are Douyin, Bilibili, YouTube, and Xiaohongshu. WeChat Channels is an explicit extension point; do not claim that provider works until its provider module has been implemented and tested. For WeChat Channels links, tell the user to first use the WeChat mini program `kg百宝箱` to download the video from the 视频号 link, then continue with local ASR or downstream processing on the downloaded file.

## Quick Start

Run the bundled CLI from this skill directory:

```bash
python3 scripts/download_video.py "https://v.douyin.com/..." --output-dir ./downloads
```

For metadata/post-caption extraction without downloading the video:

```bash
python3 scripts/download_video.py "https://v.douyin.com/..." --output-dir ./downloads --metadata-only
```

For download without ASR:

```bash
python3 scripts/download_video.py "https://v.douyin.com/..." --output-dir ./downloads --asr none
```

For Chinese speech, prefer:

```bash
SILICONFLOW_API_KEY="..." python3 scripts/download_video.py "https://v.douyin.com/..." --output-dir ./downloads --asr siliconflow --asr-language Chinese
```

To bias Whisper toward domain terms or a specific script:

```bash
python3 scripts/download_video.py "https://v.douyin.com/..." --output-dir ./downloads --asr-language Chinese --asr-prompt "请使用简体中文转写。关键词：丧尸清道夫、Shotlab、Midjourney、GPT Image、AI生图。"
```

## Workflow

1. Identify the platform from the URL.
2. Use `scripts/download_video.py` as the single entrypoint.
3. Inspect the output folder and report:
   - video path, when downloaded
   - post caption path
   - audio path
   - transcript path
   - metadata path
   - platform, item ID, author, duration, resolution, and any provider caveats

## ASR Transcript

After a video is downloaded, the CLI extracts audio with `ffmpeg` and transcribes it with SiliconFlow SenseVoiceSmall or the local Whisper CLI.

Important behavior:

- `--asr auto` is the default. It uses SiliconFlow when `SILICONFLOW_API_KEY` is set, otherwise local `whisper` if installed.
- `--asr siliconflow` requires `SILICONFLOW_API_KEY` and calls `https://api.siliconflow.cn/v1/audio/transcriptions`.
- `--asr whisper` requires the local Whisper CLI.
- `--asr none` skips audio extraction and transcription.
- `--asr-model` defaults to `base` for Whisper. For SiliconFlow, `base` or `auto` maps to `FunAudioLLM/SenseVoiceSmall`.
- `--asr-language auto` lets Whisper detect language. Use `Chinese` for Chinese videos when quality matters.
- `--asr-prompt` passes an initial prompt to Whisper. Use it to request Simplified Chinese and provide domain terms.
- `base` is good for quick validation but may produce obvious Chinese homophone errors. Use `small` or `medium` for deliverable transcripts.
- SiliconFlow writes `audio.mp3`, `transcript.txt`, and `transcript.siliconflow.json`.
- Whisper writes `audio.m4a`, `transcript.txt`, and `transcript.whisper.json`.

## Douyin Provider

The Douyin provider uses the H5 share page as the primary route. It follows the share URL, parses the server-rendered `window._ROUTER_DATA`, extracts the original post text and video resource ID, then downloads through the non-`playwm` endpoint.

If the H5 route fails, or if metadata extraction succeeds but direct media download fails, use `yt-dlp` as a fallback. The fallback first tries a normal `yt-dlp` download, then retries with Chrome cookies.

Important behavior:

- Prefer the non-watermark `aweme/v1/play/` endpoint over the share-page `playwm` endpoint.
- Treat `yt-dlp` as a backup route, not the primary Douyin route.
- Store the original Douyin publish text in `post_caption.txt`.
- Store raw and normalized metadata in `metadata.json`.
- Use `--metadata-only` for fast tests or when the user only needs copy/caption.
- Use `--no-yt-dlp-fallback` only when debugging the H5 route itself.

## Bilibili Provider

The Bilibili provider uses `yt-dlp` as the primary route for both metadata extraction and media download.

Important behavior:

- Support `bilibili.com` and `b23.tv` links.
- Store the Bilibili title plus description in `post_caption.txt`.
- Store `yt-dlp` raw metadata and normalized fields in `metadata.json`.
- Download with `bv*+ba/b` and merge to mp4 when possible.
- Retry with Chrome cookies when anonymous metadata extraction or download fails.
- Use `--metadata-only` for fast tests or when the user only needs title/description metadata.

## YouTube Provider

The YouTube provider uses `yt-dlp` as the primary route for both metadata extraction and media download.

Important behavior:

- Support `youtube.com` and `youtu.be` links.
- Store the YouTube title plus description in `post_caption.txt`.
- Store `yt-dlp` raw metadata and normalized fields in `metadata.json`.
- Download with `bv*+ba/b` and merge to mp4 when possible.
- Use local Node as the yt-dlp JavaScript runtime when available.
- Retry with `--remote-components ejs:github` or Chrome cookies when the basic route fails.
- Use `--metadata-only` for fast tests or when the user only needs title/description metadata.

## Xiaohongshu Provider

The Xiaohongshu provider uses `yt-dlp` as the primary route for both metadata extraction and media download.

Important behavior:

- Support `xiaohongshu.com` and `xhslink.com` links.
- Store the Xiaohongshu title plus note body in `post_caption.txt`.
- Store `yt-dlp` raw metadata and normalized fields in `metadata.json`.
- Download with `bv*+ba/b` and merge to mp4 when possible.
- Retry with Chrome cookies when anonymous metadata extraction or download fails.
- Use `--metadata-only` for fast tests or when the user only needs title/note metadata.

## WeChat Channels Provider

WeChat Channels is recognized but not implemented yet.

Current finding:

- `yt-dlp` does not support the tested `weixin.qq.com/sph/...` share link.
- The public web page can expose text, cover image, and QR-code flow, but did not expose a playable video URL in the tested case.
- Do not claim that this skill can directly download WeChat Channels videos until a provider has been implemented and tested.

Temporary workflow:

- Ask the user to open WeChat and search for the mini program `kg百宝箱`.
- In `kg百宝箱`, paste the 视频号 video link and download the video there.
- After the user has the downloaded video file locally, this skill can still be used for local ASR/transcript work if the file is passed through the ASR helper or a future local-file entrypoint.

## Provider Extension Contract

Add new platforms by creating a module under `scripts/providers/` and registering it in `scripts/providers/__init__.py`.

Each provider should expose:

- `PLATFORM`: stable provider name
- `supports(url: str) -> bool`
- `fetch(url: str, output_root: Path, *, metadata_only: bool = False, **options) -> dict`

Output folders should include the same artifact contract whenever possible:

- `metadata.json`
- `post_caption.txt`
- `audio.m4a` and `transcript.txt` when ASR is enabled
- video file when download is enabled

Reserved providers:

- `wechat_channels`

When a reserved provider is detected but not implemented, say so plainly and do not fabricate a download result.

## Safety

Download only material the user owns, has permission to download, or can lawfully archive for their intended use. Do not bypass DRM, paid access controls, private permissions, or platform restrictions for unauthorized redistribution.

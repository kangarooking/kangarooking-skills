---
name: video-downloader
description: Download or open videos and recover platform captions, audio transcripts, keyframes, screen text, visual facts, and editing observations as a plain multimodal_transcript.md. Use for Douyin, Bilibili, YouTube, Xiaohongshu, experimental WeChat Channels links, or local video files when preparing complete source material for analysis or downstream Skill distillation.
---

# Video Downloader 2.0

## Boundary

This skill owns the complete media-preprocessing workflow:

```text
video link or local file
→ acquire video and platform caption
→ usable timed platform subtitles, otherwise cloud ASR
→ choose keyframes / full-video / Agent clips
→ preview and confirm each exact cloud payload
→ Doubao image or native-video understanding
→ timestamped plain Markdown
```

Its final handoff is `multimodal_transcript.md`, a normal text file. Cangjie Skill stays unchanged and only consumes text to produce Skills. Do not move download, ASR, frame, OCR, or visual-model logic into Cangjie Skill.

## Requirements

Required for media work:

- Python 3.10 or newer.
- `ffmpeg` and `ffprobe`.
- `yt-dlp` for Bilibili, YouTube, and Xiaohongshu; also used as a fallback on some platforms.

Optional:

- `SILICONFLOW_API_KEY` for cloud ASR.
- Local `whisper` CLI for offline ASR.
- `ARK_API_KEY` for Doubao visual understanding.
- Playwright for first-time interactive WeChat Channels authorization.

## Speed defaults and quality tradeoffs

- Bilibili, YouTube and Xiaohongshu prefer **exact 1080p** (`--download-quality 1080p`). If unavailable, download the highest available quality, even if that is 4K; this is not a resolution ceiling. Download names include the quality preference so an old 4K file cannot masquerade as a new 1080p acquisition. Other providers retain their provider-specific quality controls.
- WeChat Channels still refreshes its link profile and expiring play URL on each run, but reuses an existing destination MP4 only after it passes a media probe. Use `--force-redownload` when the platform media itself must be refreshed. `--force-reprocess` continues to mean ASR/vision result-cache bypass and does not imply a media download.
- `--asr auto` prefers usable timed platform subtitles (human-labelled before automatic). Without subtitles, use SiliconFlow. Automatic subtitles and ASR can both make mistakes: neither is inherently the most accurate for every video. Use `--no-platform-subtitles` or `--asr siliconflow` to force a fresh audio transcription.
- Cloud ASR uses approximately 60-second chunks, cuts near silence when possible, preserves all audio time, and runs at most four requests concurrently. These are audio recognition chunks, **not** the 10-minute visual chunk limit.
- Agent scene detection runs alongside speech processing at 384px / 4fps and is cached. This is a coarse selection aid, not OCR input or a complete shot inventory.
- CLI native-video concurrency defaults to four. Prepared clips use up to 720p, 12 encoded fps, fast encoding and compressed audio. Provider sampling remains 0.5fps by default; small text and fast MV cuts can still need higher sampling or dedicated keyframes.
- `--vision-thinking disabled` avoids deep-reasoning latency for Agent selection and native-video analysis. `auto` or `enabled` can be requested explicitly. This does not change keyframe image requests. Video requests allow up to 16,384 output tokens; incomplete responses are failures, not usable completed results.
- Progress identifies each processing stage and each cloud chunk. `timings.json` records actual wall-clock times and whether the run met a 600-second target. Overlapping stage times must not be summed blindly. Ten minutes is a test target, not a promise for arbitrary video lengths, networks or API queues.
- Agent selection prioritizes distinct techniques and demonstrations over repeated advertising. If the initial plan leaves source time unselected, one additional text-model request reviews omissions using the same source material; the reviewed plan is cached. The final Markdown lists unselected visual ranges. Selected-duration coverage is not information accuracy or completeness.
- Selection input supplies raw `start_ms/end_ms` to reduce time-conversion mistakes. Opening/ending fallback sentinels do not consume the ordinary candidate count; chunk splitting and sentinels can therefore produce more execution files than `--vision-max-clips`. An explicit positive total-duration budget still applies.
- Transcript cues are serialized as JSON lines with numeric milliseconds. Each initial/review text request can retry malformed JSON once with strict-format guidance; repeated failure stops selection. This bounded format retry is separate from omission review and does not silently accept a truncated response.
- A completed native-video response with invalid timestamps/time base is re-observed at most once using its existing cloud file and explicit relative bounds. The file is not re-uploaded; timestamps are not silently clamped. A second invalid answer remains a failure. The 600-second acceptance flag requires both completion and elapsed time within target.

On macOS:

```bash
brew install ffmpeg yt-dlp
python3 -m pip install playwright
```

Playwright can reuse an installed Google Chrome. If Chrome is unavailable:

```bash
python3 -m playwright install chromium
```

## Configure Doubao Vision

The visual provider uses Volcano Ark Responses API and Files API:

- Responses endpoint: `https://ark.cn-beijing.volces.com/api/v3/responses`
- Files endpoint: `https://ark.cn-beijing.volces.com/api/v3/files`
- Image/text model: `--vision-model`, used for keyframes and Agent text selection; default `doubao-seed-evolving`.
- Native-video model: `--vision-video-model`, used only for complete-video and selected-clip analysis; default `doubao-seed-evolving` after a successful non-sensitive synthetic-video smoke test on 2026-08-30.
- Credential: environment variable `ARK_API_KEY`

The two CLI parameters remain separate even though they currently share a default. Do not assume that image and native-video capability are interchangeable across every account or future model version; override `--vision-video-model` when the current account's model capability differs.

Set the key in the current terminal:

```bash
export ARK_API_KEY="replace-with-your-new-key"
```

Never put a real key in `SKILL.md`, source code, a command committed to Git, test fixtures, screenshots, or `metadata.json`.

Minimal API shape used by this skill:

```bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-evolving",
    "input": [{
      "role": "user",
      "content": [
        {"type": "input_image", "image_url": "https://example.com/frame.jpg"},
        {"type": "input_text", "text": "请描述画面中的可见事实和屏幕文字。"}
      ]
    }]
  }'
```

Local keyframes are sent as Base64 data URLs. The skill stores normalized observations, not the full provider response.

For complete-video and Agent-clip analysis, the skill creates an upload-friendly H.264 MP4 and retains a compressed AAC audio track when the source contains audio. It uploads the prepared file with `purpose=user_data`, waits until the Files API status becomes `active`, and sends `input_video + file_id` to Responses API. The upload is deleted in `finally` on a best-effort basis; a failed delete is reported rather than treated as successful cleanup. Native-video analysis complements ASR and does not replace it, because embedded-audio understanding depends on the configured video model.

Official Files API limits relevant to this workflow:

- Ark managed storage accepts each file up to 512 MB. This implementation keeps complete-video proxies below a stricter 480 MB local safety cap, streams multipart video bytes instead of loading the whole file into memory, and stops rather than uploading an oversized proxy. It does not currently split an oversized complete-video proxy automatically.
- MP4, AVI, and MOV are supported with lowercase extensions, but a supported container does not guarantee that every internal codec variant will be recognized.
- URL or Base64 video input has a separate 50 MB per-video limit; this skill uses the Files API path for prepared videos instead.
- Video preprocessing `fps` is from 0.2 to 5. `--vision-video-fps 0.5` means the Files API samples about one frame every two seconds for model input; it is not the proxy's encoded frame rate and is not frame-by-frame analysis.
- Files uploaded without an explicit expiry default to seven-day retention and may be configured for 1–30 days. This skill does not set `expire_at`; it attempts immediate deletion after analysis, but a failed deletion can leave the file in managed storage until expiry.
- The provider documents an 80k video-token ceiling for one video; the configured model's context and input limits can be lower. There is no single official “maximum minutes” value, so longer or faster-changing videos may require a lower preprocessing fps or Agent-selected clips.

Protocol references:

- [Volcano Ark video understanding](https://www.volcengine.com/docs/82379/1895586?lang=zh)
- [Volcano VEADK Responses API and Files API](https://volcengine.github.io/veadk-python/cn/docs/framework/agent/responses-api/)
- [Official Python SDK `ResponseInputVideoParam`](https://github.com/volcengine/volcengine-python-sdk/blob/master/volcenginesdkarkruntime/types/responses/response_input_video_param.py)

The supplied API key is never written to the repository, upload plan, metadata, logs, or Markdown output. If a key has ever been pasted into a chat or document, rotate it in Volcano Ark and keep only the replacement in `ARK_API_KEY`.

## Quick Start

Run from this skill directory.

A platform URL with ASR and Doubao vision:

```bash
python3 scripts/download_video.py "https://www.youtube.com/watch?v=..." \
  --output-dir ./downloads \
  --asr auto \
  --vision auto \
  --vision-mode agent-clips \
  --profile knowledge
```

When reliable timestamped ASR exists, this interactive command previews and confirms two cloud boundaries independently: first the timestamped transcript, platform caption, and scene index used for Agent selection; then the exact selected video clips. If no reliable timestamped transcript exists, selection falls back to local scene signals and only the clip upload requires confirmation. In automation, `--confirm-cloud-upload` is one up-front authorization for every Doubao stage in that run; it is not two separate human confirmations.

`--vision-plan-only` blocks Doubao visual requests only. `--asr auto` may already have sent audio to SiliconFlow when `SILICONFLOW_API_KEY` is set. Use `--asr whisper` or `--asr none` when the planning run itself must remain fully local.

A local video:

```bash
python3 scripts/download_video.py "/absolute/path/demo.mp4" \
  --output-dir ./downloads \
  --local-caption "产品演示" \
  --local-author "作者名" \
  --asr auto \
  --vision doubao \
  --vision-mode keyframes \
  --profile tech
```

Download platform text and metadata only:

```bash
python3 scripts/download_video.py "https://v.douyin.com/..." \
  --output-dir ./downloads \
  --metadata-only
```

Skip either track:

```bash
python3 scripts/download_video.py "/absolute/path/video.mp4" \
  --asr none \
  --vision doubao \
  --vision-mode keyframes
python3 scripts/download_video.py "/absolute/path/video.mp4" --vision none
python3 scripts/download_video.py "/absolute/path/video.mp4" --asr none --vision none
```

## Choose a Visual Mode

When visual analysis is enabled, the user must choose one mode. The skill must not silently decide what leaves the machine.

| Mode | What is sent | Strength | Limitation |
|---|---|---|---|
| `keyframes` | Hybrid scene/interval JPEG keyframes | Lowest token use and cost | Can miss motion and unsampled information |
| `full-video` | Compressed 720p video, split into chunks up to 10 minutes | Covers the complete source | More input; compression may lose tiny text |
| `agent-clips` | Timestamped text for selection, then bounded MP4 clips | Recommended balance | Requires two cloud stages and reliable timestamped ASR for true Agent selection |

In an interactive terminal, omitting `--vision-mode` opens a three-choice menu and recommends `agent-clips`. In a non-interactive run, omitting it exits with code 2. `--metadata-only` and `--vision none` remain exempt.

`keyframes` and `full-video` write and display `vision_plan.json` before their Doubao request. `agent-clips` first writes `vision_selection_plan.json`; only after selection and local cutting can it write the second-stage `vision_plan.json` with exact clip paths, sizes, and durations. No Doubao request occurs until the user answers `y`, or automation passes `--confirm-cloud-upload` as one up-front authorization for all Doubao stages.

Use `--vision-plan-only` to prepare all currently feasible local visual artifacts and stop before any Doubao request. In Agent mode it stops at `vision_selection_plan.json` when cloud text selection would be required, so it cannot show the exact second-stage clip plan in advance. When there is no usable timestamped text, the local scene-fallback can still cut candidates and write the exact second-stage `vision_plan.json` before stopping. This flag does not disable an earlier SiliconFlow ASR request; select local Whisper or disable ASR for a fully local planning run.

### 1. Keyframes

```bash
python3 scripts/download_video.py "/absolute/path/video.mp4" \
  --asr none \
  --vision doubao \
  --vision-mode keyframes \
  --vision-plan-only
```

The mode detects scene changes, adds fixed-interval coverage, merges nearby timestamps, caps the final set, and sends small image batches only after confirmation.

### 2. Complete video

```bash
python3 scripts/download_video.py "/absolute/path/video.mp4" \
  --asr none \
  --vision doubao \
  --vision-mode full-video \
  --vision-video-model doubao-seed-evolving \
  --vision-video-fps 0.5 \
  --vision-plan-only
```

The skill prepares H.264/AAC video without uploading the original file. Sources longer than `--vision-max-clip-seconds` (default 600) are cut directly into continuous chunks under `vision/clips/`; 25 minutes becomes 10 + 10 + 5 minutes. There is no total-duration or Agent-candidate cap in full-video mode. Shorter sources use `vision/full-video-proxy.mp4` at up to 1280×720 and 12 encoded fps. Both paths use `--vision-concurrency` (CLI default 4), per-chunk checkpoints, and source-order merging. The plan lists every prepared file and its real size/duration; valid cached results are reused rather than uploaded again. `--vision-video-fps 0.5` controls provider sampling, not encoding. A short-source proxy still has the 480 MB local cap; prepared clips are subject to the Files API size check.

### 3. Agent clips (recommended)

```bash
python3 scripts/download_video.py "/absolute/path/video.mp4" \
  --asr auto \
  --asr-language Chinese \
  --vision doubao \
  --vision-mode agent-clips \
  --vision-max-clips 8 \
  --vision-max-clip-seconds 600 \
  --vision-max-total-clip-seconds 0 \
  --vision-concurrency 4 \
  --vision-clip-padding-seconds 2
```

The selection model receives the complete timestamped transcript, platform caption, duration, and scene timestamps. It should consider silent demonstrations/B-roll and opening/ending context, not just speech. Returned ranges are validated, clamped, padded and merged. `--vision-max-clips 8` caps candidate intervals before splitting, not the number of execution chunks. The default `--vision-max-total-clip-seconds 0` adds no total-duration cap: all selected time is split into chunks up to 600 seconds, so a selected 25-minute interval becomes 10 + 10 + 5, and a 95-minute interval can produce 10 chunks. An explicit positive total budget may truncate selections; omitted ranges are reported in warnings and the final Markdown, including any lost ending. Each prepared clip retains AAC when the source has audio.

The second preview lists those exact clips before native-video analysis. Multiple clips are analyzed with bounded four-way concurrency by CLI default; progress is printed as `[current/total]`, results are restored to source order, and every clip independently uploads, analyzes, and deletes its cloud file. Use `--vision-concurrency 1` for serial processing or up to `4` when the account's rate limits allow it. `--vision-video-fps` controls provider-side frame sampling for each clip, not clip encoding or frame-by-frame inspection.

Progress distinguishes upload/preprocessing, model analysis, received-record count, and cleanup. `[i/total]` identifies the clip, not the number completed: clip 2 may finish before clip 1. Final records are sorted by original-video timestamps even if a model returns segments out of order. A provider response explicitly marked incomplete is reported as an error, even if it contains parseable JSON.

Native-video prompts ask for operation/shot-level evidence rather than a short summary: relevant buttons, parameters, filenames, visible commands, and before/after UI states. Speech alone must not be presented as visible evidence; unreadable text must not be guessed. Ten minutes is a configurable processing ceiling, not a proven accuracy threshold. For dense recordings, use a smaller `--vision-max-clip-seconds` when actual checks show missing details; do not infer accuracy from the number of output records alone. Splitting a video into two halves for concurrency testing is a manual validation strategy, not evidence that the Agent selected those boundaries.

When ASR was requested but is pending or failed, Agent mode waits for a complete speech track and does not select or upload visual clips. Rerun with the same settings to reuse successful ASR chunks and continue. This prevents a transient ASR error from triggering an unnecessary scene-only cloud pass. If the user explicitly selects `--asr none`, or a completed transcript genuinely has no segment timestamps, the mode can still fall back to scene-change candidates plus opening/ending sentinels and records `selection_method: scene-fallback`; it never pretends the Agent mapped untimed text to the video.

Useful controls:

```text
--vision auto|doubao|none
--vision-mode keyframes|full-video|agent-clips
--vision-plan-only
--confirm-cloud-upload
--vision-model doubao-seed-evolving
--vision-video-model doubao-seed-evolving
--vision-video-fps 0.5
--vision-frame-interval 10
--vision-max-frames 24
--vision-scene-threshold 0.32
--vision-batch-size 4
--vision-max-clips 8
--vision-max-clip-seconds 600
--vision-max-total-clip-seconds 0
--vision-concurrency 4
--vision-clip-padding-seconds 2
--vision-prompt "额外关注……"
--force-reprocess
```

If `ARK_API_KEY` is missing, feasible local preparation still completes: keyframes or the complete-video proxy can be created, and Agent mode can at least produce its selection plan or scene-based fallback materials where applicable. Vision status becomes `partial`, and the Markdown reports the information gap instead of pretending cloud visual analysis succeeded.

### Profiles

Choose one:

| Profile | Visual focus |
|---|---|
| `knowledge` | frameworks, slides, charts, examples, teaching demonstrations |
| `tech` | UI states, buttons, parameters, code, errors, before/after results |
| `vlog` | locations, actions, A/B-roll, emotion, environment, transitions |
| `mv` | performance, color, composition, motifs, camera movement, rhythm clues |
| `short-video` | opening hook, subtitle rhythm, reversal, CTA, shot density |

A single video can reveal visible production patterns, but it cannot prove an invisible backstage workflow. Treat all inferred workflow claims as hypotheses. For creator-style analysis, use at least 3 videos and preferably 5–10 before describing a recurring method.

## Output Contract

A completed folder can contain:

```text
downloads/<platform>-<id>/
├── video.mp4
├── post_caption.txt
├── metadata.json
├── audio.mp3 or audio.m4a
├── transcript.txt
├── transcript.segments.jsonl
├── frames/
│   └── kf-0001-0000003500.jpg
├── frames.jsonl
├── visual_notes.jsonl
├── vision_plan.json
├── vision_selection_plan.json     # Agent mode
├── clip_selection.json            # Agent mode
├── vision/
│   ├── full-video-proxy.mp4       # Complete-video mode
│   ├── full-video-proxy.manifest.json
│   ├── clips/*.mp4                # Agent mode
│   └── clips/*.manifest.json      # Source/cache identity
└── multimodal_transcript.md
```

Key files:

- `post_caption.txt`: original platform title, description, hashtags, or user-supplied local caption.
- `transcript.txt`: audio-only plain transcript.
- `transcript.segments.jsonl`: normalized segment timestamps when the ASR backend provides them.
- `platform_subtitles.json`: recovered platform subtitle text, actual cue times, language and human/automatic provenance.
- `timings.json`: stage wall-clock measurements, visual substage measurements and 600-second target result.
- `frames.jsonl`: keyframe timestamps and sampling reason.
- `visual_notes.jsonl`: visible facts, screen text, actions, shot notes, clearly separated inferences.
- `vision_plan.json`: exact files/data types, bytes, media seconds, model, limits, consent, and execution status for the visual upload.
- `vision_selection_plan.json`: first-stage transcript/caption/scene-index upload plan for Agent selection.
- `clip_selection.json`: validated ranges, reasons, scene signals, fallback state, and local clip paths.
- `*.manifest.json`: source fingerprint and encoding parameters used to prevent stale proxy/clip reuse after a source file changes at the same path.
- `multimodal_transcript.md`: the final plain-text handoff for downstream analysis or Cangjie Skill.

For video observations spanning an interval, the Markdown's accompanying speech includes all overlapping timestamped ASR segments in chronological order. Single-image observations retain point-based alignment. The full audio transcript is also preserved separately.

## ASR

`--asr auto` first uses available platform subtitle tracks, then a valid ASR checkpoint, then SiliconFlow when configured. The CLI does **not** silently start local Whisper if credentials are missing or cloud ASR fails. Supply `SILICONFLOW_API_KEY`, explicitly choose `--asr whisper`, or opt into `--allow-local-asr-fallback`. A pending/failed speech track must not be described as a complete transcript, even if visual analysis succeeds. Cloud-specific model names map to Whisper base only when local fallback was explicitly allowed; recognized Whisper model names are preserved. Explicit `--asr siliconflow` does not switch providers.

Here “platform ASR” means an existing subtitle/transcription result, not a different recognition technology: both SiliconFlow and Whisper are also ASR. The default priority is existing platform transcription → SiliconFlow → **user-approved** local Whisper (slowest). Neither the CLI nor the public `run_asr` function implicitly opts into local fallback.

If there is no usable transcription and no key, the interactive CLI asks the user to choose (1) provide a SiliconFlow key, entered without echo, or (2) run local Whisper. Non-interactive execution returns `pending`, `action_required: choose_asr_backend`, and both choices, with exit code 3; it does not launch visual requests or an unnecessary scene scan. **The calling Agent must ask the user to choose, then resume; it must not silently pick Whisper, skip speech, or claim completion.** A rejected/expired key or other cloud failure is reported; do not switch to Whisper without explicit authorization. The opt-in `--allow-local-asr-fallback` remains an explicit authorization, not a default.

### Persistent SiliconFlow configuration

The CLI preserves a nonempty `SILICONFLOW_API_KEY` already present in its environment. Otherwise it reads the literal variable from `~/.config/kangarooking-skills/video-downloader/env` (required file mode `0600`, recommended parent directory `0700`). This also works for desktop processes that do not load shell startup files. The Python loader does not execute shell content. On the owner's machine, new zsh shells source this private file via `.zshenv`; already running shell processes may need to source it or restart. Do not copy this private file into the Skill, Git, logs or test artifacts. Interactive entry alone affects the current run; persistent storage requires the user's request.

The designated model is **`FunAudioLLM/SenseVoiceSmall`**. As verified on 2026-09-07, the [official price page](https://siliconflow.cn/pricing) lists it as free; free does not mean unlimited throughput or guaranteed latency. Do not silently substitute a paid/Pro model. `--asr-model base` is a compatibility alias mapped to this model for SiliconFlow, not a request to run Whisper base.

### Resume and caches

Normal CLI reruns reuse ASR text/timestamps using the source fingerprint, requested backend/model, language, prompt and optional duration limit. Text/raw JSON/segment artifact checksums are verified before reuse. Changing the source or transcription settings, missing files or corrupted text forces reprocessing. `--asr none` explicitly disables that track; use the same ASR settings to reuse it.

Agent text selections are cached by their full selection prompt and model, then normalized again using current chunk settings. Full-video and Agent native-video results are checkpointed atomically after each successful chunk and cloud cleanup. Cache keys include prepared-file fingerprint, time context, profile/prompt, model and sampling fps. A failed chunk is not cached; reruns reuse successful chunks and retry missing/failed ones. `--force-reprocess` bypasses ASR, selection and native-video result caches; media proxy/clip fingerprints still allow safe encoding reuse. Keyframe analysis currently reruns its image batches and is not covered by the native-video checkpoint cache.

Cache locations include `asr-cache/`, `asr-chunks/`, `vision/scene-cache/`, `vision/selection-cache/`, and `vision/analysis-cache/`. Native-video checkpoints contain normalized response text, provider usage and upload/model timings but no cloud file ID or credential. Cache identity includes reasoning settings; ASR identity also includes chunk settings and cloud availability so newly configured cloud ASR does not silently reuse an old local fallback. Preview plans describe prepared candidate payloads; cached stages may issue no request, as shown by progress messages. Automatic overload/server-error retries are bounded to three attempts for Responses, cloud ASR chunks, retrieve and delete calls; file-creation POSTs and ambiguous timeouts are not automatically replayed.

Backends:

```text
--asr auto|siliconflow|whisper|none
--asr-model base
--asr-language Chinese
--asr-prompt "请使用简体中文转写。关键词：……"
--asr-chunk-seconds 60
--asr-concurrency 4
```

SiliconFlow defaults `base/auto` to `FunAudioLLM/SenseVoiceSmall`. Whisper keeps its normal model names. SiliconFlow's documented response guarantees text, not word timestamps. Parallel cloud transcription therefore labels its real audio-window ranges as `timestamp_precision: chunk`: a 60-second range is not sentence-level alignment. The renderer discloses this limitation. Platform cues retain their actual timestamps; whole-file text without timestamps remains available without fabricated alignment. Silence-scan failures fall back to continuous equal-length audio chunks. Failed cloud chunks retain successful checkpoints but mark the overall speech track incomplete.

Official references: [SiliconFlow transcription API](https://docs.siliconflow.cn/docs/api/audio-transcriptions-post), [Ark reasoning configuration](https://www.volcengine.com/docs/82379/1795150).

## WeChat Channels (Experimental)

WeChat Channels support is integrated into this skill but remains `experimental`. Mock coverage and one public share-link end-to-end validation were completed on 2026-09-07 through the saved Yuanbao-session route; that proves the tested route, not general compatibility with every account, link type or future platform change. It has three routes.

### Route 1: compatible parser API

```bash
export WX_CHANNELS_API_URL="https://your-parser.example/api/channels/parse_sph"
export WX_CHANNELS_API_TOKEN="replace-if-needed"

python3 scripts/download_video.py "https://weixin.qq.com/sph/..." \
  --output-dir ./downloads \
  --asr none \
  --vision none
```

You can also pass `--wechat-api-url`. Prefer `WX_CHANNELS_API_TOKEN` over `--wechat-api-token` so a token does not appear in shell history.

### Route 2: existing Yuanbao cookie

```bash
export WX_CHANNELS_COOKIE="hy_user=...; hy_token=..."
python3 scripts/download_video.py "https://weixin.qq.com/sph/..." \
  --asr none \
  --vision none
```

This is useful for controlled automation, but environment variables and process inspection may expose cookies. The saved-session route is preferable for routine use.

### Route 3: first-time interactive authorization

Run in a real Terminal:

```bash
python3 scripts/download_video.py "https://weixin.qq.com/sph/..." \
  --wechat-login-timeout 300 \
  --asr none \
  --vision none
```

When no valid session exists, the skill opens an isolated browser profile. Finish WeChat/Yuanbao login once; the skill validates the session, stores only `hy_user`, `hy_token`, and `hy_source`, then continues.

Default protected paths:

```text
~/.config/kangarooking-skills/video-downloader/yuanbao-cookies.json
~/.config/kangarooking-skills/video-downloader/yuanbao-browser-profile/
```

Cookie directory permissions are `0700`; the cookie file is `0600`. The skill does not read the user's normal Chrome profile.

Useful flags:

```text
--wechat-login
--no-wechat-auto-login
--wechat-login-timeout 300
--wechat-cookie-file /private/path/yuanbao-cookies.json
--wechat-api-url URL
--wechat-api-token TOKEN
--force-redownload
```

The provider refreshes metadata and the expiring play URL on every run, but a valid existing MP4 at the deterministic output path is reused by default so its ASR and visual caches remain stable. A corrupt/empty file is downloaded again. If direct parsing breaks, use `kg百宝箱` to lawfully save the video, then pass the local file to this same CLI. The ASR and visual pipeline stays identical.

## Provider Behavior

- Douyin: H5 route first, then yt-dlp fallback.
- Bilibili: yt-dlp with metadata, caption, and merged MP4 when possible.
- YouTube: yt-dlp; may use local Node, remote components, or browser cookies when needed.
- Xiaohongshu: yt-dlp with browser-cookie fallback.
- WeChat Channels: compatible API or Yuanbao authorization; experimental.
- Local file: no copy is required; the source media is probed and reused read-only.

## Failure States

- `done`: requested stage completed.
- `planned`: local artifacts and an upload plan were created, but the Doubao request was not started.
- `partial`: useful artifacts exist, but a backend or frame batch was unavailable.
- `failed`: the stage could not produce usable output.
- `skipped`: disabled by the user or not applicable.

Do not infer completion from file presence alone. Check overall `status`, `asr.status`, `vision.status`, and errors. CLI exit codes: 0 for completed or explicitly planned/skipped work, 1 for a failed requested stage (including ASR), 2 for invalid arguments/interaction, and 3 for partial/pending requested processing. ASR errors and selection coverage warnings are included in the Markdown. Native-video records require explicit finite, in-range, positive-length timestamps and observed evidence; missing timestamps, empty records and out-of-range intervals are not silently filled or counted as successful coverage.

## Safety and Privacy

- Download only material the user owns, has permission to download, or may lawfully archive.
- Do not bypass DRM, paid access, private permissions, or platform access controls.
- Temporary signed video URLs, raw WeChat API profiles, cookies, Bearer tokens, and API keys are excluded from public artifacts.
- Depending on the chosen mode, keyframes, a compressed video proxy, timestamped transcript/caption/scene timestamps, or selected clips are sent to Volcano Ark only after interactive confirmation or the non-interactive run's up-front `--confirm-cloud-upload` authorization. Agent mode has two separately previewed Doubao stages in interactive use; the automation flag pre-authorizes both. Use `--vision-plan-only` to inspect the currently available visual scope and `--vision none` for material that must never be sent to a visual provider.
- `--vision-plan-only` does not govern SiliconFlow ASR. Use local Whisper or disable ASR when no source audio or transcript may leave the machine.
- Cloud-file deletion is best-effort. Review reported cleanup errors; do not assume a failed delete removed the file before its configured expiry.
- Creator analysis may extract general methods, but should not clone a person's voice, face, copyrighted assets, or frame-by-frame creative expression without permission.

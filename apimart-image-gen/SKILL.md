---
name: apimart-image-gen
description: Generate and download images through APIMart's asynchronous GPT-Image-2 API. Use when Codex needs APIMart image generation, GPT-Image-2 text-to-image, image-to-image with reference URLs or local image files, 1k/2k/4k output, aspect-ratio control, task polling, or saving APIMart image results locally.
---

# APIMart Image Gen

Use this skill to submit GPT-Image-2 image jobs to APIMart, poll the async task result, and download returned image URLs.

## Credential Rule

Read the API key from an environment variable. Do not hardcode API keys in prompts, scripts, skill files, zip packages, commits, or shell history.

Preferred variable:

```bash
export APIMART_API_KEY="..."
```

The helper also accepts `APIMART_TOKEN` as a fallback.

## Quick Start

Use the bundled helper for normal requests:

```bash
python scripts/apimart_image_gen.py generate \
  --prompt "一只橘猫坐在窗台上看夕阳，水彩画风格" \
  --size "16:9" \
  --resolution "2k" \
  --output-dir ./outputs/apimart-image-gen
```

The script submits `POST /v1/images/generations`, waits before the first poll, queries `GET /v1/tasks/{task_id}`, and downloads completed image URLs into `--output-dir`.

## Workflows

Text-to-image:

```bash
python scripts/apimart_image_gen.py generate \
  --prompt "a corgi astronaut on the moon, cinematic" \
  --size "16:9" \
  --resolution "2k"
```

Image-to-image with public URLs:

```bash
python scripts/apimart_image_gen.py generate \
  --prompt "把参考图变成水彩画风格" \
  --image-url "https://example.com/photo.jpg" \
  --size "4:3" \
  --resolution "2k"
```

Image-to-image with local files:

```bash
python scripts/apimart_image_gen.py generate \
  --prompt "融合这些参考图，生成一张公众号封面" \
  --image-file ./reference-a.png \
  --image-file ./reference-b.jpg \
  --size "21:9" \
  --resolution "2k"
```

Check an existing task:

```bash
python scripts/apimart_image_gen.py status \
  --task-id task_01KPQ7J7DWB7QZ3WCEK3YVPBRA \
  --download \
  --output-dir ./outputs/apimart-image-gen
```

Validate request shape without calling the API:

```bash
python scripts/apimart_image_gen.py generate \
  --prompt "星空下的古老城堡" \
  --size "16:9" \
  --resolution "4k" \
  --dry-run
```

## Defaults And Limits

- Model is fixed to `gpt-image-2`.
- `n` is fixed to integer `1`; do not send `"1"` as a string.
- Valid `resolution` values are `1k`, `2k`, and `4k`.
- Valid ratio values are `auto`, `1:1`, `3:2`, `2:3`, `4:3`, `3:4`, `5:4`, `4:5`, `16:9`, `9:16`, `2:1`, `1:2`, `3:1`, `1:3`, `21:9`, and `9:21`.
- Pixel sizes such as `1881x836` or `887x1774` are also accepted.
- Up to 16 reference images can be supplied across `--image-url` and `--image-file`.
- Prefer putting aspect ratio in `--size`, not in the prompt, to avoid conflicting instructions.
- Result URLs should be downloaded promptly because APIMart reports an `expires_at` timestamp.

## Reference

Read `references/api.md` when you need endpoint details, status values, error handling, or the size/resolution map.

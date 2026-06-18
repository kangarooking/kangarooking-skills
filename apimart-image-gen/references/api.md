# APIMart GPT-Image-2 API Reference

Primary docs:

- GPT-Image-2 generation: https://docs.apimart.ai/en/api-reference/images/gpt-image-2/generation
- Task status: https://docs.apimart.ai/en/api-reference/tasks/status
- Documentation index: https://docs.apimart.ai/llms.txt

## Submit Image Job

Endpoint:

```text
POST https://api.apimart.ai/v1/images/generations
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

Body:

```json
{
  "model": "gpt-image-2",
  "prompt": "image description",
  "n": 1,
  "size": "16:9",
  "resolution": "2k",
  "image_urls": ["https://example.com/photo.jpg"],
  "official_fallback": false
}
```

Required fields are `model` and `prompt`. The model must be `gpt-image-2`. `image_urls` switches the request to image-to-image mode and accepts public image URLs or `data:image/...;base64,...` data URIs.

Successful submission:

```json
{
  "code": 200,
  "data": [
    {
      "status": "submitted",
      "task_id": "task_01KPQ7J7DWB7QZ3WCEK3YVPBRA"
    }
  ]
}
```

## Query Task

Endpoint:

```text
GET https://api.apimart.ai/v1/tasks/{task_id}?language=en
Authorization: Bearer YOUR_API_KEY
```

Completed image results are at:

```text
data.result.images[0].url[0]
```

Possible task states include `submitted`, `pending`, `processing`, `in_progress`, `completed`, `failed`, and `cancelled`.

## Sizes

Supported ratio sizes:

```text
auto, 1:1, 3:2, 2:3, 4:3, 3:4, 5:4, 4:5, 16:9, 9:16, 2:1, 1:2, 3:1, 1:3, 21:9, 9:21
```

Pixel dimensions can also be passed directly, such as `1881x836` or `887x1774`.

Resolution tiers:

```text
1k, 2k, 4k
```

## Polling

- Wait 10-20 seconds after submission before the first query.
- Poll every 3-5 seconds.
- Single-image jobs commonly finish in about 30-60 seconds, but high resolution jobs can take longer.
- Stop and surface `error.message` when status is `failed`.

## Common Errors

- `400`: invalid parameters such as unsupported `size`, unsupported `resolution`, or moderation failure.
- `401`: authentication failed.
- `402`: insufficient balance.
- `429`: rate limited.
- `500` / `503`: server or upstream service error.

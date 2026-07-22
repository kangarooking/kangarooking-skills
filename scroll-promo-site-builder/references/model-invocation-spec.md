# Direct model invocation specification

## Model binding

Required capabilities:

- Image model: `image2.0`
- Video model: `Seedance 2.0`

The agent must call these models directly through its available model tools. Tool identifiers may differ across runtimes; select by capability description and confirmed model binding, not by guessed names.

## Before calling

For every generation:

1. Save the final prompt to `assets/prompts/`.
2. Resolve and inspect all reference assets.
3. Declare each reference role: identity, style, edit target, first frame, or last frame.
4. Choose an unambiguous output filename.
5. Record a pending manifest entry.

## image2.0 calls

- Use for new images and image edits.
- Preserve approved identity and machine invariants across all calls.
- When editing, state exactly what may change and what must remain unchanged.
- Save the returned bitmap inside the project; do not leave the only copy in temporary or model-owned storage.
- Inspect subject count, identity, anatomy, text, composition, and visual continuity.

## Seedance 2.0 calls

- Default to 16:9, 720p, and no audio.
- Use image-to-video for a single approved first frame.
- Use first-and-last-frame mode for connectors and any scene requiring an exact endpoint.
- Use the smallest reference set that contains every required identity and endpoint.
- Save the returned video inside the project and record duration, dimensions, fps, and prompt path.

## Failure policy

- Retry a transient tool failure without changing the prompt.
- For a content defect, make one targeted prompt or reference correction.
- Do not silently switch models.
- If the required model is not callable, save the prompt and input manifest, report the exact missing capability, and stop that phase.

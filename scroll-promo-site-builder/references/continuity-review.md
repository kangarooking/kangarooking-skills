# Continuity review

## Evidence to inspect

For every clip, inspect:

- Stable frame near 0.15 seconds.
- Stable frame near 0.15 seconds before the end.
- Dimensions, fps, codec, pixel format, duration, and audio tracks.
- Direction of movement.
- Character, device, and output-object identity.
- Lighting, palette, and camera height.

## Boundary decision tree

1. **Frames closely match and motion agrees:** direct join.
2. **The next scene can begin from the previous tail:** regenerate or design the next scene from that actual tail; do not add a connector.
3. **A real spatial journey is missing:** generate a Seedance 2.0 connector from actual tail to actual head.
4. **Connector semantics are correct but its final pixels miss the target:** use a localized 0.3–0.6 second dissolve.
5. **Direction, identity, subject count, or narrative is wrong:** regenerate; do not hide it with a long dissolve.

## Connector requirements

- Input 1: previous rendered scene tail.
- Input 2: next rendered scene head.
- Preserve the exact recurring subjects and counts.
- Do not use original concept art as an endpoint.
- End on the target frame and hold briefly.

## Review record

Record each boundary as:

```text
from -> to | strategy | evidence paths | issue | action | status
```

Do not describe the chain as approved until the complete review video has passed decode validation and the user has confirmed it.

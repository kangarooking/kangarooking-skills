# Seedance 2.0 prompt guidelines

## Prompt structure

Write prompts in this order:

1. Reference-frame contract.
2. Duration, aspect ratio, resolution, and audio setting.
3. Identity and quantity invariants.
4. Time-coded actions.
5. Camera path.
6. Required end state.
7. Negative constraints.

## Scene prompt template

```text
Use the supplied image as the exact first-frame visual reference. Preserve [character], [device], [delivery object], palette, materials, proportions, and direction of travel.

Generate a [duration]-second, 16:9, 720p, silent, single-continuous-shot video.

0.0–X.Xs: [clear physical action]
X.X–Y.Ys: [state change]
Y.Y–end: [stable end state that supports the next scene]

Camera: [one continuous camera path].

Keep exactly [counts]. Do not add, duplicate, remove, rename, or mutate them.
No cuts, reverse camera movement, random text, subtitles, logos, watermark, extra limbs, duplicated subjects, explosions, dark cyberpunk styling, or complex HUD.
```

## First-and-last-frame prompt

- State that image 1 is the exact start and image 2 is the exact end.
- Describe the physical route between them.
- Explain how each persistent subject moves; never allow sudden disappearance.
- Settle into the end frame during the last 0.3–0.6 seconds.
- Keep one continuous direction and camera move.

## Quantity constraints

Repeat fragile counts in both the positive prompt and negative constraints. Examples: one character, one output pack, five carriages, six labeled modules.

## Text constraints

Generated video must not invent text. Exact labels belong in deterministic overlays unless a confirmed source frame already contains them.

## Retry policy

- Identity drift: strengthen reference and invariant language.
- Wrong count: simplify action and repeat counts.
- Missing endpoint: strengthen final-state timing and use first-and-last-frame mode.
- General stylistic drift: edit only style/reference lines; preserve accepted motion.

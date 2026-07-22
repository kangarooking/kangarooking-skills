# Storyboard schema

## Project-level fields

- Product and one-sentence positioning.
- Scene count and total target duration.
- Repeated character, device, route, and delivery-object invariants.
- Global style prefix and negative prompt.
- Desktop copy safe area.
- Final CTA and proof cases.

## Per-scene fields

Use this exact structure for every scene:

```markdown
## Scene NN: name

- Objective:
- Product claim:
- Duration:
- Web eyebrow:
- Web title:
- Web body:
- Tags:
- Visible subjects:
- Start state:
- Timeline:
  - 0.0–X.Xs:
  - X.X–Y.Ys:
- Camera movement:
- End state:
- First-frame requirements:
- Last-frame requirements:
- Continuity anchors:
- image2.0 prompt path:
- Seedance 2.0 prompt path:
- Negative constraints:
```

## Copy limits

- Number: `01 / 05` style.
- Eyebrow: 2–8 Chinese characters or a short phrase.
- Title: one or two lines, normally no more than 22 Chinese characters.
- Body: normally no more than 55 Chinese characters.
- Tags: zero to three, each no more than eight Chinese characters.
- Final scene: one primary CTA and at most one secondary CTA.

## Story constraints

- One scene equals one visible action.
- A claim must be demonstrated, not merely stated.
- The first scene must name or clearly identify the real input.
- Intermediate scenes must show state change.
- The final scene must show a tangible output being used or delivered.
- Generated text is never the only source of critical information; keep equivalent DOM copy.

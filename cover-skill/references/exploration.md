# Stage 1 — Four Concepts

The goal is four suitable design hypotheses, not one template in four colors.

## Canvas and files

Use 1920×1080 for all four Stage 1 concepts so comparison occurs on one fixed 16:9 canvas. Export:

- `candidate-A.png`
- `candidate-B.png`
- `candidate-C.png`
- `candidate-D.png`
- `contact-sheet.png`
- `manifest.json`

Also create these review thumbnails without replacing the full-resolution files:

- `thumbs/candidate-A-480x270.png`
- `thumbs/candidate-B-480x270.png`
- `thumbs/candidate-C-480x270.png`
- `thumbs/candidate-D-480x270.png`

Put A–D labels in the response or contact-sheet frame, not inside the individual cover artwork.

## Build four real directions

Generate each direction as an independent composition. Across the set, vary at least three meaningful axes, and ensure any pair differs substantially on at least two:

1. composition and subject placement;
2. palette, lighting, and background treatment;
3. font personality and type treatment;
4. depth and foreground/rear text relationship;
5. product, APP screenshot, or Logo integration.

Possible route families include product-native, creator-centered, UI-inspired editorial, cinematic, graphic, or playful character-led treatment. These are prompts for exploration, not permanent templates. All four directions must still fit the current product, audience, and assets.

Do not make four outputs from one layout by recoloring, swapping a texture, or moving a small icon. Do not introduce a direction solely for novelty if it conflicts with the current APP's tone.

## Constant content across A–D

- exact title and summary;
- same supplied portrait and recognizable expression intent;
- same required product and personal identity assets;
- same factual claims;
- same face exclusion and thumbnail-readability standard.

Typography can move in front of or behind the subject, but it must not cover the face. Avoid defaulting all concepts to text on one side and the person on the other.

## Recommended production order

1. Inspect the portrait, APP screenshot, Logos, and personal IP separately.
2. Record exact copy and semantic line groups before rendering.
3. Draft four layout maps and color/type rationales.
4. Generate or edit four no-copy base scenes independently.
5. Reuse the real portrait and Logos; composite exact title and summary deterministically.
6. Inspect each at full size and 480×270.
7. Create the contact sheet and manifest, then run export validation.

## Manifest minimum schema

`manifest.json` is a JSON object containing:

- `phase`: exactly `concepts`;
- `product_identity`: non-empty APP, product, or topic identity string;
- `topic_id`: canonical lowercase SHA-256 of compact sorted-key JSON containing exact `title`, exact `summary`, `product_identity`, and the sorted SHA-256 values of assets marked `topic_key: true`;
- `run_id`: non-empty unique identifier for this exploration run;
- `title` and `summary`: exact user copy as strings;
- `semantic_groups`: non-empty array of the exact title groups used for layout;
- `assets`: array of input asset records with `role`, `path`, `usage` (`required-visible` or `reference-only`), `topic_key` boolean, and actual file `sha256`; product or APP identity assets normally use `topic_key: true`, reusable personal identity assets normally use `false`;
- `contact_sheet_panels`: exactly the four candidate filenames;
- `outputs`: exactly four records with `id` A–D, `file`, file `sha256`, `width`, `height`, `font`, `line_groups`, `prompt_notes`, and a `qa` object recording copy, face, thumbnail, and required-asset checks.

## Response at the selection gate

Show A, B, C, and D individually. Give each a one-sentence rationale covering its composition and current-theme fit. State any known limitation. Ask the user to select one; do not select on their behalf or generate five ratios yet.

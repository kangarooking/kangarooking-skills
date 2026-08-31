# Stage 1 — Four Concepts

The goal is four suitable design hypotheses, not one template in four colors.

## Canvas and files

All four Stage 1 concepts use the same resolved target so comparison remains fair. Resolve it before layout using this strict priority: explicit ratio, explicit platform, then generic `16:9` only when neither was supplied.

| `stage1_target.key` | Ratio | Full size | Review thumbnail |
|---|---:|---:|---:|
| `wechat` | 21:9 | 2100×900 | 420×180 |
| `bilibili` | 16:9 | 1920×1080 | 480×270 |
| `douyin` | 9:16 | 1080×1920 | 270×480 |
| `landscape-4x3` | 4:3 | 1600×1200 | 400×300 |
| `portrait-3x4` | 3:4 | 1200×1600 | 360×480 |
| `generic-16x9` | 16:9 | 1920×1080 | 480×270 |

Platform aliases include 公众号/微信/WeChat, B站/Bilibili, and 抖音/Douyin. A request for a 公众号封面 therefore yields four 2100×900 candidates and four 420×180 review thumbnails. Do not generate 16:9 candidates first and call later adaptation sufficient.

Export:

- `candidate-A.png`
- `candidate-B.png`
- `candidate-C.png`
- `candidate-D.png`
- `contact-sheet.png`
- `manifest.json`
- `qa-review.md`

Also create review thumbnails without replacing the full-resolution files. Insert the resolved thumbnail dimensions in each filename:

- `thumbs/candidate-A-<width>x<height>.png`
- `thumbs/candidate-B-<width>x<height>.png`
- `thumbs/candidate-C-<width>x<height>.png`
- `thumbs/candidate-D-<width>x<height>.png`

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
- same visually approved portrait-expression master derived from the supplied portrait;
- only visually approved integrated portrait-pet master(s), derived from that expression master and the raw IP identity reference;
- same required product and personal identity assets;
- the same topic-driven expression class (`surprised`, `questioning`, or `surprised-questioning`);
- a pet kangaroo naturally bearing weight on the creator's shoulder or head, with believable paws/body occlusion, contact shadow, and cloth or hair compression;
- same factual claims;
- same face exclusion and thumbnail-readability standard.

Typography can move in front of or behind the subject, but it must not cover the face. Avoid defaulting all concepts to text on one side and the person on the other.

## Recommended production order

1. Inspect the portrait, APP screenshot, Logos, and personal IP separately.
2. Record exact copy, semantic line groups, and the topic-driven portrait expression before rendering.
3. Create one identity-preserving portrait-expression master, then inspect it with `view_image`. Reject a neutral or identity-drifted master before any layout work.
4. Generate one or two integrated portrait-pet masters—`shoulder` and/or `head`—from the approved expression master plus the raw IP as character reference. Inspect every master with `view_image`. Reject any cropped/pasted original pose, free-standing body, floating gap, face obstruction, absent paw/body support, implausible occlusion, missing contact shadow/compression, or mismatched light/perspective.
5. Draft four layout maps and color/type rationales. For the owner's covers, also record subject anchor, selected pet-master hash and pose, physical-contact evidence, text-subject depth plan, and Logo integration; all four concepts must be centered or center-weighted.
6. Generate or edit four no-copy base scenes independently.
7. Reuse only the approved integrated portrait-pet master(s) and real Logos; composite exact title and summary deterministically. Never add the raw `IP-logo` bitmap as a separate layer.
8. Inspect every candidate at full size and at the resolved target review size using `view_image`; do not substitute code-only pixel checks.
9. Create the contact sheet, manifest, and `qa-review.md` per-concept PASS/FAIL table, then run export validation. Never infer visual PASS from manifest booleans alone.

## Manifest minimum schema

`manifest.json` is a JSON object containing:

- `phase`: exactly `concepts`;
- `stage1_target`: object with exactly `key`, `ratio`, and `origin`. `key` is one target key from the table above, `ratio` matches that row, and `origin` is exactly `explicit-platform`, `explicit-ratio`, or `default`; `default` is valid only for `generic-16x9`;
- `personal_signature_applies`: exactly `true`;
- `product_logo_required`: boolean; set `true` whenever a real product Logo is supplied or discoverable;
- `product_identity`: non-empty APP, product, or topic identity string;
- `topic_id`: canonical lowercase SHA-256 of compact sorted-key JSON containing exact `title`, exact `summary`, `product_identity`, and the sorted SHA-256 values of assets marked `topic_key: true`;
- `run_id`: non-empty unique identifier for this exploration run;
- `title` and `summary`: exact user copy as strings;
- `semantic_groups`: non-empty array of the exact title groups used for layout;
- `assets`: array of input asset records with `role`, `path`, `usage` (`required-visible` or `reference-only`), `topic_key` boolean, and actual file `sha256`; product or APP identity assets normally use `topic_key: true`, reusable personal identity assets normally use `false`;
- `contact_sheet_panels`: exactly the four candidate filenames;
- `portrait_expression_master`: object containing its `path`, actual `sha256`, and the shared `expression_intent`;
- `pet_companion_masters`: non-empty array of approved combined-subject records. Each has `pose` (`shoulder` or `head`), `path`, actual `sha256`, `source_portrait_sha256`, `source_ip_sha256`, `integration_method` exactly `generated-integrated`, and non-empty `generation_notes`;
- `outputs`: exactly four records with `id` A–D, `file`, file `sha256`, `width`, `height`, `font`, `line_groups`, `prompt_notes`, `expression_intent`, `subject_anchor`, `mascot_relationship`, `pet_pose`, `pet_master_sha256`, `pet_contact_evidence`, `text_subject_integration`, `logo_integration`, and a `qa` object. `pet_contact_evidence` has exact non-empty string keys `support_surface`, `paws_or_body_occlusion`, `contact_shadow_or_compression`, and `lighting_perspective_match`. The exact QA boolean keys are `copy_checked`, `face_safe`, `thumbnail_readable`, `required_assets_visible`, `portrait_expression_checked`, `mascot_integrated`, `pet_pose_natural_checked`, `pet_contact_checked`, `no_sticker_treatment_checked`, `text_subject_integrated`, `product_logo_integrated`, and `personal_signature_checked`.

## Response at the selection gate

Show A, B, C, and D individually. Give each a one-sentence rationale covering its composition and current-theme fit. State any known limitation. Ask the user to select one; do not select on their behalf or generate five ratios yet.

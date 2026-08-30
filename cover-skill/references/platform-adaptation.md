# Stage 2 — Five Responsive Ratios

Stage 2 starts after the user selects a current-topic concept, or explicitly supplies an existing selected source and requests adaptation.

## Content invariants

Across all five versions, preserve:

- title and summary character for character, including punctuation and English capitalization;
- portrait, expression, personal IP or mascot, product image, APP identity, and real Logos;
- the selected concept's palette family, font personality, hierarchy, depth, and visual story.

“Content unchanged” permits only responsive line breaks, position, scale, spacing, and non-critical background crop or expansion. It never permits deleting the summary, abbreviating the title, changing `Cli` to `CLI`, replacing punctuation, inventing words, or regenerating the face or Logo.

## Native outputs

Export these files at the default dimensions:

| Platform | Ratio | Size | Filename |
|---|---:|---:|---|
| WeChat | 21:9 | 2100×900 | `cover-wechat-21x9.png` |
| Bilibili | 16:9 | 1920×1080 | `cover-bilibili-16x9.png` |
| Douyin | 9:16 | 1080×1920 | `cover-douyin-9x16.png` |
| Landscape | 4:3 | 1600×1200 | `cover-landscape-4x3.png` |
| Portrait | 3:4 | 1200×1600 | `cover-portrait-3x4.png` |

Also export `platform-contact-sheet.png`, `manifest.json`, and these QA thumbnails:

- `thumbs/cover-wechat-21x9-420x180.png`
- `thumbs/cover-bilibili-16x9-480x270.png`
- `thumbs/cover-douyin-9x16-270x480.png`
- `thumbs/cover-landscape-4x3-400x300.png`
- `thumbs/cover-portrait-3x4-360x480.png`

## Manifest minimum schema

`manifest.json` is a JSON object containing:

- `phase`: exactly `selected`;
- `product_identity`, `topic_id`, and `run_id`: exactly the values from the selected Stage 1 run;
- `title` and `summary`: exact user copy as strings;
- `semantic_groups`: non-empty array of the exact title groups;
- `source_concept_id`: selected A–D concept, `external`, or `custom`;
- `parent_concept_ids`: for `custom`, the unique A–D concepts used to build the revised master;
- `source_run_id`: Stage 1 run ID, or the external/custom source identifier;
- `source_path`: selected or revised master path;
- `source_sha256`: actual SHA-256 of the selected source file;
- `assets`: array of input asset records with `role`, `path`, `usage`, `topic_key`, and file `sha256`;
- `contact_sheet_panels`: exactly the five platform output filenames;
- `outputs`: exactly five records with `platform`, `file`, file `sha256`, `width`, `height`, `font`, `line_groups`, `layout_notes`, and a `qa` object recording copy, face, thumbnail, required-asset, and native-recomposition checks.

For a pure A–D selection, `source_path` must resolve to the matching `concepts/candidate-<ID>.png`, and validation must receive that Stage 1 `manifest.json`. For a revised or mixed master from the current run, use `custom`, retain the current topic/run IDs, record its parent concept IDs plus revised master path and SHA-256, and also validate against the Stage 1 manifest; only the exact candidate-path constraint is skipped. For a direct external source, use `external`, create a new adaptation topic/run ID, verify the external source path and SHA-256, and omit the Stage 1 manifest.

## Reconstruction method

Treat the chosen concept as a design system and source-layer reference, not a bitmap to stretch or crop.

1. Rebuild or extend the background at the target canvas.
2. Reuse the same portrait cutout whenever possible; move and rescale it without changing identity.
3. Reframe the APP screenshot or product layer without distortion or loss of its key recognizable feature.
4. Reflow semantic title groups for the new width and height.
5. Re-render exact text and Logos at native resolution.
6. Rebuild rear/subject/front layer relationships and the face exclusion mask.
7. Inspect the native output and a target-sized thumbnail.

Generative expansion is acceptable for non-critical background or scene texture. Do not use it to redraw the face, exact UI copy, or Logos.

## Ratio-specific guidance

### 21:9 WeChat

Compress vertical stacking and use horizontal rhythm. Prefer one or two title rows when legible. Keep critical copy and identity away from fragile extreme-edge crops.

### 16:9 Bilibili

Use the selected concept's balanced master composition, with room for title hierarchy, subject, and APP identity at thumbnail scale.

### 9:16 Douyin

Create a true vertical composition. Re-stack title groups around the upper and middle subject; do not crop a horizontal master. Keep platform-overlay-sensitive areas conservative—especially the right edge and lower portion—while retaining all copy and identity assets.

### 4:3 landscape

Reduce lateral whitespace and rebalance text around the subject. Protect the head, shoulders, Logo, and product screenshot from edge loss.

### 3:4 portrait

Use a vertical reflow with deliberate top-to-bottom hierarchy. Retain the summary at a readable size and keep the selected concept recognizable.

## Consistency boundary

The five outputs should clearly belong to one selected concept. This lock ends with the current topic. The next new title or APP reference begins a fresh four-direction exploration unless the user explicitly requests continuity.

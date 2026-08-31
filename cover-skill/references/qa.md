# Mandatory QA

Passing file checks is necessary but not sufficient. Use `view_image` for full-size, thumbnail, portrait-master, and cross-ratio visual review. Do not mark QA from code, coordinates, or manifest values alone.

## Stage 1 gate

- Exactly four individual candidate files exist, plus a contact sheet and manifest.
- The identity-preserving portrait-expression master was visually inspected before layout and matches the recorded emotion; a neutral or identity-drifted master fails.
- All four use the exact title, summary, punctuation, and English capitalization.
- A–D are meaningfully different; they are not one template recolored.
- The title is the first hierarchy and immediately readable at the resolved target review size.
- The summary is secondary but remains readable with deliberate attention at the resolved target review size.
- Line breaks follow semantic groups; no mid-word split, hanging punctuation, or strange one-character orphan appears.
- No text, Logo, or decoration covers the eyes, eyebrows, nose, mouth, glasses, or central face area.
- Any hair, shoulder, arm, mascot, or product overlap leaves every affected glyph unmistakable.
- Portrait, personal IP, APP screenshot, and Logos remain recognizable and undistorted.
- For the owner's covers, the portrait expression clearly reads as surprised, questioning, or surprised-questioning according to the recorded intent; a neutral presenter face fails.
- The kangaroo looks like a pet naturally lying or crawling on the creator's shoulder or head. Its paws/chest/body visibly bear weight; useful occlusion, contact shadow, cloth or hair compression, matched perspective, and matched light prove the contact.
- The raw source IP has not been cropped, keyed, resized, or pasted into the cover. A positionally correct but independently pasted/full-body mascot, visible ground feet or tail, floating gap, sticker outline, rectangular edge, or independent platform fails.
- All four concepts are centered or center-weighted. Internal asymmetry may vary, but a generic text-left/person-right split fails.
- Title, portrait, kangaroo, and product subject share deliberate front/rear depth. A large isolated text panel plus unrelated stickers fails.
- The product Logo is large enough to recognize and integrated into the subject, title lockup, product object, or a deliberate branded module; a tiny automatic corner badge fails.
- The summary remains clearly readable at the resolved target review size, normally with about 11–13 px or greater CJK glyph height.
- No gibberish, duplicated characters, fake Logo, invented function, or extra marketing claim is present.
- Each concept fits the current theme and reference assets.
- Delivery stops for A–D selection.
- `qa-review.md` records one row per candidate with explicit PASS/FAIL for copy, expression, face safety, natural pet pose, physical contact, no pasted source, centered anchor, text-depth integration, product-Logo integration, and target-thumbnail readability. Every row must be PASS before delivery.

## Stage 2 gate

- Exactly five ratio files exist at the expected dimensions, plus a platform contact sheet and manifest.
- Each output preserves the exact title, summary, punctuation, capitalization, portrait, product, and Logos.
- All five inherit the selected concept's visual identity.
- Every ratio has a deliberate native composition; no output is a stretched image or blind center crop.
- Face exclusion, glyph recognizability, Logo fidelity, product visibility, and edge safety pass independently for every ratio.
- APP and portrait layers are not distorted, accidentally cut, or regenerated inconsistently.
- Portrait expression, pet-master identity and pose, physical support/contact evidence, center-weighted subject logic, text-subject depth, and Logo integration remain recognizable in every ratio.
- Neither the portrait nor kangaroo is separated or reduced to a detached sticker merely to fit a narrow ratio; the raw source IP never appears as a composited layer.
- The 9:16 and 3:4 versions are genuine vertical reflows and retain the summary.
- Text is readable both at full resolution and at realistic platform thumbnail or phone-feed size.
- `qa-review.md` records the same hard gates for each ratio after full-size and thumbnail inspection; every row must be PASS.

## Standard `qa-review.md` table

Use these exact English column names so export validation and human review share one contract:

| Output | Overall | Exact copy | Expression | Face safe | Pet pose natural | Pet contact | No pasted source | Center anchor | Text depth | Product Logo | Thumbnail readability |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `candidate-A.png` | PASS | PASS | PASS | PASS | PASS - shoulder | PASS - paws drape, torso occluded, contact shadow | PASS | PASS | PASS | PASS | PASS |

Replace the example filename with every required output. Each row must contain eleven `PASS` values: one `Overall` result plus the ten hard-gate columns. A row with fewer than eleven PASS values, any FAIL value, a missing output, the wrong number/order of columns, or a missing exact column name fails export validation. Ratio outputs use the same table and their native filenames.

## Copy verification

Run OCR only as a warning aid; manually compare the visible title and summary against the original character by character. Ignore only compositor whitespace introduced around visual line breaks. Spaces present in the user's original copy remain significant. Do not ignore punctuation, capitalization, repeated characters, or omissions.

## Export validation

Run:

```bash
python3 <cover-skill-dir>/scripts/validate_exports.py --phase concepts --dir <concepts-dir>
python3 <cover-skill-dir>/scripts/validate_exports.py --phase selected --dir <selected-dir> --source-manifest <concepts-dir>/manifest.json
```

Use `--source-manifest` for A–D and revised current-run `custom` masters. Omit it only for a direct `external` source; the validator still checks that external path and SHA-256.

The validator checks required files, readable PNGs, manifest JSON, pixel dimensions, approved pet-master paths/hashes/source binding, output-to-master pose/hash binding, structured contact evidence, and whether `qa-review.md` includes the exact `Overall` plus ten hard-gate columns with eleven PASS values for every output. It cannot independently judge whether the depicted contact is visually believable, or fully judge semantic line breaks, contrast, face safety, content fidelity, or design quality; inspect those manually before writing the report.

If any hard gate fails, revise before showing the output as final.

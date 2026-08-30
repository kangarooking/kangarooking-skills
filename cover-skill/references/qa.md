# Mandatory QA

Passing file checks is necessary but not sufficient. Perform full-size, thumbnail, and cross-ratio visual review.

## Stage 1 gate

- Exactly four individual candidate files exist, plus a contact sheet and manifest.
- All four use the exact title, summary, punctuation, and English capitalization.
- A–D are meaningfully different; they are not one template recolored.
- The title is the first hierarchy and immediately readable at 480×270.
- The summary is secondary but remains readable with deliberate attention at 480×270.
- Line breaks follow semantic groups; no mid-word split, hanging punctuation, or strange one-character orphan appears.
- No text, Logo, or decoration covers the eyes, eyebrows, nose, mouth, glasses, or central face area.
- Any hair, shoulder, arm, mascot, or product overlap leaves every affected glyph unmistakable.
- Portrait, personal IP, APP screenshot, and Logos remain recognizable and undistorted.
- No gibberish, duplicated characters, fake Logo, invented function, or extra marketing claim is present.
- Each concept fits the current theme and reference assets.
- Delivery stops for A–D selection.

## Stage 2 gate

- Exactly five ratio files exist at the expected dimensions, plus a platform contact sheet and manifest.
- Each output preserves the exact title, summary, punctuation, capitalization, portrait, product, and Logos.
- All five inherit the selected concept's visual identity.
- Every ratio has a deliberate native composition; no output is a stretched image or blind center crop.
- Face exclusion, glyph recognizability, Logo fidelity, product visibility, and edge safety pass independently for every ratio.
- APP and portrait layers are not distorted, accidentally cut, or regenerated inconsistently.
- The 9:16 and 3:4 versions are genuine vertical reflows and retain the summary.
- Text is readable both at full resolution and at realistic platform thumbnail or phone-feed size.

## Copy verification

Run OCR only as a warning aid; manually compare the visible title and summary against the original character by character. Ignore only compositor whitespace introduced around visual line breaks. Spaces present in the user's original copy remain significant. Do not ignore punctuation, capitalization, repeated characters, or omissions.

## Export validation

Run:

```bash
python3 <cover-skill-dir>/scripts/validate_exports.py --phase concepts --dir <concepts-dir>
python3 <cover-skill-dir>/scripts/validate_exports.py --phase selected --dir <selected-dir> --source-manifest <concepts-dir>/manifest.json
```

Use `--source-manifest` for A–D and revised current-run `custom` masters. Omit it only for a direct `external` source; the validator still checks that external path and SHA-256.

The validator checks required files, readable PNGs, manifest JSON, and pixel dimensions. It cannot judge semantic line breaks, contrast, face safety, content fidelity, or design quality; inspect those manually.

If any hard gate fails, revise before showing the output as final.

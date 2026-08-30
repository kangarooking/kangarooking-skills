---
name: shijing-paper-zine
description: Transform ordinary snapshots—including daily moments, portraits, objects, pets, food, interiors, streets, architecture, landscapes, travel, and humanistic scenes—into the restrained Shijing Paper Zine visual style. Use when the user wants any real photo turned into a spacious paper-editorial composition with an irregular photographic fragment, simplified source-derived drawing, one structural print color, tactile torn-paper texture, minimal micro-copy, a consistent multi-image series, or a source-to-poster comparison.
---

# 拾景纸刊

Turn an ordinary photograph into a quiet editorial page. Treat this as a visual style rather than a travel-photo format. Read the scene before choosing a treatment. Preserve the relationship that makes the photograph specific; remove visual noise before adding design.

## Required input

Use one user-supplied or properly licensed photograph per poster. Accept casual phone snapshots, daily life, portraits, objects, pets, food, interiors, landscape, architecture, street, travel, and humanistic scenes.

If the user supplies several photographs, treat them as a series only when they share a place, time, subject, relationship, mood, or narrative. Otherwise process them as independent posters.

## Preset style references

- Inspect [example-landscape.png](assets/example-landscape.png) to calibrate paper whitespace and photographic share in open scenes.
- Inspect [example-urban.png](assets/example-urban.png) to calibrate urban structure, eye direction, and structural color.
- Inspect [example-humanity.png](assets/example-humanity.png) to calibrate the preserved relationship between people and their environment.
- Inspect [example-cover.png](assets/example-cover.png) to calibrate fragment hierarchy and consistency for a multi-image cover.
- Treat these files as visual-language references only. Do not copy their landmarks, people, layouts, wording, or travel subject matter into a new result.
- Derive every new composition from the user's source photograph and Scene Note. The examples must not narrow this style to travel images.

## Choose the fidelity mode first

### Pixel-preserving mode

Use when faces, products, signs, artworks, or documentary truth must remain exact.

- Keep the original photograph unchanged as a placed canvas element.
- Build paper, drawing, color, text, and torn boundaries around or across its edge.
- Do not ask a generative model to recreate identity-critical content.

### Generative reconstruction mode

Use only when the user accepts reinterpretation or the scene has no identity-critical detail.

- Send the photograph as visual reference.
- Warn internally that people, buildings, objects, and text may be reconstructed.
- Avoid claiming pixel-level preservation in the delivery.
- Prefer back views, distant figures, landscapes, and architecture without critical signage.

Default to pixel-preserving mode when the request is ambiguous and the available canvas supports direct compositing.

## Build a Scene Note

Before generating, resolve six visible decisions:

1. **Anchor:** the one subject or fragment that must remain recognizable.
2. **Relationship:** the distance, overlap, direction, scale, or near/far tension that makes this scene particular.
3. **Eye path:** the line that carries attention through the image—shoreline, road, gaze, railing, skyline, tree trunk, or repeated objects.
4. **Quiet field:** sky, water, wall, ground, haze, or another low-information area that can become paper.
5. **Compression target:** crowds, windows, foliage, cages, signs, gravel, waves, or other repeated detail that must be merged or removed.
6. **Color source:** one meaningful hue or object from the photograph that can become structural color.

Do not start from a style label. Start from these scene facts.

## Compose the poster

- Use a vertical 3:4 canvas by default; use the user's requested ratio when supplied.
- Keep roughly 30–45% photographic material and 40–60% quiet paper.
- Use one irregular photographic anchor instead of a centered rectangular photo.
- Continue one source direction across the photo–paper boundary.
- Use one primary drawing grammar: sparse contour, broad silhouette, dry-print field, or cut-paper mass.
- Remove 60–85% of small descriptive detail. Dense scenes require fewer, larger marks.
- Use warm cream or neutral fibrous paper unless the source demands another restrained paper tone.
- Keep the result flat and scan-like. Avoid mockup depth.

Read [scene-routing.md](references/scene-routing.md) and choose the route for everyday objects, portraits, interiors, food, landscapes, urban scenes, or humanistic photographs.

## Use one structural color

Choose one saturated print hue from a real visual cue in the photograph.

The color must do at least two jobs:

- touch or cross the photographic anchor;
- continue a source contour or direction;
- rebalance visual weight;
- connect separated fragments;
- establish entry, movement, or exit;
- clarify figure and ground.

If removing the hue does not weaken the composition, redesign it. Do not park a colored rectangle, circle, or brush mark in an empty corner.

For a multi-poster series, each poster may use a different hue, but paper, drawing grammar, text scale, and edge behavior must remain consistent.

## Build the material boundary

- Use an uneven hand-torn edge where photography becomes paper.
- Show narrow fibers, local abrasion, broken pigment, and natural variation.
- Keep the boundary flat; no cast shadow, curled corner, sticker outline, or thick layered-paper depth.
- Let drawing or structural color cross selected edge segments so the two fields belong to one composition.

## Add micro-copy only when it helps

- Use no text, or one short line.
- Prefer one to five English words or no more than eight Chinese characters.
- Use typewriter, dry letterpress, pencil, or quiet handwriting.
- Place it in genuine breathing room as the final stop in the eye path.
- Reproduce user-supplied wording exactly.
- Do not add dates, coordinates, barcodes, archive numbers, logos, CTAs, fake credits, or magazine metadata unless requested.

## Compile the generation prompt

Write four compact sections:

1. **Format and hierarchy:** ratio, photographic share, quiet-paper share, focal area, and eye path.
2. **Scene facts:** anchor, relationship, direction, and content that must remain.
3. **Translation:** what becomes drawing, what disappears, exact structural hue, edge behavior, and optional micro-copy.
4. **Hard constraints:** fidelity mode, flat paper reproduction, legibility, and prohibited aesthetics.

Describe visible decisions, not design theory. State what must disappear as clearly as what must remain.

## Series workflow

For a three-image series:

1. Choose one image with an open or quiet field.
2. Choose one image with a strong direction, object arrangement, or spatial rhythm.
3. Choose one image with a human, emotional, or daily-life relationship.
4. Build a separate Scene Note for each.
5. Keep canvas, paper tone, drawing family, text scale, and material treatment consistent.
6. Give each poster one source-derived structural hue.
7. Create one cover from three unequal fragments; do not use a grid or three equal thumbnails.
8. Deliver the cover, individual posters, original-to-result comparisons, and a one-paragraph method summary.

## Correction loop

Inspect once at full size and once as a thumbnail. Make one targeted revision only.

- If the result looks like a filter, reduce transformed photography and enlarge quiet paper.
- If the result looks empty, extend one source-derived contour or color field; do not add filler.
- If drawing is too detailed, merge repeated forms and remove at least half the marks.
- If color looks decorative, attach it to the source direction or replace it.
- If the photograph looks like a sticker, remove the white outline and restore irregular fibers.
- If identity changes, switch to pixel-preserving mode or replace the source with a non-identity-critical scene.
- If text dominates, reduce scale and contrast or remove it.

Before final delivery, read and complete [quality-gate.md](references/quality-gate.md).

## Hard avoids

Avoid full-frame filters, literal tracing, dense botanical detail, copied windows or leaves, multiple bright hues, generic abstract decorations, commercial advertising hierarchy, glossy mockups, tape, sticker borders, heavy shadows, curled paper, scrapbooking clutter, cinematic lighting, 3D depth, beauty retouching, invented landmarks, altered product packaging, random readable text, and watermarks.

## Output

Return the generated poster and a brief explanation of:

- what relationship was preserved;
- what detail was removed;
- how the structural color guides the eye;
- whether the result is pixel-preserving or generatively reconstructed.

Do not reveal a long prompt unless the user asks for it.

# Workflow and phase deliverables

## Contents

1. Project intake
2. Story definition
3. Visual system
4. Storyboard
5. Asset generation
6. Continuity
7. Site and handoff

## 1. Project intake

Required inputs:

- Product name and authoritative product source.
- Reference page, reference video, or effect description.
- Logo and existing visual assets.
- Audience and primary CTA.
- Local delivery by default; public deployment only when explicitly requested.

Create the asset manifest before generation. Record each asset's id, role, model, prompt path, output path, status, references, and review result.

## 2. Story definition

The brief must state:

- One-sentence positioning.
- What the product is not.
- Three benefits translated into user value.
- Real proof or recognizable cases.
- A concrete continuous metaphor.
- Visual direction and explicit exclusions.

Do not choose a style solely because it looks technological. The metaphor must explain the product.

## 3. Visual system

Generate and confirm in this order:

1. Brand character or logo integration.
2. Core machine, vehicle, environment, or delivery-object sheet.
3. Palette, materials, lighting, camera, and safe text area.
4. One representative key visual.

Do not generate all scenes before this gate passes.

## 4. Storyboard

Default to five scenes:

1. Input and problem recognition.
2. Understanding or decomposition.
3. Validation or selection.
4. Construction or transformation.
5. Testing and tangible delivery.

Adapt the verbs to the product, not the other way around. Preserve one movement direction and one recognizable delivery object.

## 5. Asset generation

Generate one scene at a time. Save prompts before calling models. Inspect each result before using it downstream. A successful model call is not an approval signal.

Use image2.0 for every raster design asset and Seedance 2.0 for every generated video. Do not substitute models.

## 6. Continuity

Wait until scene videos exist before extracting connector endpoints. Compare real rendered frames, then use the least costly strategy that preserves narrative continuity.

## 7. Site and handoff

Freeze the approved video chain before implementing scroll timing. Build locally, test media, package source, and include startup instructions. Do not deploy by default.

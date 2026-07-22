---
name: scroll-promo-site-builder
description: Create a scroll-controlled cinematic product website with rich motion (动效网站) from product materials, reference pages or videos, and brand assets. Use for requests involving 网站动效, immersive product landing pages where scrolling moves a continuous video forward and backward, multi-scene visual storytelling, direct image2.0 and Seedance 2.0 generation, scene-continuity review, or local preview packaging. Do not use for ordinary corporate sites, dashboards, ecommerce, blogs, or standalone promo videos without a website.
---

# Scroll Promo Site Builder

Build a complete local product-promo site whose desktop scroll position controls a continuous cinematic video. Generate image assets directly with `image2.0` and video assets directly with `Seedance 2.0`. Keep the workflow portable across Agent Skills implementations.

## Positioning and attribution

This skill is positioned as a production workflow for cinematic motion websites: it turns product strategy, visual assets, generated video, scroll interaction, review, and local handoff into one repeatable process.

Its scroll-scrubbing, rendered-boundary-frame, connector, and short-GOP media workflow was developed with reference to [oso95/scroll-world](https://github.com/oso95/scroll-world), which is available under the MIT License. This package is a separate React-based implementation with a stricter direct-model contract, product-story phase gates, a single reviewed web-video timeline, static mobile fallback, and local delivery tooling. See `THIRD_PARTY_NOTICES.md` for the upstream copyright and license text.

## Non-negotiable model contract

- Invoke `image2.0` directly for character sheets, equipment sheets, key visuals, first frames, and required last frames.
- Invoke `Seedance 2.0` directly for scene clips and connector clips.
- Do not route either model through another creative platform, canvas system, or intermediary workflow.
- Do not silently substitute another image or video model.
- Discover callable tools by their capability descriptions rather than assuming identical tool names across agents.
- If either required model is unavailable, finish the prompt and input manifest for that generation step, report the missing capability, and stop that phase.
- Save every returned image or video into the project and update the asset manifest immediately.

Read [model-invocation-spec.md](references/model-invocation-spec.md) before the first model call.

## Required phase gates

Pause only at these gates unless required input is missing:

1. **Direction gate:** confirm product positioning, concrete visual metaphor, visual style, and explicit exclusions.
2. **Visual-system gate:** confirm the brand character, core machine or vehicle, palette, materials, and composition rules.
3. **Storyboard gate:** confirm the complete 4–7 scene storyboard and website copy before generating scene clips.
4. **Video-chain gate:** confirm the reviewed full sequence before implementing the site.

Do not ask the user to operate the models. The agent owns generation, saving, inspection, and retries within the agreed scope.

## Workflow

### 0. Inspect the runtime and inputs

- Identify the project root and create a new output folder without overwriting unrelated user files.
- Check file writing, terminal, Python 3, Node.js, npm, ffmpeg, ffprobe, image2.0, and Seedance 2.0 capabilities.
- Collect the product source, reference webpage/video, desired effect notes, logo or brand assets, audience, CTA, and local-versus-public delivery intent.
- Default to local delivery. Publishing requires an explicit user request.
- Read [runtime-compatibility.md](references/runtime-compatibility.md) for capability fallbacks.
- Copy `assets/document-templates/project-intake.md` and complete it as `00-project-intake.md`.

### 1. Define the product story

- Establish one-sentence positioning, what the product is not, three core benefits, proof, target audience, and CTA.
- Choose one concrete metaphor that can visually persist across the entire journey.
- Make the product understandable within the first five seconds.
- Avoid generic light orbs, particles, cosmic maps, or dark cyber aesthetics unless the product and references require them.
- Produce `01-creative-brief.md`, `02-requirements.md`, and `03-development-plan.md` using the bundled document templates.
- Stop at the direction gate.

Read [workflow.md](references/workflow.md) for required deliverables and decision rules.

### 2. Build the visual system with image2.0

- Integrate the brand mark into the story as a character, guide, prop, stamp, vehicle operator, or delivery actor when appropriate.
- Generate the character consistency sheet first.
- Generate the core vehicle, machine, environment, or delivery-object consistency sheet second.
- Lock palette, materials, lighting, camera language, safe text area, and invariants.
- Use original packaging and category motifs for real examples; do not reproduce copyrighted covers or recognizable public-figure portraits.
- Keep long text out of generated imagery. Use blank plaques or deterministic HTML/post-production text when exact wording matters.
- Save prompts beside generated assets.
- Stop at the visual-system gate.

Read [visual-consistency.md](references/visual-consistency.md) before generating consistency sheets.

### 3. Write the storyboard and copy

- Default to five core scenes; use 4–7 only when product complexity justifies it.
- Give each scene one visible action and one product claim.
- Preserve the same character, device, direction of travel, and delivery object across scenes.
- Make the final scene show a tangible deliverable being installed, opened, handed over, or entering the target system.
- Complete every field defined in [storyboard-schema.md](references/storyboard-schema.md).
- Use concise DOM copy: number, eyebrow, title, body, up to three tags, and final CTA.
- Save `05-storyboard.md` and stop at the storyboard gate.

### 4. Generate scene images and videos

For each approved scene:

1. Write and save the complete image2.0 prompt.
2. Invoke image2.0 with all applicable consistency references.
3. Save the key visual and first frame.
4. Inspect subject count, identity, composition, readable object cues, and forbidden text.
5. Make one targeted edit when needed; do not randomize the whole direction.
6. Write and save the Seedance 2.0 prompt.
7. Invoke Seedance 2.0 with the approved reference frame(s), 16:9, 720p, and audio disabled by default.
8. Save the clip and generation record into the asset manifest.

Read [video-prompt-guidelines.md](references/video-prompt-guidelines.md) before writing Seedance prompts.

Use this project layout:

```text
assets/
├── brand/
├── design/
├── prompts/
├── video/
│   ├── scenes/
│   ├── connectors/
│   ├── scene-frames/
│   ├── connector-frames/
│   └── review/
└── manifest.json
```

### 5. Review continuity and generate connectors

- Run `scripts/probe_videos.py` on all generated clips.
- Run `scripts/extract_boundary_frames.sh` to extract stable frames around 0.15 seconds from each edge.
- Run `scripts/make_contact_sheet.sh` to create a review sheet.
- For each boundary, choose exactly one strategy: direct join, integrate the transition into the next scene, Seedance connector, short edit dissolve, or regenerate.
- Generate a connector only from the previous scene's actual tail frame and the next scene's actual head frame.
- Do not use the original concept images as connector endpoints.
- Use a short dissolve only when semantics and movement already match but the generated connector did not reach the exact target.
- Build a review sequence with `scripts/build_review_sequence.py` and stop at the video-chain gate.

Read [continuity-review.md](references/continuity-review.md) before deciding connector strategy.

### 6. Implement the website

- Copy `assets/site-template/` into the project site directory and replace all placeholders.
- Use Vite + React + TypeScript + native CSS by default, or preserve the user's existing framework.
- Map document scroll progress to continuous video time in both directions.
- Synchronize scene copy, navigation, progress rail, and CTA with video time.
- Use `preload="auto"` or request the current frame immediately after metadata is ready.
- Never block seeking on a state that can only be reached after seeking; this creates a poster-only deadlock.
- Keep the poster until a real video frame has rendered, then let the video take over.
- Use a static multi-scene mobile layout rather than cropping a 16:9 desktop video into portrait.
- Provide reduced-motion and video-failure fallbacks.

Read [scroll-site-implementation.md](references/scroll-site-implementation.md) before editing the template.

### 7. Validate and package locally

- Encode the web video with `scripts/encode_web_video.sh`.
- Run the production build.
- Decode-check the final video and verify the project starts locally.
- Complete [delivery-checklist.md](references/delivery-checklist.md).
- Copy the handoff templates, then run `scripts/package_local_preview.sh`.
- Default output is source code plus a local preview archive. Do not publish or push unless explicitly requested.

## Script map

- `probe_videos.py`: JSON media inventory and mismatch detection.
- `extract_boundary_frames.sh`: stable head and tail extraction.
- `make_contact_sheet.sh`: visual overview of boundary frames.
- `build_review_sequence.py`: normalized concatenation with optional per-boundary dissolves.
- `encode_web_video.sh`: scroll-seek-friendly H.264 output.
- `package_local_preview.sh`: clean local handoff archive with integrity check.

Run scripts with explicit project and output arguments. Never depend on the caller's current directory.

## Completion criteria

Complete the task only when:

- Product direction, visual system, storyboard, and full video chain were confirmed.
- Required images came from direct image2.0 calls.
- Required scene and connector clips came from direct Seedance 2.0 calls.
- All generated assets are saved locally with prompts and a manifest.
- The desktop site uses real video scrubbing rather than image replacement.
- Upward scrolling reverses the visual journey.
- Mobile, reduced-motion, and media-failure states remain readable.
- The production build and media decode check pass.
- The user receives a local source folder, preview archive, and startup instructions.

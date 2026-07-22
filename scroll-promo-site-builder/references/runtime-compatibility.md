# Runtime compatibility

## Capability check

Before work, verify:

- File read and write access.
- Terminal execution.
- Python 3.
- Node.js and npm.
- ffmpeg and ffprobe.
- A directly callable image2.0 capability.
- A directly callable Seedance 2.0 capability.

Do not assume a specific agent product, installation directory, or tool identifier.

## Portable path rules

- Resolve paths from the project root or the skill root.
- Pass explicit `--project`, `--input`, and `--output` arguments to scripts.
- Do not embed author-machine paths, home directories, or workspace names.
- Quote paths because they may contain spaces or non-ASCII characters.

## Capability degradation

- No browser: ask for screenshots, recordings, or exported reference files.
- No terminal: produce documents and generation prompts, then report that deterministic media validation and packaging remain blocked.
- No ffmpeg/ffprobe: do not claim continuity or decode validation passed.
- No image2.0: stop before image generation; do not choose another model.
- No Seedance 2.0: stop before video generation; do not choose another model.

## Cross-agent behavior

The root `SKILL.md` contains the workflow. Platform metadata is optional. An agent that can read the skill, edit files, run the required runtimes, and call the two models should produce equivalent artifacts even when its tool names differ.

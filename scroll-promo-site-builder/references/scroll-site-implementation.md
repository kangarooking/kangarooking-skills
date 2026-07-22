# Scroll-controlled site implementation

## Architecture

Use one continuous, reviewed web video when practical. Map page scroll progress to video time:

```text
localProgress = clamp(-worldRect.top / (worldHeight - viewportHeight), 0, 1)
targetTime = localProgress * videoDuration
```

Use a fixed stage inside a tall scroll track. Keep navigation, copy, progress, and video time derived from the same scene timeline.

## Media readiness

- Use `preload="auto"` for the primary scrub video unless the file-size strategy requires a more advanced loader.
- After `loadedmetadata`, immediately request the frame corresponding to current scroll position.
- Reveal the video after `loadeddata`, `canplay`, or a successful `seeked` event.
- Keep the poster visible until a real frame is available.
- Do not make `syncVideo()` return merely because a UI `videoReady` flag is false if seeking is the action required to make it true.
- On `seeked`, chase the newest target time so fast scrolling cannot leave the video at a stale frame.

## Desktop

- Sticky full-viewport stage.
- Video or poster layer.
- Readable local gradient behind copy, not a large opaque card.
- Scene copy stack.
- Header navigation.
- Progress rail.
- Final CTA remains available at the end.

## Mobile

Default to static scene cards with full 16:9 images and DOM copy. Do not crop a wide narrative into portrait and lose key content. Build a native portrait video chain only when explicitly scoped.

## Accessibility

- Keep all claims in DOM text.
- Provide visible focus styles.
- Support Home, End, PageUp, and PageDown when suitable.
- Honor `prefers-reduced-motion` with static content.
- Maintain readable content if video fails.

## Performance

- Encode H.264, yuv420p, faststart, and a short GOP for seeking.
- Keep the initial poster small.
- Avoid loading both full-resolution source media and web media.
- Use a versioned media URL after replacing the video to prevent stale browser caching.

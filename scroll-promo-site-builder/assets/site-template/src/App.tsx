import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { scenes, VIDEO_DURATION } from "./scenes";

const repoUrl = "__PRIMARY_CTA_URL__";

export default function App() {
  const worldRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const targetTime = useRef(0);
  const raf = useRef<number | null>(null);
  const [active, setActive] = useState(0);
  const [progress, setProgress] = useState(0);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  const starts = useMemo(() => scenes.map((scene) => scene.start / VIDEO_DURATION), []);

  const syncVideo = useCallback(() => {
    const video = videoRef.current;
    if (!video || failed || video.readyState < HTMLMediaElement.HAVE_METADATA) return;
    if (!video.seeking && Math.abs(targetTime.current - video.currentTime) > 0.035) {
      video.currentTime = targetTime.current;
    }
  }, [failed]);

  const update = useCallback(() => {
    const world = worldRef.current;
    if (!world) return;
    const rect = world.getBoundingClientRect();
    const distance = Math.max(world.offsetHeight - innerHeight, 1);
    const local = Math.min(Math.max(-rect.top / distance, 0), 1);
    const time = local * VIDEO_DURATION;
    let index = 0;
    scenes.forEach((scene, i) => { if (time >= scene.start) index = i; });
    targetTime.current = time;
    setProgress(local);
    setActive(index);
    syncVideo();
  }, [syncVideo]);

  useEffect(() => {
    const onScroll = () => {
      if (raf.current !== null) return;
      raf.current = requestAnimationFrame(() => {
        update();
        raf.current = null;
      });
    };
    update();
    addEventListener("scroll", onScroll, { passive: true });
    addEventListener("resize", onScroll);
    return () => {
      removeEventListener("scroll", onScroll);
      removeEventListener("resize", onScroll);
      if (raf.current !== null) cancelAnimationFrame(raf.current);
    };
  }, [update]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const requestFrame = () => {
      video.currentTime = targetTime.current === 0 ? 0.001 : targetTime.current;
    };
    video.addEventListener("loadedmetadata", requestFrame);
    video.load();
    return () => video.removeEventListener("loadedmetadata", requestFrame);
  }, []);

  function jump(ratio: number) {
    const world = worldRef.current;
    if (!world) return;
    scrollTo({ top: world.offsetTop + ratio * (world.offsetHeight - innerHeight), behavior: "smooth" });
  }

  return (
    <main>
      <header className="header">
        <a className="brand" href="#start">__PRODUCT_NAME__ <small>__BRAND_BYLINE__</small></a>
        <nav>{scenes.map((scene, i) => <button className={i === active ? "active" : ""} onClick={() => jump(starts[i])} key={scene.id}>{scene.nav}</button>)}</nav>
        <a className="cta small" href={repoUrl} target="_blank" rel="noreferrer">__PRIMARY_CTA_LABEL__ ↗</a>
      </header>

      <section className="world" id="start" ref={worldRef}>
        <div className="stage">
          <div className="media" aria-hidden="true">
            <img className={`poster ${ready && !failed ? "hidden" : ""}`} src={scenes[active].still} alt="" />
            <video
              ref={videoRef}
              className={ready && !failed ? "ready" : ""}
              src="/media/scroll-story.mp4?v=1"
              poster="/stills/scene-01.jpg"
              preload="auto"
              muted
              playsInline
              onLoadedData={() => setReady(true)}
              onCanPlay={() => setReady(true)}
              onSeeked={() => { setReady(true); requestAnimationFrame(syncVideo); }}
              onError={() => setFailed(true)}
            />
            <div className="wash" />
          </div>

          <div className="copyStack">
            {scenes.map((scene, i) => (
              <article className={`copy ${i === active ? "active" : ""}`} key={scene.id}>
                <div className="kicker"><span>{scene.number} / {String(scenes.length).padStart(2, "0")}</span><i style={{ background: scene.accent }} /><span>{scene.eyebrow}</span></div>
                {i === 0 ? <h1>{scene.title}</h1> : <h2>{scene.title}</h2>}
                <p>{scene.body}</p>
                <div className="tags">{scene.tags.map((tag) => <span key={tag}>{tag}</span>)}</div>
                {i === scenes.length - 1 && <a className="cta" href={repoUrl} target="_blank" rel="noreferrer">__PRIMARY_CTA_LABEL__ ↗</a>}
              </article>
            ))}
          </div>

          <aside className="rail" aria-label={`当前场景：${scenes[active].nav}`}>
            <strong>{scenes[active].number}</strong>
            <div className="railTrack"><i style={{ height: `${progress * 100}%` }} />{scenes.map((scene, i) => <button className={i === active ? "active" : i < active ? "past" : ""} onClick={() => jump(starts[i])} aria-label={`前往${scene.nav}`} key={scene.id} />)}</div>
            <span>{String(scenes.length).padStart(2, "0")}</span>
          </aside>
        </div>
      </section>

      <section className="mobileStory">
        {scenes.map((scene, i) => <article className="mobileScene" key={scene.id}><img src={scene.still} alt={`${scene.nav}：${scene.title}`} /><div><small>{scene.number} / {String(scenes.length).padStart(2, "0")} · {scene.eyebrow}</small><h2>{scene.title}</h2><p>{scene.body}</p>{i === scenes.length - 1 && <a className="cta" href={repoUrl}>__PRIMARY_CTA_LABEL__ ↗</a>}</div></article>)}
      </section>
    </main>
  );
}

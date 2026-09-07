"""Parallel cloud ASR with honest chunk-level time ranges and retry checkpoints."""
from __future__ import annotations

import json
import math
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import monotonic, sleep


def chunk_ranges(duration: float, chunk_seconds: float, silences: list[float]) -> list[tuple[float, float]]:
    """Prefer nearby silence without dropping or duplicating source time."""
    bounds = [0.0]
    while duration - bounds[-1] > chunk_seconds + 5:
        target = bounds[-1] + chunk_seconds
        nearby = [s for s in silences if abs(s-target) <= 5 and s > bounds[-1]+10]
        bounds.append(min(nearby, key=lambda s: abs(s-target)) if nearby else target)
    bounds.append(duration)
    return list(zip(bounds, bounds[1:]))


def transcribe_chunks(audio: Path, transcript: Path, raw: Path, *, model: str,
                      chunk_seconds: float = 60, concurrency: int = 4,
                      force: bool = False, progress=None) -> None:
    from asr import _run, transcribe_with_siliconflow
    from vision.frame_sampler import probe_duration
    from vision.cache import source_fingerprint, result_path, read_result, write_result
    import shutil
    duration = probe_duration(audio)
    if not math.isfinite(chunk_seconds) or chunk_seconds < 10 or not 1 <= concurrency <= 4:
        raise RuntimeError('Cloud ASR chunk must be >=10 seconds; concurrency must be 1–4.')
    root = raw.parent / 'asr-chunks'
    root.mkdir(parents=True, exist_ok=True)
    source = source_fingerprint(audio)
    silences = []
    try:
        silence = subprocess.run([shutil.which('ffmpeg') or 'ffmpeg', '-hide_banner', '-i', str(audio),
            '-af', 'silencedetect=noise=-35dB:d=0.25', '-f', 'null', '-'], capture_output=True, text=True, timeout=60)
        if silence.returncode == 0:
            silences = [float(s) for s in re.findall(r'silence_end: ([0-9.]+)', silence.stderr)]
        elif progress:
            progress('ASR 静音检测失败，按连续等长音频块处理，不丢弃内容')
    except subprocess.TimeoutExpired:
        if progress: progress('ASR 静音检测超时，按连续等长音频块处理，不丢弃内容')
    ranges = chunk_ranges(duration, chunk_seconds, silences)

    def process(index, start, end):
        t = monotonic()
        checkpoint = result_path(root, {'source': source, 'model': model, 'start': start, 'end': end, 'schema': 1})
        cached = read_result(checkpoint) if not force else None
        if cached and isinstance(cached.get('text'), str):
            if progress: progress(f'ASR [{index+1}/{len(ranges)}] 复用已转写音频块')
            return cached
        clip = root / f'{index:04d}.mp3'
        text_path, json_path = root / f'{index:04d}.txt', root / f'{index:04d}.raw.json'
        _run([shutil.which('ffmpeg') or 'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
              '-ss', str(start), '-i', str(audio), '-t', str(end-start),
              '-ac', '1', '-ar', '16000', '-b:a', '64k', str(clip)], 'ASR chunk extraction failed')
        for attempt in range(3):
            try:
                transcribe_with_siliconflow(clip, text_path, json_path, model=model, timeout=120)
                break
            except RuntimeError as exc:
                # ASR is read-only; replay only explicit overload/server rejection, not unknown timeouts.
                if attempt == 2 or not any(f'HTTP {c}' in str(exc) for c in (429, 500, 502, 503, 504)):
                    raise
                sleep(2 ** attempt)
        data = json.loads(json_path.read_text(encoding='utf-8'))
        record = {'start': start, 'end': end, 'text': data['text'],
                  'timestamp_precision': 'chunk', 'seconds': round(monotonic()-t, 3)}
        write_result(checkpoint, record)
        if progress: progress(f'ASR [{index+1}/{len(ranges)}] 完成 {start:g}–{end:g}秒')
        return record

    records, errors = [], []
    with ThreadPoolExecutor(max_workers=min(concurrency, len(ranges))) as pool:
        futures = {pool.submit(process, i, start, end): i for i, (start, end) in enumerate(ranges)}
        for future in as_completed(futures):
            try:
                records.append(future.result())
            except (RuntimeError, OSError, ValueError) as exc:
                errors.append(f'chunk {futures[future]+1}: {exc}')
                if progress:
                    progress(f'ASR [{futures[future]+1}/{len(ranges)}] 失败：{exc}；其余片段继续，重跑将复用成功缓存')
    records.sort(key=lambda r: r['start'])
    data = {'text': '\n'.join(r['text'] for r in records), 'segments': records,
            'model': model, 'timestamp_precision': 'chunk', 'errors': errors}
    raw.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    transcript.write_text(data['text'] + '\n', encoding='utf-8')
    if errors:
        raise RuntimeError('Incomplete cloud ASR; successful chunks cached. ' + '; '.join(errors))

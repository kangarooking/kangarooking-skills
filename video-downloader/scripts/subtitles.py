"""Recover real timed captions; never assign guessed word timestamps."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from urllib.request import Request, urlopen


def fetch_platform_subtitles(metadata: dict, output_dir: Path, *, language: str = 'zh') -> dict:
    """Prefer human-labelled tracks, then automatic captions. Failure is nonfatal."""
    candidates = []
    requested = language.lower()
    requested = {'chinese': 'zh', 'mandarin': 'zh', 'english': 'en'}.get(requested, requested)
    for kind, field in (('platform-subtitles', 'subtitles'), ('platform-auto-captions', 'automatic_captions')):
        for lang, entries in (metadata.get(field) or {}).items():
            # Do not silently substitute an unrelated language when Chinese was requested.
            normalized_lang = lang.lower().removeprefix('ai-')
            if requested != 'auto' and not (normalized_lang.startswith(('zh', 'cmn')) if requested == 'zh' else normalized_lang.startswith(requested)):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get('ext') in ('json', 'json3', 'srt', 'vtt') and (entry.get('data') or entry.get('url', '').startswith('https://')):
                    actual_kind = 'platform-auto-captions' if lang.startswith('ai-') else kind
                    candidates.append((actual_kind, lang, entry))
    candidates.sort(key=lambda c: c[0] == 'platform-auto-captions')
    destination = output_dir / 'platform_subtitles.json'
    for kind, lang, entry in candidates:
        try:
            headers = {**(metadata.get('http_headers') or {}), **(entry.get('http_headers') or {})}
            content = entry.get('data')
            if content is None:
                with urlopen(Request(entry['url'], headers=headers), timeout=20) as response:
                    content = response.read().decode('utf-8-sig')
            records = normalize_timed_text(content) if entry['ext'] in ('srt', 'vtt') else normalize_captions(json.loads(content))
            if not records:
                continue
            result = {'status': 'done', 'backend': kind, 'language': lang, 'segments': records}
            destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            return {'status': 'done', 'backend': kind, 'path': str(destination), 'segment_count': len(records)}
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return {'status': 'unavailable', 'error': 'No usable caption track; continue to audio ASR.'}


def normalize_timed_text(content: str) -> list[dict]:
    def seconds(stamp):
        parts = stamp.replace(',', '.').split(':')
        return sum(float(value) * (60 ** i) for i, value in enumerate(reversed(parts)))
    records = []
    for block in re.split(r'\n\s*\n', content.replace('\r\n', '\n')):
        lines = block.splitlines()
        for i, line in enumerate(lines):
            match = re.match(r'([\d:.,]+)\s+-->\s+([\d:.,]+)', line)
            if match:
                text = re.sub('<[^>]+>', '', ' '.join(lines[i+1:])).strip()
                start, end = map(seconds, match.groups())
                if text and 0 <= start < end:
                    records.append({'start': start, 'end': end, 'text': text})
                break
    return records


def normalize_captions(payload: dict) -> list[dict]:
    records = []
    if not isinstance(payload, dict):
        return records
    for item in payload.get('body', payload.get('events', [])):
        if not isinstance(item, dict):
            continue
        try:
            if 'from' in item:
                start, end = float(item['from']), float(item['to'])
                text = str(item.get('content') or '').strip()
            else:
                start = float(item['tStartMs']) / 1000
                end = start + float(item['dDurationMs']) / 1000
                text = ''.join(str(s.get('utf8') or '') for s in item.get('segs', [])).strip()
            if text and math.isfinite(start) and math.isfinite(end) and 0 <= start < end:
                records.append({'start': start, 'end': end, 'text': text})
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(records, key=lambda r: (r['start'], r['end']))


def use_platform_subtitles(path: Path, output_dir: Path) -> dict:
    from asr import _write_normalized_segments
    payload = json.loads(path.read_text(encoding='utf-8'))
    records = payload.get('segments') or []
    if not records:
        raise RuntimeError('Platform captions contain no timed text.')
    transcript = output_dir / 'transcript.txt'
    transcript.write_text('\n'.join(r['text'] for r in records) + '\n', encoding='utf-8')
    segments = output_dir / 'transcript.segments.jsonl'
    _write_normalized_segments(path, transcript, segments, payload['backend'])
    return {'status': 'done', 'backend': payload['backend'], 'transcript_path': str(transcript),
            'segments_path': str(segments), 'raw_json_path': str(path), 'reused': True,
            'timestamp_precision': 'platform-caption',
            'warnings': ['Automatic platform captions may contain recognition errors.'] if payload['backend'] == 'platform-auto-captions' else []}

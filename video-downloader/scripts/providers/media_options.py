"""Shared yt-dlp quality policy: exact preferred height, then best available."""


def format_selector(quality: str = '1080p') -> str:
    if quality == 'best':
        return 'bv*+ba/b'
    if quality not in ('1080p', '720p', '480p'):
        raise ValueError('Download quality must be 1080p, 720p, 480p or best.')
    height = int(quality[:-1])
    return f'bv*[height={height}]+ba/b[height={height}]/bv*+ba/b'


def quality_filename(filename: str, quality: str) -> str:
    from pathlib import Path
    path = Path(filename)
    return f'{path.stem}-{quality}{path.suffix}'

"""Provider registry for video-source-downloader."""

from __future__ import annotations

from urllib.parse import urlparse

from . import bilibili, douyin, xiaohongshu, youtube


IMPLEMENTED_PROVIDERS = [douyin, bilibili, youtube, xiaohongshu]

PLANNED_DOMAINS = {
    "wechat_channels": ("channels.weixin.qq.com", "weixin.qq.com", "video.weixin.qq.com"),
}


def detect_provider(url: str):
    for provider in IMPLEMENTED_PROVIDERS:
        if provider.supports(url):
            return provider
    return None


def planned_provider_for(url: str) -> str | None:
    host = urlparse(url).netloc.lower()
    for provider_name, domains in PLANNED_DOMAINS.items():
        if any(domain in host for domain in domains):
            return provider_name
    return None

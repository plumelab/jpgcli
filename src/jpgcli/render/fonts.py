from __future__ import annotations

from functools import lru_cache

from matplotlib import font_manager

CJK_FONT_CANDIDATES = [
    "Hiragino Sans GB",
    "PingFang SC",
    "Songti SC",
    "Arial Unicode MS",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
]

LATIN_FALLBACKS = [
    "DejaVu Sans",
]


@lru_cache(maxsize=1)
def resolve_font_stack() -> list[str]:
    available = {font.name for font in font_manager.fontManager.ttflist}
    resolved = [name for name in CJK_FONT_CANDIDATES if name in available]
    resolved.extend(name for name in LATIN_FALLBACKS if name in available and name not in resolved)
    if not resolved:
        resolved = ["DejaVu Sans"]
    return resolved


def has_cjk_font() -> bool:
    stack = resolve_font_stack()
    return any(name in CJK_FONT_CANDIDATES for name in stack)

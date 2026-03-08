from __future__ import annotations

from dataclasses import dataclass

from jpgcli.schemas.chart_spec import RenderTheme


@dataclass(frozen=True)
class ThemeConfig:
    palette: list[str]
    background: str
    grid_color: str
    title_size: int
    subtitle_size: int
    label_size: int
    tick_size: int
    legend_size: int
    font_family: str


THEMES = {
    RenderTheme.PAPER: ThemeConfig(
        palette=["#1f4e79", "#2e75b6", "#70ad47", "#c55a11", "#7f6000"],
        background="#ffffff",
        grid_color="#d9e2f3",
        title_size=17,
        subtitle_size=11,
        label_size=11,
        tick_size=10,
        legend_size=10,
        font_family="DejaVu Sans",
    ),
    RenderTheme.REPORT: ThemeConfig(
        palette=["#2f5597", "#00b0f0", "#92d050", "#ffc000", "#c00000"],
        background="#fbfbfd",
        grid_color="#e7eaf3",
        title_size=18,
        subtitle_size=11,
        label_size=11,
        tick_size=10,
        legend_size=10,
        font_family="DejaVu Sans",
    ),
}

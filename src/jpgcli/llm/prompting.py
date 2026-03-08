from __future__ import annotations

import json

from jpgcli.schemas.chart_spec import RenderTheme
from jpgcli.schemas.data_summary import DataFrameSummary


def build_chart_prompt(summary: DataFrameSummary, user_prompt: str, theme: RenderTheme) -> str:
    allowed_schema = {
        "chart_type": ["bar", "grouped_bar", "line", "scatter", "area", "boxplot"],
        "x": "existing column name",
        "y": "existing column name",
        "series": "optional existing column name",
        "aggregation": ["none", "sum", "mean", "count", "median"],
        "sort": ["none", "asc", "desc"],
        "title": "optional string",
        "subtitle": "optional string",
        "caption": "optional string",
        "theme": ["paper", "report"],
        "palette": "optional string",
        "x_label": "optional string",
        "y_label": "optional string",
        "legend_title": "optional string",
        "legend_position": ["best", "upper_left", "upper_right", "lower_left", "lower_right"],
        "error_bar": ["none", "sd", "se"],
        "show_points": "optional boolean",
        "annotate_values": "optional boolean",
        "rotate_xticks": "optional integer degree",
        "y_min": "optional number",
        "y_max": "optional number",
        "notes": ["optional strings"],
    }
    return (
        "You are a chart-planning assistant. Convert the user's request into strict JSON.\n"
        "Rules:\n"
        "1. Output JSON only, no markdown.\n"
        "2. Use only existing column names.\n"
        "3. Allowed chart types: bar, grouped_bar, line, scatter, area, boxplot.\n"
        "4. Prefer scientific, clean plots suitable for weekly reports and slide decks.\n"
        "5. If the source is text-only, do not invent data columns.\n"
        "6. Use boxplot for distribution comparison and area for cumulative/trend-like filled plots when appropriate.\n"
        "7. Use show_points, error_bar, labels, and legend settings only when they improve readability.\n"
        f"6. Default theme should be {theme.value} unless the user clearly asks otherwise.\n\n"
        f"JSON schema guidance:\n{json.dumps(allowed_schema, ensure_ascii=False, indent=2)}\n\n"
        f"Data summary:\n{summary.model_dump_json(indent=2)}\n\n"
        f"User request:\n{user_prompt}\n"
    )

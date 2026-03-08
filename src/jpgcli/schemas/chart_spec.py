from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChartType(str, Enum):
    BAR = "bar"
    GROUPED_BAR = "grouped_bar"
    LINE = "line"
    SCATTER = "scatter"
    AREA = "area"
    BOXPLOT = "boxplot"


class Aggregation(str, Enum):
    NONE = "none"
    SUM = "sum"
    MEAN = "mean"
    COUNT = "count"
    MEDIAN = "median"


class SortOrder(str, Enum):
    NONE = "none"
    ASC = "asc"
    DESC = "desc"


class RenderTheme(str, Enum):
    PAPER = "paper"
    REPORT = "report"


class ErrorBarStyle(str, Enum):
    NONE = "none"
    SD = "sd"
    SE = "se"


class LegendPosition(str, Enum):
    BEST = "best"
    UPPER_LEFT = "upper_left"
    UPPER_RIGHT = "upper_right"
    LOWER_LEFT = "lower_left"
    LOWER_RIGHT = "lower_right"


class ChartSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chart_type: ChartType
    x: str
    y: str | None = None
    series: str | None = None
    aggregation: Aggregation = Aggregation.NONE
    sort: SortOrder = SortOrder.NONE
    title: str | None = None
    subtitle: str | None = None
    caption: str | None = None
    theme: RenderTheme | None = None
    palette: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    legend_title: str | None = None
    legend_position: LegendPosition = LegendPosition.UPPER_LEFT
    error_bar: ErrorBarStyle = ErrorBarStyle.SD
    show_points: bool | None = None
    annotate_values: bool = False
    rotate_xticks: int | None = None
    y_min: float | None = None
    y_max: float | None = None
    notes: list[str] = Field(default_factory=list)

    @field_validator("y")
    @classmethod
    def validate_y_required(cls, value: str | None, info):
        chart_type = info.data.get("chart_type")
        if chart_type in {ChartType.BAR, ChartType.GROUPED_BAR, ChartType.LINE, ChartType.SCATTER, ChartType.AREA, ChartType.BOXPLOT} and not value:
            raise ValueError("y is required for the selected chart type")
        return value

    @model_validator(mode="after")
    def validate_chart_constraints(self):
        if self.chart_type == ChartType.GROUPED_BAR and not self.series:
            raise ValueError("grouped_bar requires a series column")
        if self.chart_type == ChartType.BOXPLOT and self.aggregation != Aggregation.NONE:
            raise ValueError("boxplot must use raw data with aggregation=none")
        if self.y_min is not None and self.y_max is not None and self.y_min >= self.y_max:
            raise ValueError("y_min must be smaller than y_max")
        return self


class ChartRequest(BaseModel):
    prompt: str
    desired_theme: RenderTheme = RenderTheme.PAPER
    output_format: Literal["png"] = "png"

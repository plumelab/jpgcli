from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    inferred_type: str
    null_count: int
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)


class DataFrameSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str
    sheet_name: str | None = None
    row_count: int
    column_count: int
    columns: list[ColumnSummary]
    numeric_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    datetime_columns: list[str] = Field(default_factory=list)
    preview_rows: list[dict[str, Any]] = Field(default_factory=list)
    text_context: str | None = None

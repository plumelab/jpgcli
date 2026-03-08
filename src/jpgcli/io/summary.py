from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
)

from jpgcli.schemas.data_summary import ColumnSummary, DataFrameSummary


def infer_column_type(series: pd.Series) -> str:
    if is_datetime64_any_dtype(series):
        return "datetime"
    if is_numeric_dtype(series):
        return "numeric"
    if is_bool_dtype(series):
        return "boolean"
    return "categorical"


def summarize_dataframe(
    dataframe: pd.DataFrame,
    *,
    source_type: str,
    sheet_name: str | None = None,
    text_context: str | None = None,
) -> DataFrameSummary:
    columns: list[ColumnSummary] = []
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    datetime_columns: list[str] = []

    for column_name in dataframe.columns:
        series = dataframe[column_name]
        inferred_type = infer_column_type(series)
        if inferred_type == "numeric":
            numeric_columns.append(str(column_name))
        elif inferred_type == "datetime":
            datetime_columns.append(str(column_name))
        else:
            categorical_columns.append(str(column_name))

        columns.append(
            ColumnSummary(
                name=str(column_name),
                inferred_type=inferred_type,
                null_count=int(series.isna().sum()),
                unique_count=int(series.nunique(dropna=True)),
                sample_values=_sample_values(series),
            )
        )

    preview = dataframe.head(5).where(dataframe.notna(), None).to_dict(orient="records")

    return DataFrameSummary(
        source_type=source_type,
        sheet_name=sheet_name,
        row_count=int(len(dataframe)),
        column_count=int(len(dataframe.columns)),
        columns=columns,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        datetime_columns=datetime_columns,
        preview_rows=preview,
        text_context=text_context,
    )


def summarize_text(text: str) -> DataFrameSummary:
    return DataFrameSummary(
        source_type="text",
        row_count=0,
        column_count=0,
        columns=[],
        text_context=text[:4000],
    )


def _sample_values(series: pd.Series) -> list[Any]:
    sample = series.dropna().head(3).tolist()
    return [value.item() if hasattr(value, "item") else value for value in sample]

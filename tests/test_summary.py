from pathlib import Path

import pandas as pd

from jpgcli.io.loaders import load_input
from jpgcli.io.summary import summarize_dataframe, summarize_text


def test_summarize_dataframe_detects_column_types() -> None:
    dataframe = pd.DataFrame(
        {
            "week": pd.to_datetime(["2026-03-01", "2026-03-02"]),
            "group": ["A", "B"],
            "value": [1.2, 3.4],
        }
    )
    summary = summarize_dataframe(dataframe, source_type="csv")
    assert summary.row_count == 2
    assert "value" in summary.numeric_columns
    assert "group" in summary.categorical_columns
    assert "week" in summary.datetime_columns


def test_summarize_text_keeps_context() -> None:
    summary = summarize_text("weekly report note")
    assert summary.source_type == "text"
    assert summary.text_context == "weekly report note"


def test_load_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("name,value\nA,10\nB,20\n", encoding="utf-8")
    dataframe, source_type, sheet_name = load_input(csv_path)
    assert source_type == "csv"
    assert sheet_name is None
    assert list(dataframe["name"]) == ["A", "B"]

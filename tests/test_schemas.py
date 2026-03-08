import pytest
from pydantic import ValidationError

from jpgcli.schemas.chart_spec import ChartSpec


def test_chart_spec_validates_successfully() -> None:
    spec = ChartSpec.model_validate(
        {
            "chart_type": "bar",
            "x": "week",
            "y": "value",
            "aggregation": "sum",
            "sort": "desc",
            "theme": "paper",
            "error_bar": "sd",
            "legend_position": "upper_left",
        }
    )
    assert spec.chart_type.value == "bar"


def test_chart_spec_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ChartSpec.model_validate(
            {
                "chart_type": "bar",
                "x": "week",
                "y": "value",
                "unknown": True,
            }
        )


def test_boxplot_rejects_aggregated_spec() -> None:
    with pytest.raises(ValidationError):
        ChartSpec.model_validate(
            {
                "chart_type": "boxplot",
                "x": "treatment",
                "y": "value",
                "aggregation": "mean",
            }
        )

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from jpgcli.render.charts import ChartRenderer
from jpgcli.schemas.chart_spec import ChartSpec, RenderTheme


def test_renderer_generates_png(tmp_path: Path) -> None:
    dataframe = pd.DataFrame({"week": ["W1", "W2"], "value": [10, 20]})
    spec = ChartSpec.model_validate(
        {
            "chart_type": "bar",
            "x": "week",
            "y": "value",
            "aggregation": "none",
            "sort": "none",
            "title": "Weekly Data",
        }
    )
    output_path = tmp_path / "chart.png"
    renderer = ChartRenderer()
    renderer.render(dataframe, spec, output_path, theme=RenderTheme.PAPER)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_renderer_sets_font_stack_for_chinese_labels(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("jpgcli.render.charts.resolve_font_stack", lambda: ["Hiragino Sans GB", "DejaVu Sans"])
    monkeypatch.setattr("jpgcli.render.charts.has_cjk_font", lambda: True)
    dataframe = pd.DataFrame({"处理": ["对照", "干旱"], "数值": [10, 20]})
    spec = ChartSpec.model_validate(
        {
            "chart_type": "bar",
            "x": "处理",
            "y": "数值",
            "aggregation": "none",
            "sort": "none",
            "title": "不同处理下叶片 SOD 活性比较",
        }
    )
    output_path = tmp_path / "cn_chart.png"
    renderer = ChartRenderer()
    renderer.render(dataframe, spec, output_path, theme=RenderTheme.PAPER)
    assert output_path.exists()
    assert plt.rcParams["font.family"][0] == "sans-serif"
    assert plt.rcParams["font.sans-serif"][0] == "Hiragino Sans GB"


def test_grouped_bar_renderer_generates_png_with_replicates(tmp_path: Path) -> None:
    dataframe = pd.DataFrame(
        {
            "treatment": ["Control", "Control", "Control", "Drought", "Drought", "Drought"],
            "plant_variety": ["WT", "WT", "Mutant", "WT", "WT", "Mutant"],
            "sod_activity_u_g_fw": [120.0, 118.0, 122.0, 133.0, 131.0, 145.0],
        }
    )
    spec = ChartSpec.model_validate(
        {
            "chart_type": "grouped_bar",
            "x": "treatment",
            "y": "sod_activity_u_g_fw",
            "series": "plant_variety",
            "aggregation": "mean",
            "sort": "none",
            "title": "SOD activity",
        }
    )
    output_path = tmp_path / "grouped_chart.png"
    renderer = ChartRenderer()
    renderer.render(dataframe, spec, output_path, theme=RenderTheme.PAPER)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_area_renderer_generates_png(tmp_path: Path) -> None:
    dataframe = pd.DataFrame(
        {
            "day": [0, 1, 2, 0, 1, 2],
            "treatment": ["Control", "Control", "Control", "Drought", "Drought", "Drought"],
            "value": [10.0, 12.0, 13.5, 9.0, 14.0, 16.0],
        }
    )
    spec = ChartSpec.model_validate(
        {
            "chart_type": "area",
            "x": "day",
            "y": "value",
            "series": "treatment",
            "aggregation": "mean",
            "title": "Trend",
            "legend_position": "upper_right",
        }
    )
    output_path = tmp_path / "area_chart.png"
    ChartRenderer().render(dataframe, spec, output_path, theme=RenderTheme.PAPER)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_boxplot_renderer_generates_png(tmp_path: Path) -> None:
    dataframe = pd.DataFrame(
        {
            "treatment": ["Control", "Control", "Control", "Drought", "Drought", "Drought"],
            "value": [10.0, 11.0, 12.0, 15.0, 16.0, 17.0],
        }
    )
    spec = ChartSpec.model_validate(
        {
            "chart_type": "boxplot",
            "x": "treatment",
            "y": "value",
            "show_points": True,
            "title": "Distribution",
        }
    )
    output_path = tmp_path / "boxplot_chart.png"
    ChartRenderer().render(dataframe, spec, output_path, theme=RenderTheme.PAPER)
    assert output_path.exists()
    assert output_path.stat().st_size > 0

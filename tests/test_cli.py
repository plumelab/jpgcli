import json
from pathlib import Path

from typer.testing import CliRunner

from jpgcli.cli.app import app
from jpgcli.config import AppConfig
from jpgcli.llm.client import ChartSpecGenerator
from jpgcli.schemas.chart_spec import ChartSpec


class StubGenerator(ChartSpecGenerator):
    def __init__(self) -> None:
        pass

    def generate(self, summary, request):
        return ChartSpec.model_validate(
            {
                "chart_type": "line",
                "x": "week",
                "y": "value",
                "aggregation": "none",
                "sort": "none",
                "title": "Trend",
                "theme": "report",
            }
        )


def test_cli_chart_generates_output(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "weekly.csv"
    csv_path.write_text("week,value\nW1,10\nW2,12\n", encoding="utf-8")
    runner = CliRunner()
    monkeypatch.setattr("jpgcli.cli.app.ChartSpecGenerator", StubGenerator)
    monkeypatch.setattr(
        "jpgcli.cli.app.load_app_config",
        lambda: AppConfig(api_key="sk-test", model="gpt-test", input_dir=str(tmp_path), output_dir=str(tmp_path)),
    )
    result = runner.invoke(
        app,
        [
            "chart",
            str(csv_path),
            "--prompt",
            "做成趋势图",
            "--output",
            str(tmp_path / "out.png"),
            "--debug-json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "out.png").exists()
    debug_spec = json.loads((tmp_path / "out.spec.json").read_text(encoding="utf-8"))
    assert debug_spec["chart_type"] == "line"


def test_init_writes_env_file(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["init"],
        input=f"y\nsk-demo-key\ngpt-demo\n{tmp_path / 'input'}\n{tmp_path / 'output'}\nhttps://example.com/v1\ny\n",
    )
    assert result.exit_code == 0, result.stdout
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=sk-demo-key" in env_text
    assert "OPENAI_MODEL=gpt-demo" in env_text
    assert "OPENAI_BASE_URL=https://example.com/v1" in env_text
    assert f"JPGCLI_INPUT_DIR={tmp_path / 'input'}" in env_text
    assert f"JPGCLI_OUTPUT_DIR={tmp_path / 'output'}" in env_text


def test_chart_requires_init_in_non_interactive_mode(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "weekly.csv"
    csv_path.write_text("week,value\nW1,10\nW2,12\n", encoding="utf-8")
    runner = CliRunner()
    monkeypatch.setattr("jpgcli.cli.app.load_app_config", lambda: AppConfig())
    result = runner.invoke(app, ["chart", str(csv_path), "--prompt", "做成趋势图"])
    assert result.exit_code == 1
    assert "Run `jpgcli init` first" in result.output


def test_chart_auto_init_then_generates_output(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "weekly.csv"
    csv_path.write_text("week,value\nW1,10\nW2,12\n", encoding="utf-8")
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("jpgcli.cli.app.ChartSpecGenerator", StubGenerator)
    result = runner.invoke(
        app,
        ["chart", str(csv_path), "--prompt", "做成趋势图", "--output", str(tmp_path / "auto.png")],
        input=f"n\nsk-demo-key\ngpt-demo\n{tmp_path / 'input'}\n{tmp_path / 'output'}\ny\n",
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "auto.png").exists()
    assert (tmp_path / ".env").exists()


def test_init_check_reports_status(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        "jpgcli.cli.app.load_app_config",
        lambda: AppConfig(api_key="sk-secret-key", model="gpt-test", input_dir="/tmp/in", output_dir="/tmp/out"),
    )
    result = runner.invoke(app, ["init", "--check"])
    assert result.exit_code == 0
    assert "Configuration status: complete" in result.stdout
    assert "OPENAI_API_KEY=" in result.stdout
    assert "sk-secret-key" not in result.stdout


def test_chart_interactive_selects_file_and_auto_saves(tmp_path: Path, monkeypatch) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    csv_path = input_dir / "weekly.csv"
    csv_path.write_text("week,value\nW1,10\nW2,12\n", encoding="utf-8")
    runner = CliRunner()
    monkeypatch.setattr("jpgcli.cli.app.ChartSpecGenerator", StubGenerator)
    monkeypatch.setattr(
        "jpgcli.cli.app.load_app_config",
        lambda: AppConfig(api_key="sk-test", model="gpt-test", input_dir=str(input_dir), output_dir=str(output_dir)),
    )
    result = runner.invoke(app, ["chart"], input="1\n做成趋势图\n")
    assert result.exit_code == 0, result.output
    generated = list(output_dir.glob("weekly_*.png"))
    assert len(generated) == 1


def test_chart_interactive_fails_when_no_supported_files(tmp_path: Path, monkeypatch) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    runner = CliRunner()
    monkeypatch.setattr(
        "jpgcli.cli.app.load_app_config",
        lambda: AppConfig(api_key="sk-test", model="gpt-test", input_dir=str(input_dir), output_dir=str(output_dir)),
    )
    result = runner.invoke(app, ["chart"])
    assert result.exit_code == 1
    assert "No supported input files found" in result.output

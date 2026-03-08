from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import click
import typer

from jpgcli.config import AppConfig, load_app_config, read_env_values, write_app_config
from jpgcli.io.loaders import load_input, load_text
from jpgcli.io.summary import summarize_dataframe, summarize_text
from jpgcli.llm.client import ChartSpecGenerator
from jpgcli.render.charts import ChartRenderer
from jpgcli.schemas.chart_spec import ChartRequest, RenderTheme
from jpgcli.utils.errors import ConfigError, JpgCliError

app = typer.Typer(help="Generate research-style charts from data and prompts.")
SUPPORTED_INPUT_SUFFIXES = {".xlsx", ".xls", ".xlsm", ".csv", ".txt"}


@app.command()
def init(
    check: bool = typer.Option(False, "--check", help="Check whether config is complete."),
) -> None:
    config = load_app_config()
    if check:
        status = "complete" if config.is_complete() and config.has_directories() else "incomplete"
        typer.echo(f"Configuration status: {status}")
        if config.input_dir and not Path(config.input_dir).exists():
            typer.echo("Warning: input directory does not exist")
        if config.output_dir and not Path(config.output_dir).exists():
            typer.echo("Warning: output directory does not exist")
        for key, value in config.masked().items():
            typer.echo(f"{key}={value}")
        raise typer.Exit(code=0 if config.is_complete() and config.has_directories() else 1)

    _run_init_flow(force_prompt=True)


@app.command()
def chart(
    input_path: Path | None = typer.Argument(None, exists=True, readable=True, help="Path to xlsx/csv/txt input."),
    prompt: str | None = typer.Option(None, "--prompt", "-p", help="Natural-language chart request."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Path to output PNG."),
    sheet: str | None = typer.Option(None, "--sheet", help="Excel sheet name or index."),
    theme: RenderTheme = typer.Option(RenderTheme.PAPER, "--theme", help="Render theme."),
    title: str | None = typer.Option(None, "--title", help="Override chart title."),
    dpi: int = typer.Option(300, "--dpi", help="PNG DPI."),
    width: float = typer.Option(10.0, "--width", help="Figure width in inches."),
    height: float = typer.Option(6.0, "--height", help="Figure height in inches."),
    debug_json: bool = typer.Option(False, "--debug-json", help="Write chart spec JSON next to output."),
) -> None:
    try:
        _ensure_config_ready()
        selected_input, selected_prompt, selected_output = _resolve_chart_inputs(input_path, prompt, output)
        dataframe, source_type, sheet_name = load_input(selected_input, sheet=sheet)
        if source_type == "text":
            summary = summarize_text(load_text(selected_input))
        else:
            summary = summarize_dataframe(dataframe, source_type=source_type, sheet_name=sheet_name)

        generator = ChartSpecGenerator()
        spec = generator.generate(summary, ChartRequest(prompt=selected_prompt, desired_theme=theme))

        if source_type == "text" or dataframe is None:
            raise typer.BadParameter("Text-only input is not supported for chart rendering in v1.")

        renderer = ChartRenderer()
        output_path = selected_output
        final_theme = spec.theme or theme
        renderer.render(
            dataframe,
            spec,
            output_path,
            theme=final_theme,
            width=width,
            height=height,
            dpi=dpi,
            override_title=title,
        )

        if debug_json:
            debug_path = output_path.with_suffix(".spec.json")
            debug_path.write_text(json.dumps(spec.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
            typer.echo(f"Chart spec saved to {debug_path}")

        typer.echo(f"Chart saved to {output_path}")
    except JpgCliError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from exc


def _ensure_config_ready() -> None:
    config = load_app_config()
    if config.is_complete() and config.has_directories():
        return
    _run_init_flow(force_prompt=False)


def _run_init_flow(*, force_prompt: bool) -> None:
    env_path = Path.cwd() / ".env"
    existing_values = read_env_values(env_path)
    if existing_values and force_prompt:
        should_override = typer.confirm("Detected an existing .env file. Overwrite managed OpenAI settings?", default=False)
        if not should_override:
            typer.echo("Initialization cancelled. Existing configuration was kept.")
            raise typer.Exit(code=0)

    try:
        typer.echo("Welcome to jpgcli initialization.")
        use_custom_base_url = typer.confirm("Do you want to set a custom API base URL?", default=False)
        api_key = typer.prompt("Enter your OPENAI_API_KEY", hide_input=True).strip()
        model = typer.prompt("Enter your OPENAI_MODEL", default="gpt-4.1-mini").strip()
        input_dir = typer.prompt("Enter your default input directory", default=str(Path.cwd() / "input")).strip()
        output_dir = typer.prompt("Enter your default output directory", default=str(Path.cwd() / "output")).strip()
        base_url = ""
        if use_custom_base_url:
            base_url = typer.prompt("Enter your OPENAI_BASE_URL").strip()
    except (EOFError, click.Abort) as exc:
        raise ConfigError("Missing configuration in non-interactive mode. Run `jpgcli init` first.") from exc

    _ensure_directory(Path(input_dir), "input directory")
    _ensure_directory(Path(output_dir), "output directory")
    config = AppConfig(
        api_key=api_key,
        model=model,
        base_url=base_url or None,
        input_dir=str(Path(input_dir).expanduser()),
        output_dir=str(Path(output_dir).expanduser()),
    )
    try:
        should_save = typer.confirm(f"Write this configuration to {env_path}?", default=True)
    except (EOFError, click.Abort) as exc:
        raise ConfigError("Missing configuration in non-interactive mode. Run `jpgcli init` first.") from exc
    if not should_save:
        raise ConfigError("Initialization aborted before writing .env.")

    write_app_config(config, env_path)
    typer.echo(f"Configuration saved to {env_path}")


def _resolve_chart_inputs(
    input_path: Path | None,
    prompt: str | None,
    output: Path | None,
) -> tuple[Path, str, Path]:
    config = load_app_config()
    if input_path is not None and prompt:
        return input_path, prompt, output or input_path.with_suffix(".png")

    input_dir = _validated_directory(config.input_dir, "input directory")
    output_dir = _validated_directory(config.output_dir, "output directory", create=True)
    available_files = _list_supported_input_files(input_dir)
    if not available_files:
        raise ConfigError(f"No supported input files found in {input_dir}.")

    typer.echo("Available files:")
    for index, file_path in enumerate(available_files, start=1):
        typer.echo(f"{index}. {file_path.name}")

    try:
        selected_index = typer.prompt("Select a file by number", type=int)
        selected_file = available_files[selected_index - 1]
        selected_prompt = prompt or typer.prompt("Enter your chart prompt").strip()
    except (EOFError, click.Abort) as exc:
        raise ConfigError("Interactive chart mode requires terminal input.") from exc
    except IndexError as exc:
        raise ConfigError("Invalid file selection.") from exc

    return selected_file, selected_prompt, output or _build_output_path(output_dir, selected_file)


def _list_supported_input_files(input_dir: Path) -> list[Path]:
    return sorted(
        [path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES],
        key=lambda path: path.name.lower(),
    )


def _build_output_path(output_dir: Path, input_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"{input_path.stem}_{timestamp}.png"


def _validated_directory(path_value: str | None, label: str, *, create: bool = False) -> Path:
    if not path_value:
        raise ConfigError(f"Missing {label}. Please run `jpgcli init` first.")
    path = Path(path_value).expanduser()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        raise ConfigError(f"Configured {label} does not exist: {path}")
    if not path.is_dir():
        raise ConfigError(f"Configured {label} is not a directory: {path}")
    return path


def _ensure_directory(path: Path, label: str) -> None:
    try:
        path.expanduser().mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"Unable to create {label}: {path}") from exc

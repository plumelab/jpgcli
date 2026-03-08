from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from jpgcli.utils.errors import ConfigError

MANAGED_KEYS = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "JPGCLI_INPUT_DIR", "JPGCLI_OUTPUT_DIR")


@dataclass
class AppConfig:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    input_dir: str | None = None
    output_dir: str | None = None

    def is_complete(self) -> bool:
        return bool(self.api_key and self.model)

    def has_directories(self) -> bool:
        return bool(self.input_dir and self.output_dir)

    def masked(self) -> dict[str, str]:
        return {
            "OPENAI_API_KEY": _mask_secret(self.api_key),
            "OPENAI_BASE_URL": self.base_url or "(default)",
            "OPENAI_MODEL": self.model or "(missing)",
            "JPGCLI_INPUT_DIR": self.input_dir or "(missing)",
            "JPGCLI_OUTPUT_DIR": self.output_dir or "(missing)",
        }


def load_app_config(env_path: Path | None = None) -> AppConfig:
    env_file = env_path or Path.cwd() / ".env"
    load_dotenv(env_file)
    return AppConfig(
        api_key=os.getenv("OPENAI_API_KEY") or None,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        model=os.getenv("OPENAI_MODEL") or None,
        input_dir=os.getenv("JPGCLI_INPUT_DIR") or None,
        output_dir=os.getenv("JPGCLI_OUTPUT_DIR") or None,
    )


def read_env_values(env_path: Path | None = None) -> dict[str, str]:
    env_file = env_path or Path.cwd() / ".env"
    if not env_file.exists():
        return {}
    return {key: value for key, value in dotenv_values(env_file).items() if value is not None}


def write_app_config(config: AppConfig, env_path: Path | None = None) -> Path:
    env_file = env_path or Path.cwd() / ".env"
    existing = read_env_values(env_file)
    for key in MANAGED_KEYS:
        existing.pop(key, None)

    updates = {
        "OPENAI_API_KEY": config.api_key or "",
        "OPENAI_MODEL": config.model or "",
        "JPGCLI_INPUT_DIR": config.input_dir or "",
        "JPGCLI_OUTPUT_DIR": config.output_dir or "",
    }
    if config.base_url:
        updates["OPENAI_BASE_URL"] = config.base_url

    merged = {**existing, **updates}
    content = "\n".join(f"{key}={_quote_env_value(value)}" for key, value in merged.items() if value != "")
    if content:
        content += "\n"
    env_file.write_text(content, encoding="utf-8")
    return env_file


def ensure_config_complete(config: AppConfig) -> None:
    if not config.is_complete():
        raise ConfigError("Missing required configuration. Please run `jpgcli init` or set your .env values.")


def _mask_secret(value: str | None) -> str:
    if not value:
        return "(missing)"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _quote_env_value(value: str) -> str:
    if value == "":
        return value
    if any(char.isspace() for char in value) or "#" in value:
        return f'"{value}"'
    return value

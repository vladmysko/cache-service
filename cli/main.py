import json
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CliSettings(BaseSettings):
    host: str = "http://127.0.0.1:8000"
    repeat: int = 1

    input_file: str | None = Field(
        default=None,
        validation_alias="input",
    )
    json_input: str | None = Field(
        default=None,
        validation_alias="json",
    )
    output_file: str = Field(
        default="-",
        validation_alias="output",
    )

    model_config = SettingsConfigDict(
        cli_parse_args=True,
        case_sensitive=True,
        cli_shortcuts={
            "host": "H",
            "repeat": "r",
            "input": "i",
            "json": "j",
            "output": "o",
        },
    )

    @field_validator("repeat")
    @classmethod
    def validate_repeat(cls, value: int) -> int:
        if value < 1:
            raise ValueError("repeat must be at least 1")
        return value

    @model_validator(mode="after")
    def validate_input_source(self):
        if self.input_file is None and self.json_input is None:
            raise ValueError(
                "either --input or --json must be provided"
            )

        if self.input_file is not None and self.json_input is not None:
            raise ValueError(
                "--input and --json cannot be used together"
            )

        return self


def read_input(settings: CliSettings) -> dict[str, Any]:
    if settings.json_input is not None:
        raw = settings.json_input
    elif settings.input_file == "-":
        raw = sys.stdin.read()
    else:
        path = Path(settings.input_file)
        raw = path.read_text(encoding="utf-8")

    data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError("input JSON must be an object")

    return data


def write_output(
    settings: CliSettings,
    results: list[dict[str, Any]],
) -> None:
    text = "\n".join(
        json.dumps(result, ensure_ascii=False)
        for result in results
    )

    if settings.output_file == "-":
        print(text)
        return

    Path(settings.output_file).write_text(
        text + "\n",
        encoding="utf-8",
    )


def run(settings: CliSettings) -> None:
    payload = read_input(settings)

    url = f"{settings.host.rstrip('/')}/payload"

    results = []

    with httpx.Client(timeout=30.0) as client:
        for _ in range(settings.repeat):
            response = client.post(url, json=payload)
            response.raise_for_status()
            results.append(response.json())

    write_output(settings, results)


def main() -> None:
    try:
        settings = CliSettings()
        run(settings)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        httpx.HTTPError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
import json

import pytest
from pydantic import ValidationError

from cli.main import CliSettings, read_input, write_output


def test_read_input_from_json():
    settings = CliSettings(
        json='{"list_1":["a"],"list_2":["b"]}',
        _cli_parse_args=[],
    )

    result = read_input(settings)

    assert result == {
        "list_1": ["a"],
        "list_2": ["b"],
    }


def test_read_input_from_file(tmp_path):
    input_file = tmp_path / "input.json"
    input_file.write_text(
        json.dumps({
            "list_1": ["a"],
            "list_2": ["b"],
        }),
        encoding="utf-8",
    )

    settings = CliSettings(
        input=str(input_file),
        _cli_parse_args=[],
    )

    result = read_input(settings)

    assert result == {
        "list_1": ["a"],
        "list_2": ["b"],
    }


def test_write_output_to_file(tmp_path):
    output_file = tmp_path / "output.json"

    settings = CliSettings(
        json='{"list_1":["a"],"list_2":["b"]}',
        output=str(output_file),
        _cli_parse_args=[],
    )

    write_output(
        settings,
        [{"id": "test-id"}],
    )

    assert (
        output_file.read_text(encoding="utf-8").strip()
        == '{"id": "test-id"}'
    )


def test_repeat_must_be_positive():
    with pytest.raises(ValidationError):
        CliSettings(
            json='{"list_1":["a"],"list_2":["b"]}',
            repeat=0,
            _cli_parse_args=[],
        )
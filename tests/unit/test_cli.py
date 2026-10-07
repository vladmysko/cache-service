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

def test_cli_posts_repeatedly_from_stdin(monkeypatch, capsys):
    import io
    import httpx
    from cli.main import run

    requests = []
    client_class = httpx.Client

    def handler(request):
        requests.append(request)
        return httpx.Response(201, json={"id": "same-id"})

    monkeypatch.setattr("cli.main.httpx.Client", lambda **kwargs: client_class(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    monkeypatch.setattr("sys.stdin", io.StringIO('{"list_1":["a"],"list_2":["b"]}'))
    settings = CliSettings(_cli_parse_args=[
        "-H", "http://example.test/", "-r", "3", "-i", "-", "-o", "-",
    ])
    run(settings)
    assert len(requests) == 3
    assert all(request.method == "POST" and str(request.url) == "http://example.test/payload" for request in requests)
    assert all(json.loads(request.content) == {"list_1": ["a"], "list_2": ["b"]} for request in requests)
    assert capsys.readouterr().out.splitlines() == ['{"id": "same-id"}'] * 3


def test_cli_http_failure_exits_with_error(monkeypatch, capsys):
    import httpx
    from cli.main import main

    client_class = httpx.Client
    monkeypatch.setattr("sys.argv", ["cache-cli", "-j", '{"list_1":[],"list_2":[]}'])
    monkeypatch.setattr("cli.main.httpx.Client", lambda **kwargs: client_class(
        transport=httpx.MockTransport(lambda request: httpx.Response(422, json={"detail": "invalid"})),
        **kwargs,
    ))
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "422" in captured.err

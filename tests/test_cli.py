"""
Integration and CLI tests for main.py.
Verifies command-line arguments, stdout/file output, exit codes,
and error reporting.
"""

import json
from pathlib import Path
import pytest

from main import run


def test_cli_stdout_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Verify CLI prints formatted JSON to stdout when no output file is provided."""
    sample_file = tmp_path / "style.css"
    sample_file.write_text(".box { margin: 10px; }", encoding="utf-8")

    exit_code = run([str(sample_file)])
    assert exit_code == 0

    captured = capsys.readouterr()
    output_doc = json.loads(captured.out)
    assert output_doc["source"] == "style.css"
    assert output_doc["summary"]["total_rules"] == 1
    assert output_doc["summary"]["total_declarations"] == 1


def test_cli_output_file_argument(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Verify CLI writes formatted JSON to the path specified in --output."""
    sample_file = tmp_path / "style.css"
    sample_file.write_text(".box { padding: 5px; }", encoding="utf-8")
    out_file = tmp_path / "out" / "result.json"

    exit_code = run([str(sample_file), "--output", str(out_file)])
    assert exit_code == 0
    assert out_file.exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["summary"]["total_declarations"] == 1

    captured = capsys.readouterr()
    assert "Successfully parsed" in captured.err


def test_cli_compact_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Verify --compact produces single-line JSON without extra whitespace."""
    sample_file = tmp_path / "style.css"
    sample_file.write_text(".card { color: red; }", encoding="utf-8")

    exit_code = run([str(sample_file), "--compact"])
    assert exit_code == 0

    captured = capsys.readouterr()
    # Compact output is on a single line (plus newline)
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["summary"]["total_rules"] == 1


def test_cli_missing_file_error(capsys: pytest.CaptureFixture[str]):
    """Verify CLI returns non-zero exit code and error message for nonexistent file."""
    exit_code = run(["non_existent_file_9876.css"])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "not found" in captured.err.lower()


def test_cli_empty_file_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Verify CLI returns non-zero exit code and error message for empty file."""
    empty_file = tmp_path / "empty.css"
    empty_file.write_text("", encoding="utf-8")

    exit_code = run([str(empty_file)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "empty" in captured.err.lower()


def test_cli_directory_path_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Verify CLI returns non-zero exit code when given a directory instead of a file."""
    test_dir = tmp_path / "css_folder"
    test_dir.mkdir()

    exit_code = run([str(test_dir)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "not a regular file" in captured.err.lower()


def test_cli_non_css_extension_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Verify CLI emits warning when file does not have .css extension but succeeds."""
    txt_file = tmp_path / "styles.txt"
    txt_file.write_text("a { color: blue; }", encoding="utf-8")

    exit_code = run([str(txt_file)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Warning:" in captured.err
    assert ".css extension" in captured.err

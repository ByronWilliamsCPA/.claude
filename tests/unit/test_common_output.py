"""Tests for claude_config.common.output writers."""

from claude_config.common.output import err, out


def test_out_writes_line_to_stdout(capsys):
    out("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
    assert captured.err == ""


def test_out_default_emits_blank_line(capsys):
    out()
    assert capsys.readouterr().out == "\n"


def test_err_writes_line_to_stderr(capsys):
    err("oops")
    captured = capsys.readouterr()
    assert captured.err == "oops\n"
    assert captured.out == ""

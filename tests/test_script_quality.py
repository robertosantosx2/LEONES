from pathlib import Path

from scripts.check_script_quality import check_file


def write_script(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "example.py"
    path.write_text(content, encoding="utf-8")
    return path


def test_quality_accepts_a_small_documented_script(tmp_path: Path) -> None:
    path = write_script(
        tmp_path,
        '#!/usr/bin/env python3\n"""Example script."""\nprint("ok")\n',
    )
    assert check_file(path) == []


def test_quality_reports_long_lines_and_multiple_statements(tmp_path: Path) -> None:
    path = write_script(
        tmp_path,
        '#!/usr/bin/env python3\n"""Example script."""\n'
        + "x = "
        + "a; b\n"
        + "# "
        + "x" * 110
        + "\n",
    )
    problems = check_file(path)
    assert any("varias instrucciones" in problem for problem in problems)
    assert any("supera 100" in problem for problem in problems)


def test_quality_reports_missing_documentation(tmp_path: Path) -> None:
    path = write_script(tmp_path, "#!/usr/bin/env python3\nprint('ok')\n")
    assert any("docstring inicial" in problem for problem in check_file(path))

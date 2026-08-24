from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from boolean_functions import evaluate_zhegalkin, zhegalkin_from_number

ROOT = Path(__file__).parents[1]
REFERENCE_TABLE = ROOT / "references" / "tex_data.txt"
MINIMAL_TABLE = """\\begin{longtable}{| l| r | p{11cm}|}
Номер класса & Длина функции & Мощность & ПСПФ\\\\
1 & 1 & 1 & $0$ \\\\
\\end{longtable}
"""


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "main.py", *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def evaluate_formatted_expression(expression: str, assignment: dict[int, int]) -> int:
    tokens = re.findall(r"x_\d+|[()+]|[01]", expression)
    position = 0

    def expression_value() -> int:
        nonlocal position
        result = product_value()
        while position < len(tokens) and tokens[position] == "+":
            position += 1
            result ^= product_value()
        return result

    def product_value() -> int:
        nonlocal position
        result = atom_value()
        while position < len(tokens) and tokens[position] != ")" and tokens[position] != "+":
            result &= atom_value()
        return result

    def atom_value() -> int:
        nonlocal position
        token = tokens[position]
        position += 1
        if token == "(":
            result = expression_value()
            assert tokens[position] == ")"
            position += 1
            return result
        if token.startswith("x_"):
            return assignment[int(token[2:])]
        return int(token)

    result = expression_value()
    assert position == len(tokens)
    return result


def test_calculate_defaults_to_four_arguments() -> None:
    result = run_cli("calculate", "0")
    assert result.returncode == 0
    assert result.stdout == "0\n"
    assert result.stderr == ""


def test_calculate_warns_but_continues_for_k_five() -> None:
    result = run_cli("calculate", "--k=5", "0")
    assert result.returncode == 0
    assert result.stdout == "0\n"
    assert result.stderr.count("warning:") == 1


def test_calculate_rejects_out_of_range_number_without_traceback() -> None:
    result = run_cli("calculate", "--k=1", "4")
    assert result.returncode != 0
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_calculate_output_expands_to_the_source_function() -> None:
    result = run_cli("calculate", "--k=4", "27031")
    assert result.returncode == 0
    polynomial = zhegalkin_from_number(27031, 4)
    for assignment_mask in range(1 << 4):
        assignment = {variable: (assignment_mask >> (4 - variable)) & 1 for variable in range(1, 5)}
        actual = evaluate_formatted_expression(result.stdout.strip(), assignment)
        expected = evaluate_zhegalkin(polynomial, assignment_mask)
        assert actual == expected


def test_generate_table_enriches_the_reference_table(tmp_path: Path) -> None:
    input_path = tmp_path / "reference.tex"
    output_path = tmp_path / "out.tex"
    shutil.copyfile(REFERENCE_TABLE, input_path)

    result = run_cli("generate_table", "--k=4", f"--out={output_path}", str(input_path))

    assert result.returncode == 0
    assert result.stdout == ""
    output = output_path.read_text(encoding="utf-8")
    assert (
        "Номер класса & Длина функции & Мощность & Оптимальная ПСПФ & "
        "Длина построенной & Построенная ПСПФ"
    ) in output
    input_lines = input_path.read_text(encoding="utf-8").splitlines()
    original_rows = [line for line in input_lines if " & $" in line]
    constructed_rows = [line for line in output.splitlines() if " & $" in line]
    assert len(original_rows) == 32
    assert len(constructed_rows) == 32
    assert all(
        constructed.startswith(original.removesuffix("\\\\").rstrip() + " & ")
        for original, constructed in zip(original_rows, constructed_rows, strict=True)
    )
    assert all(row.count("&") == 5 for row in constructed_rows)


def test_generate_table_no_length_keeps_five_output_columns(tmp_path: Path) -> None:
    input_path = tmp_path / "minimal.tex"
    output_path = tmp_path / "out.tex"
    input_path.write_text(MINIMAL_TABLE, encoding="utf-8")

    result = run_cli(
        "generate_table",
        "--k=4",
        "--no-length",
        f"--out={output_path}",
        str(input_path),
    )

    assert result.returncode == 0
    output = output_path.read_text(encoding="utf-8")
    assert (
        "Номер класса & Длина функции & Мощность & Оптимальная ПСПФ & Построенная ПСПФ"
    ) in output
    assert "Длина построенной" not in output
    assert "1 & 1 & 1 & $0$ & $0$" in output


def test_generate_table_warns_once_for_k_five(tmp_path: Path) -> None:
    input_path = tmp_path / "minimal.tex"
    output_path = tmp_path / "out.tex"
    input_path.write_text(MINIMAL_TABLE, encoding="utf-8")

    result = run_cli("generate_table", "--k=5", f"--out={output_path}", str(input_path))

    assert result.returncode == 0
    assert result.stderr.count("warning:") == 1
    assert result.stdout == ""


def test_generate_table_preserves_existing_output_after_malformed_input(tmp_path: Path) -> None:
    input_path = tmp_path / "malformed.tex"
    output_path = tmp_path / "out.tex"
    input_path.write_text(MINIMAL_TABLE.replace("$0$", "not math"), encoding="utf-8")
    output_path.write_text("keep this output", encoding="utf-8")

    result = run_cli("generate_table", "--k=4", f"--out={output_path}", str(input_path))

    assert result.returncode != 0
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert output_path.read_text(encoding="utf-8") == "keep this output"

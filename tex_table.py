"""Enrich the PSPF column in a LaTeX longtable with generated expressions."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path
from tempfile import NamedTemporaryFile

ORIGINAL_EXPRESSION_WIDTH = "11cm"
OUTPUT_EXPRESSION_WIDTH = "5.5cm"
ORIGINAL_HEADER = "Длина функции & Номер & ПСПФ"
OUTPUT_HEADER = "Длина функции & Номер & Оптимальная ПСПФ & Построенная ПСПФ"

DATA_ROW_RE = re.compile(
    r"^(?P<indent>\s*)(?P<length>\d+)(?P<sep1>\s*&\s*)"
    r"(?P<number>\d+)(?P<sep2>\s*&\s*)\$(?P<expression>[^$&]*)\$"
    r"(?P<ending>\\\\\s*)(?P<newline>\r?\n)?$"
)
POTENTIAL_DATA_ROW_RE = re.compile(r"^\s*\d+\s*&")
BEGIN_LONGTABLE_RE = re.compile(r"^[ \t]*\\begin\{longtable\}\{.*\}[ \t]*(?:\r?\n)?$")
TARGET_BEGIN_LONGTABLE_RE = re.compile(
    rf"^[ \t]*\\begin\{{longtable\}}\{{\|[ \t]*l[ \t]*\|[ \t]*r[ \t]*\|[ \t]*p"
    rf"\{{{re.escape(ORIGINAL_EXPRESSION_WIDTH)}\}}\|\}}[ \t]*(?:\r?\n)?$"
)
END_LONGTABLE_RE = re.compile(r"^[ \t]*\\end\{longtable\}[ \t]*(?:\r?\n)?$")
HEADER_RE = re.compile(rf"^[ \t]*{re.escape(ORIGINAL_HEADER)}[ \t]*\\\\[ \t]*(?:\r?\n)?$")
MULTICOLUMN_CONTINUATION_RE = re.compile(
    r"^(?P<prefix>[ \t]*(?:\\hline[ \t]+)?\\multicolumn\{)3"
    r"(?P<suffix>\}\{[lcr]\}\{.*\}[ \t]*\\\\[ \t]*(?:\r?\n)?)$"
)
WIDTH_RE = re.compile(rf"p\{{{re.escape(ORIGINAL_EXPRESSION_WIDTH)}\}}\|")


class TexTableError(ValueError):
    """Raised when a target LaTeX table cannot be safely enriched."""


def enrich_tex_table(
    text: str,
    k: int,
    builder: Callable[[int, int], str],
    source_name: str = "<input>",
) -> str:
    """Return *text* with recognized PSPF longtables enriched.

    Only longtables containing the expected legacy header are changed.  A
    numeric-prefix row in such a table must match the complete data-row format
    so malformed input fails without a partially generated output.
    """

    output: list[str] = []
    table_lines: list[tuple[int, str]] = []
    in_longtable = False
    recognized_tables = 0
    data_rows = 0

    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        if not in_longtable:
            if BEGIN_LONGTABLE_RE.search(line):
                in_longtable = True
                table_lines = [(line_number, line)]
            else:
                output.append(line)
            continue

        table_lines.append((line_number, line))
        if END_LONGTABLE_RE.search(line):
            transformed, recognized, rows = _transform_table(table_lines, k, builder, source_name)
            output.extend(transformed)
            recognized_tables += int(recognized)
            data_rows += rows
            table_lines = []
            in_longtable = False

    if table_lines:
        if _is_recognized_table(table_lines):
            first_line = table_lines[0][0]
            raise TexTableError(f"{source_name}:{first_line}: unterminated recognized longtable")
        transformed, recognized, rows = _transform_table(table_lines, k, builder, source_name)
        output.extend(transformed)
        recognized_tables += int(recognized)
        data_rows += rows

    if not recognized_tables:
        raise TexTableError(f"{source_name}: no recognized longtable found")
    if not data_rows:
        raise TexTableError(f"{source_name}: no data rows found in recognized longtable")

    return "".join(output)


def _transform_table(
    table_lines: list[tuple[int, str]],
    k: int,
    builder: Callable[[int, int], str],
    source_name: str,
) -> tuple[list[str], bool, int]:
    if not _is_recognized_table(table_lines):
        return [line for _, line in table_lines], False, 0

    transformed: list[str] = []
    data_rows = 0
    for line_number, line in table_lines:
        if HEADER_RE.match(line):
            transformed.append(line.replace(ORIGINAL_HEADER, OUTPUT_HEADER, 1))
            continue

        if POTENTIAL_DATA_ROW_RE.match(line):
            match = DATA_ROW_RE.match(line)
            if match is None:
                raise TexTableError(f"{source_name}:{line_number}: malformed data row")
            built = builder(int(match["number"]), k)
            transformed.append(
                "".join(
                    (
                        match["indent"],
                        match["length"],
                        match["sep1"],
                        match["number"],
                        match["sep2"],
                        "$",
                        match["expression"],
                        "$ & $",
                        built,
                        "$",
                        match["ending"],
                        match["newline"] or "",
                    )
                )
            )
            data_rows += 1
            continue

        if TARGET_BEGIN_LONGTABLE_RE.match(line):
            replacement = f"p{{{OUTPUT_EXPRESSION_WIDTH}}}| p{{{OUTPUT_EXPRESSION_WIDTH}}}|"
            transformed.append(WIDTH_RE.sub(replacement, line))
            continue

        transformed.append(MULTICOLUMN_CONTINUATION_RE.sub(r"\g<prefix>4\g<suffix>", line))

    return transformed, True, data_rows


def _is_recognized_table(table_lines: list[tuple[int, str]]) -> bool:
    return any(TARGET_BEGIN_LONGTABLE_RE.match(line) for _, line in table_lines) and any(
        HEADER_RE.match(line) for _, line in table_lines
    )


def write_enriched_table(
    input_path: Path,
    output_path: Path,
    k: int,
    builder: Callable[[int, int], str],
) -> None:
    """Transform *input_path* and atomically replace *output_path*."""

    with input_path.open(encoding="utf-8", newline="") as input_file:
        source = input_file.read()
    enriched = enrich_tex_table(source, k, builder, str(input_path))
    temporary_name: str | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=output_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_name = temporary_file.name
            temporary_file.write(enriched)
            temporary_file.flush()
        os.replace(temporary_name, output_path)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

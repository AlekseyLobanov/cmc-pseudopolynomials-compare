import pytest

from pspf import PSPF, LinearFactor, PseudoMonomial
from tex_table import TexTableError, enrich_tex_table, write_enriched_table

INPUT_COLUMNS = "| l| r | p{11cm}|"
INPUT_HEADER = "Номер класса & Длина функции & Мощность & ПСПФ"


def built_pspf(polynomial: set[int], k: int) -> PSPF:
    del polynomial, k
    return PSPF((PseudoMonomial((LinearFactor((1,)),)),), True)


def test_enriches_table_and_preserves_metadata_and_surrounding_latex() -> None:
    source = (
        "before\n"
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\n"
        f"{INPUT_HEADER}\\\\\n"
        "\\endhead\n"
        "\\hline \\multicolumn{4}{r}{continued} \\\\\n"
        "7 & 2 & 560 & $x_1$\\\\\n"
        "\\end{longtable}\n"
        "after\n"
    )

    result = enrich_tex_table(source, 4, built_pspf)

    assert result.startswith("before\n") and result.endswith("after\n")
    assert "\\begin{longtable}{| l| r | r | p{5.5cm}| r | p{5.5cm}|}" in result
    assert (
        "Номер класса & Длина функции & Мощность & Оптимальная ПСПФ & "
        "Длина построенной & Построенная ПСПФ"
    ) in result
    assert "\\multicolumn{6}" in result
    assert "7 & 2 & 560 & $x_1$ & 2 & $x_1 + 1$\\\\" in result


def test_can_enrich_table_without_constructed_length_column() -> None:
    source = (
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\n"
        f"{INPUT_HEADER}\\\\\n"
        "\\hline \\multicolumn{4}{r}{continued} \\\\\n"
        "7 & 2 & 560 & $x_1$\\\\\n"
        "\\end{longtable}\n"
    )

    result = enrich_tex_table(source, 4, built_pspf, include_length=False)

    assert "\\begin{longtable}{| l| r | r | p{5.5cm}| p{5.5cm}|}" in result
    assert (
        "Номер класса & Длина функции & Мощность & Оптимальная ПСПФ & Построенная ПСПФ"
    ) in result
    assert "Длина построенной" not in result
    assert "\\multicolumn{5}" in result
    assert "7 & 2 & 560 & $x_1$ & $x_1 + 1$\\\\" in result


def test_passes_recovered_polynomials_to_builder_in_file_order() -> None:
    source = (
        "до таблицы\r\n"
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\r\n"
        f"{INPUT_HEADER}\\\\\r\n"
        "7 & 2 & 560 & $x_1 + x_2 x_1$\\\\\r\n"
        "8 & 2 & 1680 & $1$\\\\\r\n"
        "\\end{longtable}\r\n"
        "после таблицы\r\n"
    )
    calls: list[tuple[set[int], int]] = []

    def builder(polynomial: set[int], k: int) -> PSPF:
        calls.append((set(polynomial), k))
        return PSPF((), False)

    result = enrich_tex_table(source, 2, builder)

    assert calls == [({0b10, 0b11}, 2), ({0}, 2)]
    assert result.startswith("до таблицы\r\n")
    assert result.endswith("после таблицы\r\n")


def test_malformed_data_does_not_replace_existing_output(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_text(
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\n"
        f"{INPUT_HEADER}\\\\\n"
        "7 & 2 & broken & $x_1$\\\\\n"
        "\\end{longtable}\n",
        encoding="utf-8",
    )
    output_path.write_text("old output", encoding="utf-8")

    with pytest.raises(TexTableError):
        write_enriched_table(input_path, output_path, 4, built_pspf)

    assert output_path.read_text(encoding="utf-8") == "old output"


def test_malformed_math_row_reports_input_path_and_line_number(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_text(
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\n"
        f"{INPUT_HEADER}\\\\\n"
        "7 & 2 & 560 & not-math\\\\\n"
        "\\end{longtable}\n",
        encoding="utf-8",
    )

    with pytest.raises(TexTableError) as error:
        write_enriched_table(input_path, output_path, 4, built_pspf)

    assert str(input_path) in str(error.value)
    assert ":3:" in str(error.value)


def test_invalid_pspf_reports_input_path_and_line_and_preserves_output(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_text(
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\n"
        f"{INPUT_HEADER}\\\\\n"
        "7 & 2 & 560 & $x_5$\\\\\n"
        "\\end{longtable}\n",
        encoding="utf-8",
    )
    output_path.write_text("old output", encoding="utf-8")

    with pytest.raises(TexTableError) as error:
        write_enriched_table(input_path, output_path, 4, built_pspf)

    assert str(input_path) in str(error.value)
    assert ":3:" in str(error.value)
    assert "outside 1..4" in str(error.value)
    assert output_path.read_text(encoding="utf-8") == "old output"


def test_extra_data_cell_reports_input_path_and_line_and_preserves_output(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_text(
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\n"
        f"{INPUT_HEADER}\\\\\n"
        "7 & 2 & 560 & $x_1$ & $unexpected$\\\\\n"
        "\\end{longtable}\n",
        encoding="utf-8",
    )
    output_path.write_text("old output", encoding="utf-8")

    with pytest.raises(TexTableError) as error:
        write_enriched_table(input_path, output_path, 4, built_pspf)

    assert str(input_path) in str(error.value)
    assert ":3:" in str(error.value)
    assert output_path.read_text(encoding="utf-8") == "old output"


def test_path_writer_preserves_crlf_line_endings(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_bytes(
        (
            "before\r\n"
            f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\r\n"
            f"{INPUT_HEADER}\\\\\r\n"
            "7 & 2 & 560 & $x_1$\\\\\r\n"
            "\\end{longtable}\r\n"
            "after\r\n"
        ).encode()
    )

    write_enriched_table(input_path, output_path, 4, built_pspf)

    result = output_path.read_bytes()
    assert b"\n" not in result.replace(b"\r\n", b"")
    assert result.startswith(b"before\r\n")
    assert result.endswith(b"after\r\n")


def test_preserves_header_and_multicolumn_markers_in_comments() -> None:
    recognized_comment_header = f"% {INPUT_HEADER}\n"
    recognized_comment_continuation = "% \\hline \\multicolumn{4}{r}{comment} \\\\\n"
    source = (
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\n"
        f"{INPUT_HEADER}\\\\\n"
        f"{recognized_comment_header}"
        f"{recognized_comment_continuation}"
        "7 & 2 & 560 & $x_1$\\\\\n"
        "\\end{longtable}\n"
    )

    result = enrich_tex_table(source, 4, built_pspf)

    assert recognized_comment_header in result
    assert recognized_comment_continuation in result
    assert result.count("\\multicolumn{6}") == 0


def test_rejects_header_without_expected_column_declaration() -> None:
    source = (
        "\\begin{longtable}{| l| r | p{10cm}|}\n"
        f"{INPUT_HEADER}\\\\\n"
        "7 & 2 & 560 & $x_1$\\\\\n"
        "\\end{longtable}\n"
    )

    with pytest.raises(TexTableError, match="no recognized longtable"):
        enrich_tex_table(source, 4, built_pspf)


def test_rejects_unterminated_recognized_table() -> None:
    source = (
        f"\\begin{{longtable}}{{{INPUT_COLUMNS}}}\n{INPUT_HEADER}\\\\\n7 & 2 & 560 & $x_1$\\\\\n"
    )

    with pytest.raises(TexTableError, match="unterminated recognized longtable"):
        enrich_tex_table(source, 4, built_pspf)

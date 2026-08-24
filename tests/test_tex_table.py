import pytest

from pspf import PSPF, LinearFactor, PseudoMonomial
from tex_table import TexTableError, enrich_tex_table, write_enriched_table


def built_pspf(number: int, k: int) -> PSPF:
    del number, k
    return PSPF((PseudoMonomial((LinearFactor((1,)),)),), True)


def test_enriches_table_and_preserves_surrounding_latex() -> None:
    source = (
        "before\n"
        "\\begin{longtable}{| l| r | p{11cm}|}\n"
        "Длина функции & Номер & ПСПФ\\\\\n"
        "\\endhead\n"
        "\\hline \\multicolumn{3}{r}{continued} \\\\\n"
        "2 & 278 & $x_4$\\\\\n"
        "\\end{longtable}\n"
        "after\n"
    )

    result = enrich_tex_table(source, 4, built_pspf)

    assert result.startswith("before\n") and result.endswith("after\n")
    assert "\\begin{longtable}{| l| r | p{5.5cm}| r | p{5.5cm}|}" in result
    assert (
        "Длина функции & Номер & Оптимальная ПСПФ & Длина построенной & Построенная ПСПФ"
    ) in result
    assert "\\multicolumn{5}" in result
    assert "2 & 278 & $x_4$ & 2 & $x_1 + 1$\\\\" in result


def test_can_enrich_table_without_constructed_length_column() -> None:
    source = (
        "\\begin{longtable}{| l| r | p{11cm}|}\n"
        "Длина функции & Номер & ПСПФ\\\\\n"
        "\\hline \\multicolumn{3}{r}{continued} \\\\\n"
        "2 & 278 & $x_4$\\\\\n"
        "\\end{longtable}\n"
    )

    result = enrich_tex_table(source, 4, built_pspf, include_length=False)

    assert "\\begin{longtable}{| l| r | p{5.5cm}| p{5.5cm}|}" in result
    assert "Длина функции & Номер & Оптимальная ПСПФ & Построенная ПСПФ" in result
    assert "Длина построенной" not in result
    assert "\\multicolumn{4}" in result
    assert "2 & 278 & $x_4$ & $x_1 + 1$\\\\" in result


def test_calls_builder_in_file_order_and_keeps_outside_text_byte_for_byte() -> None:
    source = (
        "до таблицы\r\n"
        "\\begin{longtable}{| l| r | p{11cm}|}\r\n"
        "Длина функции & Номер & ПСПФ\\\\\r\n"
        "3 & 900 & $first$\\\\\r\n"
        "4 & 12 & $second$\\\\\r\n"
        "\\end{longtable}\r\n"
        "после таблицы\r\n"
    )
    calls: list[tuple[int, int]] = []

    def builder(number: int, k: int) -> PSPF:
        calls.append((number, k))
        return PSPF((), bool(number))

    result = enrich_tex_table(source, 7, builder)

    assert calls == [(900, 7), (12, 7)]
    assert result.startswith("до таблицы\r\n")
    assert result.endswith("после таблицы\r\n")


def test_malformed_data_does_not_replace_existing_output(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_text(
        "\\begin{longtable}{| l| r | p{11cm}|}\n"
        "Длина функции & Номер & ПСПФ\\\\\n"
        "2 & broken & $x_1$\\\\\n"
        "\\end{longtable}\n",
        encoding="utf-8",
    )
    output_path.write_text("old output", encoding="utf-8")

    with pytest.raises(TexTableError):
        write_enriched_table(input_path, output_path, 4, lambda number, k: PSPF((), False))

    assert output_path.read_text(encoding="utf-8") == "old output"


def test_malformed_math_row_reports_input_path_and_line_number(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_text(
        "\\begin{longtable}{| l| r | p{11cm}|}\n"
        "Длина функции & Номер & ПСПФ\\\\\n"
        "2 & 278 & not-math\\\\\n"
        "\\end{longtable}\n",
        encoding="utf-8",
    )

    with pytest.raises(TexTableError) as error:
        write_enriched_table(input_path, output_path, 4, lambda number, k: PSPF((), False))

    assert str(input_path) in str(error.value)
    assert ":3:" in str(error.value)


def test_extra_data_cell_reports_input_path_and_line_and_preserves_output(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_text(
        "\\begin{longtable}{| l| r | p{11cm}|}\n"
        "Длина функции & Номер & ПСПФ\\\\\n"
        "2 & 278 & $x_4$ & $unexpected$\\\\\n"
        "\\end{longtable}\n",
        encoding="utf-8",
    )
    output_path.write_text("old output", encoding="utf-8")

    with pytest.raises(TexTableError) as error:
        write_enriched_table(input_path, output_path, 4, lambda number, k: PSPF((), False))

    assert str(input_path) in str(error.value)
    assert ":3:" in str(error.value)
    assert output_path.read_text(encoding="utf-8") == "old output"


def test_path_writer_preserves_crlf_line_endings(tmp_path) -> None:
    input_path = tmp_path / "input.tex"
    output_path = tmp_path / "output.tex"
    input_path.write_bytes(
        (
            "before\r\n"
            "\\begin{longtable}{| l| r | p{11cm}|}\r\n"
            "Длина функции & Номер & ПСПФ\\\\\r\n"
            "2 & 278 & $x_4$\\\\\r\n"
            "\\end{longtable}\r\n"
            "after\r\n"
        ).encode()
    )

    write_enriched_table(input_path, output_path, 4, lambda number, k: PSPF((), False))

    result = output_path.read_bytes()
    assert b"\n" not in result.replace(b"\r\n", b"")
    assert result.startswith(b"before\r\n")
    assert result.endswith(b"after\r\n")


def test_preserves_header_and_multicolumn_markers_in_comments() -> None:
    recognized_comment_header = "% Длина функции & Номер & ПСПФ\n"
    recognized_comment_continuation = "% \\hline \\multicolumn{3}{r}{comment} \\\\\n"
    non_target_comment_header = "% Длина функции & Номер & ПСПФ\n"
    non_target_comment_continuation = "% \\hline \\multicolumn{3}{r}{non-target comment} \\\\\n"
    source = (
        "\\begin{longtable}{| l| r | p{11cm}|}\n"
        "Длина функции & Номер & ПСПФ\\\\\n"
        f"{recognized_comment_header}"
        f"{recognized_comment_continuation}"
        "2 & 278 & $x_4$\\\\\n"
        "\\end{longtable}\n"
        "\\begin{longtable}{| l| r | p{11cm}|}\n"
        f"{non_target_comment_header}"
        f"{non_target_comment_continuation}"
        "\\end{longtable}\n"
    )

    result = enrich_tex_table(source, 4, lambda number, k: PSPF((), False))

    assert recognized_comment_header in result
    assert recognized_comment_continuation in result
    assert non_target_comment_header in result
    assert non_target_comment_continuation in result
    assert result.count("\\multicolumn{4}") == 0


def test_rejects_header_without_expected_three_column_declaration() -> None:
    source = (
        "\\begin{longtable}{| l| r | p{10cm}|}\n"
        "Длина функции & Номер & ПСПФ\\\\\n"
        "2 & 278 & $x_4$\\\\\n"
        "\\end{longtable}\n"
    )

    with pytest.raises(TexTableError, match="no recognized longtable"):
        enrich_tex_table(source, 4, lambda number, k: PSPF((), False))


def test_rejects_unterminated_recognized_table() -> None:
    source = (
        "\\begin{longtable}{| l| r | p{11cm}|}\n"
        "Длина функции & Номер & ПСПФ\\\\\n"
        "2 & 278 & $x_4$\\\\\n"
    )

    with pytest.raises(TexTableError, match="unterminated recognized longtable"):
        enrich_tex_table(source, 4, lambda number, k: PSPF((), False))

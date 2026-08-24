import itertools
import re
from pathlib import Path

import pytest

from boolean_functions import evaluate_zhegalkin
from pspf import PSPF
from pspf_parser import parse_pspf_polynomial
from tex_table import enrich_tex_table

DATA_ROW_RE = re.compile(
    r"^\s*(?P<class_number>\d+)\s*&\s*(?P<length>\d+)\s*&\s*"
    r"(?P<cardinality>\d+)\s*&\s*\$(?P<expression>[^$&]*)\$\s*\\\\\s*$"
)
TOKEN_RE = re.compile(r"x_\d+|[()+]|[01]")


class ExpressionParser:
    """Evaluate the restricted Boolean-expression grammar used by the table."""

    def __init__(self, expression: str, values: dict[int, int]) -> None:
        self.tokens = re.findall(r"x_\d+|[()+]|[01]", expression)
        previous_end = 0
        for match in TOKEN_RE.finditer(expression):
            gap = expression[previous_end : match.start()]
            if gap.strip():
                raise ValueError(f"unsupported character(s): {gap!r}")
            previous_end = match.end()
        gap = expression[previous_end:]
        if gap.strip():
            raise ValueError(f"unsupported character(s): {gap!r}")
        self.values = values
        self.position = 0

    def parse(self) -> int:
        result = self._expression()
        if self.position != len(self.tokens):
            raise ValueError(f"unexpected token: {self.tokens[self.position]}")
        return result

    def _expression(self) -> int:
        result = self._product()
        while self._accept("+"):
            result ^= self._product()
        return result

    def _product(self) -> int:
        result = self._atom()
        while self._starts_atom():
            result &= self._atom()
        return result

    def _atom(self) -> int:
        token = self._next()
        if token == "(":
            result = self._expression()
            if self._next() != ")":
                raise ValueError("missing closing parenthesis")
            return result
        if token == "0" or token == "1":
            return int(token)
        if token.startswith("x_"):
            return self.values[int(token[2:])]
        raise ValueError(f"unexpected token: {token}")

    def _starts_atom(self) -> bool:
        if self.position == len(self.tokens):
            return False
        token = self.tokens[self.position]
        return token == "(" or token in {"0", "1"} or token.startswith("x_")

    def _accept(self, token: str) -> bool:
        if self.position < len(self.tokens) and self.tokens[self.position] == token:
            self.position += 1
            return True
        return False

    def _next(self) -> str:
        if self.position == len(self.tokens):
            raise ValueError("unexpected end of expression")
        token = self.tokens[self.position]
        self.position += 1
        return token


def evaluate_reference_expression(expression: str, values: dict[int, int]) -> int:
    return ExpressionParser(expression, values).parse()


def load_reference_rows() -> dict[int, str]:
    source = Path(__file__).parents[1] / "references" / "tex_data.txt"
    rows: dict[int, str] = {}
    for line in source.read_text(encoding="utf-8").splitlines():
        match = DATA_ROW_RE.match(line)
        if match:
            rows[int(match["class_number"])] = match["expression"]
    return rows


def test_expression_parser_evaluates_xor_and_adjacent_and() -> None:
    assert evaluate_reference_expression("x_1 + x_2 x_1", {1: 1, 2: 0}) == 1


def test_expression_parser_rejects_unsupported_characters() -> None:
    with pytest.raises(ValueError, match="unsupported character"):
        evaluate_reference_expression("x_1 - x_2", {1: 1, 2: 0})


def test_reference_pspfs_recover_expected_zhegalkin_polynomials() -> None:
    rows = load_reference_rows()
    assert parse_pspf_polynomial(rows[1], 4) == set()
    assert parse_pspf_polynomial(rows[2], 4) == {0b1111}
    assert parse_pspf_polynomial(rows[3], 4) == {0b1110}


def test_recovered_reference_polynomials_match_independent_evaluation() -> None:
    for expression in load_reference_rows().values():
        polynomial = parse_pspf_polynomial(expression, 4)
        for assignment_mask, assignment in enumerate(itertools.product((0, 1), repeat=4)):
            values = {index: value for index, value in enumerate(assignment, start=1)}
            assert evaluate_zhegalkin(polynomial, assignment_mask) == (
                evaluate_reference_expression(expression, values)
            )


def test_all_reference_rows_parse_and_enrich() -> None:
    rows = load_reference_rows()
    polynomials: list[set[int]] = []

    def record_polynomial(polynomial: set[int], k: int) -> PSPF:
        del k
        polynomials.append(set(polynomial))
        return PSPF((), False)

    source = (Path(__file__).parents[1] / "references" / "tex_data.txt").read_text(encoding="utf-8")
    enriched = enrich_tex_table(source, 4, record_polynomial)
    assert len(rows) == 32
    assert len(polynomials) == 32
    assert polynomials[0] == set()
    data_rows = [line for line in enriched.splitlines() if re.match(r"^\s*\d+\s*&", line)]
    assert len(data_rows) == 32
    assert all(line.count("&") == 5 for line in data_rows)

"""Parse formatted PSPF expressions into Zhegalkin polynomials."""

from __future__ import annotations

import re

from pspf import multiply_polynomials

TOKEN_RE = re.compile(r"x_\d+|[()+]|[01]")


class PSPFParseError(ValueError):
    """Raised when a PSPF expression does not match the supported grammar."""


def parse_pspf_polynomial(expression: str, k: int) -> set[int]:
    """Return the Zhegalkin polynomial represented by *expression*."""
    if k <= 0:
        raise PSPFParseError("k must be a positive integer")
    if not expression.strip():
        raise PSPFParseError("empty expression")
    return _PolynomialParser(expression, k).parse()


class _PolynomialParser:
    def __init__(self, expression: str, k: int) -> None:
        self.tokens = self._tokenize(expression)
        self.k = k
        self.position = 0

    @staticmethod
    def _tokenize(expression: str) -> list[str]:
        tokens: list[str] = []
        previous_end = 0
        for match in TOKEN_RE.finditer(expression):
            gap = expression[previous_end : match.start()]
            if gap.strip():
                raise PSPFParseError(f"unsupported character(s): {gap!r}")
            tokens.append(match.group())
            previous_end = match.end()
        gap = expression[previous_end:]
        if gap.strip():
            raise PSPFParseError(f"unsupported character(s): {gap!r}")
        return tokens

    def parse(self) -> set[int]:
        result = self._expression()
        if self.position != len(self.tokens):
            raise PSPFParseError(f"unexpected token: {self.tokens[self.position]}")
        return result

    def _expression(self) -> set[int]:
        result = self._product()
        while self._accept("+"):
            result.symmetric_difference_update(self._product())
        return result

    def _product(self) -> set[int]:
        result = self._atom()
        while self._starts_atom():
            result = multiply_polynomials(result, self._atom())
        return result

    def _atom(self) -> set[int]:
        token = self._next()
        if token == "(":
            result = self._expression()
            if self.position == len(self.tokens) or self._next() != ")":
                raise PSPFParseError("missing closing parenthesis")
            return result
        if token == "0":
            return set()
        if token == "1":
            return {0}
        if token.startswith("x_"):
            variable = int(token[2:])
            if not 1 <= variable <= self.k:
                raise PSPFParseError(f"variable x_{variable} is outside 1..{self.k}")
            return {1 << (self.k - variable)}
        raise PSPFParseError(f"unexpected token: {token}")

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
            raise PSPFParseError("unexpected end of expression")
        token = self.tokens[self.position]
        self.position += 1
        return token

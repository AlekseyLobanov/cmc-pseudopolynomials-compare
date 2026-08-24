import pytest

from pspf_parser import PSPFParseError, parse_pspf_polynomial


def test_parses_xor_and_adjacent_multiplication_into_zhegalkin_polynomial() -> None:
    assert parse_pspf_polynomial("x_1 + x_2 x_1", 2) == {0b10, 0b11}


def test_multiplication_uses_boolean_idempotence_and_mod_two_cancellation() -> None:
    assert parse_pspf_polynomial("(x_1 + x_2) (x_1 + x_2)", 2) == {0b10, 0b01}


def test_parses_nested_factors_and_constants() -> None:
    assert parse_pspf_polynomial("1 + x_3 ((x_1 + x_2) (x_2 + 1))", 3) == {
        0b000,
        0b111,
        0b101,
    }


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("x_5", "outside 1..4"),
        ("x_1 - x_2", "unsupported character"),
        ("(x_1 + x_2", "closing parenthesis"),
        ("", "empty expression"),
    ],
)
def test_rejects_invalid_pspf_expression(expression: str, message: str) -> None:
    with pytest.raises(PSPFParseError, match=message):
        parse_pspf_polynomial(expression, 4)

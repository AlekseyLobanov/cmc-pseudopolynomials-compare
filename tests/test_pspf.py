import pytest

from boolean_functions import evaluate_zhegalkin, zhegalkin_from_number
from pspf import (
    PSPF,
    LinearFactor,
    PseudoMonomial,
    build_pspf,
    expand_pseudomonomial,
    format_pspf,
    multiply_polynomials,
)


def test_multiplication_uses_boolean_idempotence_and_mod_two() -> None:
    assert multiply_polynomials({0b01, 0b10}, {0b01, 0b10}) == {0b01, 0b10}


def test_expands_pseudomonomial() -> None:
    term = PseudoMonomial((LinearFactor((3, 1)), LinearFactor((3, 2))))
    assert expand_pseudomonomial(term, 3) == {0b101, 0b110, 0b001, 0b011}


def test_formats_factors_and_constant_deterministically() -> None:
    term = PseudoMonomial((LinearFactor((3, 2)), LinearFactor((3, 1))))
    assert format_pspf(PSPF((term,), True)) == "(x_3 + x_2) (x_3 + x_1) + 1"
    assert format_pspf(PSPF((), False)) == "0"


def expand_pspf(result: PSPF, k: int) -> set[int]:
    polynomial: set[int] = {0} if result.constant else set()
    for term in result.terms:
        polynomial.symmetric_difference_update(expand_pseudomonomial(term, k))
    return polynomial


def test_article_example_has_expected_deterministic_terms() -> None:
    polynomial = {0b110, 0b101, 0b011, 0b100}
    result = build_pspf(polynomial, 3)
    assert format_pspf(result) == "(x_3 + x_2) (x_3 + x_1) + x_3 + x_1"
    assert expand_pspf(result, 3) == polynomial


@pytest.mark.parametrize(
    ("k", "number"),
    [(1, 0), (1, 1), (2, 6), (3, 105), (4, 278), (4, 27031), (4, 59521)],
)
def test_constructed_pspf_is_equivalent(k: int, number: int) -> None:
    source = zhegalkin_from_number(number, k)
    expanded = expand_pspf(build_pspf(source, k), k)
    assert [evaluate_zhegalkin(expanded, mask) for mask in range(1 << k)] == [
        evaluate_zhegalkin(source, mask) for mask in range(1 << k)
    ]


@pytest.mark.parametrize("polynomial", [{-1}, {4}])
def test_build_rejects_masks_outside_the_variable_width(polynomial: set[int]) -> None:
    with pytest.raises(ValueError):
        build_pspf(polynomial, 2)


def test_build_rejects_non_positive_variable_count() -> None:
    with pytest.raises(ValueError):
        build_pspf(set(), 0)

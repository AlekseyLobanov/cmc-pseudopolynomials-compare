import pytest

from boolean_functions import (
    BooleanFunctionError,
    evaluate_zhegalkin,
    number_from_truth_table,
    truth_table_from_number,
    validate_function_number,
    zhegalkin_from_number,
    zhegalkin_from_truth_table,
)


@pytest.mark.parametrize("number", [-1, 65536])
def test_rejects_invalid_four_argument_number(number: int) -> None:
    with pytest.raises(BooleanFunctionError):
        validate_function_number(number, 4)


def test_rejects_non_positive_k() -> None:
    with pytest.raises(BooleanFunctionError):
        validate_function_number(0, 0)


def test_number_uses_first_truth_value_as_most_significant_bit() -> None:
    values = truth_table_from_number(1, 4)
    assert values == [0] * 15 + [1]
    assert number_from_truth_table(values) == 1


def test_number_rejects_non_binary_truth_table_values() -> None:
    with pytest.raises(BooleanFunctionError):
        number_from_truth_table([0, 2])


def test_four_variable_parity_number() -> None:
    values = truth_table_from_number(27030, 4)
    assert values == [mask.bit_count() % 2 for mask in range(16)]


def test_zhegalkin_for_four_variable_conjunction() -> None:
    assert zhegalkin_from_number(1, 4) == {0b1111}


def test_number_and_zhegalkin_for_four_variable_first_truth_value() -> None:
    assert truth_table_from_number(32768, 4) == [1] + [0] * 15
    assert zhegalkin_from_number(32768, 4) == set(range(16))


def test_zhegalkin_for_constant_one() -> None:
    assert zhegalkin_from_number(65535, 4) == {0}


def test_zhegalkin_mobius_transform_for_two_variables() -> None:
    # f(00), f(01), f(10), f(11) = 0, 1, 1, 1 is x_1 + x_2 + x_1*x_2.
    assert zhegalkin_from_truth_table([0, 1, 1, 1]) == {0b01, 0b10, 0b11}


@pytest.mark.parametrize("values", [[], [0, 1, 0], [0, 2]])
def test_zhegalkin_rejects_invalid_truth_tables(values: list[int]) -> None:
    with pytest.raises(BooleanFunctionError):
        zhegalkin_from_truth_table(values)


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_zhegalkin_round_trip_for_deterministic_numbers(k: int) -> None:
    maximum = (1 << (1 << k)) - 1
    for number in {0, 1, maximum // 3, maximum // 2, maximum}:
        polynomial = zhegalkin_from_number(number, k)
        rebuilt = [evaluate_zhegalkin(polynomial, assignment) for assignment in range(1 << k)]
        assert number_from_truth_table(rebuilt) == number

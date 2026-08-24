from collections.abc import Collection, Sequence


class BooleanFunctionError(ValueError):
    """Invalid Boolean function dimensions or number."""


def validate_function_number(number: int, k: int) -> None:
    if k <= 0:
        raise BooleanFunctionError("k must be a positive integer")
    if number < 0:
        raise BooleanFunctionError("function number must be non-negative")
    value_count = 1 << k
    if number.bit_length() > value_count:
        raise BooleanFunctionError(
            f"function number does not fit a truth table with {value_count} values"
        )


def truth_table_from_number(number: int, k: int) -> list[int]:
    validate_function_number(number, k)
    value_count = 1 << k
    return [(number >> (value_count - 1 - mask)) & 1 for mask in range(value_count)]


def number_from_truth_table(values: Sequence[int]) -> int:
    number = 0
    for value in values:
        if value not in (0, 1):
            raise BooleanFunctionError("truth-table values must be zero or one")
        number = (number << 1) | value
    return number


def zhegalkin_from_truth_table(values: Sequence[int]) -> set[int]:
    size = len(values)
    if size == 0 or size & (size - 1):
        raise BooleanFunctionError("truth table length must be a positive power of two")
    coefficients = list(values)
    if any(value not in (0, 1) for value in coefficients):
        raise BooleanFunctionError("truth-table values must be zero or one")
    bit = 1
    while bit < size:
        for mask in range(size):
            if mask & bit:
                coefficients[mask] ^= coefficients[mask ^ bit]
        bit <<= 1
    return {mask for mask, coefficient in enumerate(coefficients) if coefficient}


def zhegalkin_from_number(number: int, k: int) -> set[int]:
    return zhegalkin_from_truth_table(truth_table_from_number(number, k))


def evaluate_zhegalkin(polynomial: Collection[int], assignment_mask: int) -> int:
    return sum(monomial & assignment_mask == monomial for monomial in polynomial) % 2

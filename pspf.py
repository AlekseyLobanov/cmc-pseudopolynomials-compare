from dataclasses import dataclass


@dataclass(frozen=True)
class LinearFactor:
    variables: tuple[int, ...]


@dataclass(frozen=True)
class PseudoMonomial:
    factors: tuple[LinearFactor, ...]


@dataclass(frozen=True)
class PSPF:
    terms: tuple[PseudoMonomial, ...]
    constant: bool = False


def multiply_polynomials(left: set[int], right: set[int]) -> set[int]:
    result: set[int] = set()
    for left_mask in left:
        for right_mask in right:
            product = left_mask | right_mask
            if product in result:
                result.remove(product)
            else:
                result.add(product)
    return result


def _variable_mask(variable: int, k: int) -> int:
    return 1 << (k - variable)


def expand_pseudomonomial(term: PseudoMonomial, k: int) -> set[int]:
    result = {0}
    for factor in term.factors:
        factor_polynomial = {_variable_mask(variable, k) for variable in factor.variables}
        result = multiply_polynomials(result, factor_polynomial)
    return result


def _format_factor(factor: LinearFactor, in_product: bool) -> str:
    expression = " + ".join(f"x_{variable}" for variable in factor.variables)
    return f"({expression})" if in_product and len(factor.variables) > 1 else expression


def format_pspf(pspf: PSPF) -> str:
    expressions = []
    for term in pspf.terms:
        in_product = len(term.factors) > 1
        expressions.append(" ".join(_format_factor(factor, in_product) for factor in term.factors))
    if pspf.constant:
        expressions.append("1")
    return " + ".join(expressions) if expressions else "0"


def build_pspf(polynomial: set[int], k: int) -> PSPF:
    if k <= 0:
        raise ValueError("k must be a positive integer")
    if any(mask < 0 or mask >= 1 << k for mask in polynomial):
        raise ValueError("polynomial masks must fit within k variables")

    current = set(polynomial)
    terms: list[PseudoMonomial] = []
    while any(current_mask != 0 for current_mask in current):
        leading = max(
            (mask for mask in current if mask),
            key=lambda mask: (mask.bit_count(), mask),
        )
        factors = []
        for variable in range(k, 0, -1):
            variable_bit = _variable_mask(variable, k)
            if not leading & variable_bit:
                continue
            variables = [variable]
            for replacement in range(k, 0, -1):
                replacement_bit = _variable_mask(replacement, k)
                if leading & replacement_bit:
                    continue
                neighbor = (leading ^ variable_bit) | replacement_bit
                if neighbor in current:
                    variables.append(replacement)
            factors.append(LinearFactor(tuple(sorted(variables, reverse=True))))
        term = PseudoMonomial(tuple(factors))
        current.symmetric_difference_update(expand_pseudomonomial(term, k))
        terms.append(term)
    return PSPF(tuple(terms), 0 in current)

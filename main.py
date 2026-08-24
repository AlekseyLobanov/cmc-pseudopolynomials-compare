"""Command-line tools for constructing pseudo-polynomial expressions."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from boolean_functions import BooleanFunctionError, zhegalkin_from_number
from pspf import build_pspf, format_pspf
from tex_table import TexTableError, write_enriched_table

WARNING = "warning: k >= 5; computation may require exponential time and memory"


def calculate_expression(number: int, k: int) -> str:
    """Construct a formatted PSPF for a Boolean function number."""
    polynomial = zhegalkin_from_number(number, k)
    return format_pspf(build_pspf(polynomial, k))


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    calculate_parser = subparsers.add_parser("calculate")
    calculate_parser.add_argument("--k", type=int, default=4)
    calculate_parser.add_argument("number", type=int)

    table_parser = subparsers.add_parser("generate_table")
    table_parser.add_argument("--k", type=int, default=4)
    table_parser.add_argument("input", type=Path)
    table_parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected CLI command and return its process status."""
    args = build_parser().parse_args(argv)
    if args.k >= 5:
        print(WARNING, file=sys.stderr)

    try:
        if args.k <= 0:
            raise BooleanFunctionError("k must be a positive integer")
        if args.command == "calculate":
            print(calculate_expression(args.number, args.k))
        else:
            write_enriched_table(args.input, args.out, args.k, calculate_expression)
    except (BooleanFunctionError, TexTableError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

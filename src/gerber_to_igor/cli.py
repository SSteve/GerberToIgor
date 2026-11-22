import argparse
import logging
import re
from collections.abc import Iterator

from .gerber import Gerber
from .gerber_token import Token
from .point import Units


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("gerberfile", help="Gerber file to translate.")

    # Length Units are "Hundredths of Inches", "Thousandths of Inches", and "Tenths of Millimeters"
    parser.add_argument(
        "-u",
        "--units",
        help="Units: 1 = tenths of millimeters, 2 = hundredths of inches, 3 = thousandths of inches",
        type=int,
        choices=[unit.value for unit in Units],
        default=Units.HUNDREDTHS.value,
    )

    # Mark tool offset
    parser.add_argument(
        "-m", "--markoffset", help="Mark tool offset (in inches).", default="0,0"
    )

    # Cut tool offset
    parser.add_argument(
        "-c", "--cutoffset", help="Cut tool offset (in inches).", default="0,0"
    )

    # Drill tool offset
    parser.add_argument(
        "-d", "--drilloffset", help="Drill tool offset (in inches).", default="0,0"
    )

    # Verbose flag
    parser.add_argument(
        "-v", "--verbose", help="Display progress to terminal.", action="store_true"
    )

    return parser


def gerber_tokenizer(input_string: str) -> Iterator[Token]:
    commands = re.findall(r"([A-WZ]\d*|X-?\d+Y-?\d+)", input_string)
    for cmd in commands:
        if cmd.startswith("X"):
            x, y = map(int, re.findall(r"-?\d+", cmd))
            yield Token.from_coordinate(x, y)
        else:
            # Some commands (e.g. A, B) have no number.
            value = int(cmd[1:]) if len(cmd) > 1 else None
            yield Token.from_command(cmd[0], value)


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    with open(args.gerberfile) as gerber_file:
        text = gerber_file.read()

    with Gerber(
        args.gerberfile,
        Units(args.units),
        args.cutoffset,
        args.markoffset,
        args.drilloffset,
    ) as gerber:
        for token in gerber_tokenizer(text):
            gerber.command(token)

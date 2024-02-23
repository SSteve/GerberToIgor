import argparse
import re
from typing import Iterator

from gerber import Gerber
from gerber_token import Token


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("gerberfile", help="Gerber file to translate.")

    # Length Units are "Hundredths of Inches", "Thousandths of Inches", and "Tenths of Millimeters"
    parser.add_argument(
        "-u",
        "--units",
        help="Units: 1 = tenths of millimeters, 2 = hundredths of inches, 3 = thousandths of inches",
        default=2,
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
    parser.add_argument("-v", "--verbose", help="Display progress to terminal.")

    return parser


def gerber_tokenizer(input_string: str) -> Iterator[Token]:
    commands = re.findall(r"([A-W,Z]\d*|X-?\d+Y-?\d+)", input_string)
    for cmd in commands:
        if cmd.startswith("X"):
            x, y = map(int, re.findall(r"-?\d+", cmd))
            yield Token.from_coordinate(x, y)
        else:
            yield Token.from_command(cmd[0], cmd[1:])


if __name__ == "__main__":
    parser = build_arg_parser()
    args = parser.parse_args()

    gerber = Gerber(
        args.gerberfile, args.units, args.cutoffset, args.markoffset, args.drilloffset
    )

    with open(args.gerberfile, "r") as gerber_file:
        for token in gerber_tokenizer(gerber_file.read()):
            gerber.command(token)

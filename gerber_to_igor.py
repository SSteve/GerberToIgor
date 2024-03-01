import argparse
import os
import re
from typing import Iterator

import tomllib

from gerber import Gerber
from gerber_token import Token


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("gerberfile", help="Gerber file to translate.")

    # Length Units are "Hundredths of Inches", "Thousandths of Inches", and "Tenths of Millimeters"
    parser.add_argument(
        "-u",
        "--units",
        help="Units: 1 = tenths of millimeters, 2 = hundredths of inches, 3 = thousandths of inches. (Default: 2)",
        choices=[1, 2, 3],
    )

    # Mark tool offset
    parser.add_argument(
        "-m", "--markoffset", help="Mark tool offset (in inches). (Default 0,0)"
    )

    # Cut tool offset
    parser.add_argument(
        "-c", "--cutoffset", help="Cut tool offset (in inches). (Default 0,0)"
    )

    # Drill tool offset
    parser.add_argument(
        "-d", "--drilloffset", help="Drill tool offset (in inches). (Default 0,0)"
    )

    # Verbose flag
    parser.add_argument(
        "-v", "--verbose", help="Display progress to terminal.", action="store_true"
    )

    return parser


def gerber_tokenizer(input_string: str) -> Iterator[Token]:
    commands = re.findall(r"([A-W,Z/]\d*|X-?\d+Y-?\d+)", input_string)
    for cmd in commands:
        if cmd.startswith("X"):
            x, y = map(int, re.findall(r"-?\d+", cmd))
            yield Token.from_coordinate(x, y)
        else:
            yield Token.from_command(cmd[0], int(cmd[1:]))


if __name__ == "__main__":
    file_options = {}
    if os.path.exists("gerber_to_igor.toml"):
        with open("gerber_to_igor.toml", "rb") as f:
            file_options = tomllib.load(f)

    parser = build_arg_parser()
    args = parser.parse_args()

    gerber = Gerber(
        args.gerberfile,
        args.units or file_options.get("units", 2),
        args.cutoffset or file_options.get("cutoffset", "0,0"),
        args.markoffset or file_options.get("markoffset", "0,0"),
        args.drilloffset or file_options.get("drilloffset", "0,0"),
        args.verbose or file_options.get("verbose", False),
    )

    with open(args.gerberfile, "r") as gerber_file:
        for token in gerber_tokenizer(gerber_file.read()):
            should_stop = gerber.command(token)
            if should_stop:
                break

    gerber.finish()

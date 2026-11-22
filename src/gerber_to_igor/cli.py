import argparse
import logging
import re
from collections.abc import Iterator

from .gerber import Gerber
from .gerber_token import Token
from .point import Units

logger = logging.getLogger(__name__)


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


# A block (text between "*" end-of-block markers) is an optional coordinate,
# either axis of which may be omitted, followed by zero or more commands.
BLOCK = re.compile(r"(?:X([-+]?\d+))?(?:Y([-+]?\d+))?((?:[A-WZ]\d*)*)")
COMMAND = re.compile(r"([A-WZ])(\d*)")


def gerber_tokenizer(input_string: str) -> Iterator[Token]:
    for raw_block in input_string.split("*"):
        block = re.sub(r"\s+", "", raw_block)
        if not block:
            continue
        match = BLOCK.fullmatch(block)
        if not match:
            # E.g. label text following an M31 block, which isn't supported.
            logger.warning(f"Skipping unrecognized block {raw_block.strip()!r}")
            continue
        x, y, commands = match.groups()
        if x is not None or y is not None:
            yield Token.from_coordinate(
                None if x is None else int(x), None if y is None else int(y)
            )
        for code, digits in COMMAND.findall(commands):
            # Some commands (e.g. A, B) have no number.
            yield Token.from_command(code, int(digits) if digits else None)


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

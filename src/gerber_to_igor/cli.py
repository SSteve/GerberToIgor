import argparse
import logging
import math
import re
import sys
from collections.abc import Iterator
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .gerber import Gerber
from .gerber_token import Token
from .point import Point, Units

logger = logging.getLogger(__name__)


def offset(text: str) -> Point:
    """Parse an "X,Y" tool offset in inches."""
    try:
        point = Point.from_text(text)
    except ValueError:
        point = None
    if point is None or not (math.isfinite(point.x) and math.isfinite(point.y)):
        raise argparse.ArgumentTypeError(
            f"expected X,Y in inches (for example 1.5,-2), got {text!r}"
        )
    return point


def default_output_path(gerber_path: Path) -> Path:
    return gerber_path.with_suffix(".itx")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gerber-to-igor",
        description="Convert a Gerber cutter file to an Igor Pro text file (.itx) "
        "that plots the mark, cut, drill, and notch tool paths.",
        epilog="Attach negative offsets to the option, as in --cutoffset=-1,2 "
        "or -c-1,2 (a separate -c -1,2 needs Python 3.14 or newer).",
    )
    parser.add_argument("gerberfile", type=Path, help="Gerber file to convert.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Igor text file to write (default: the input path with .itx).",
    )
    parser.add_argument(
        "-u",
        "--units",
        help="Coordinate units: 1 = tenths of millimeters, "
        "2 = hundredths of inches (default), 3 = thousandths of inches. "
        "G70, G71, or G91 in the file overrides this.",
        type=int,
        choices=[unit.value for unit in Units],
        default=Units.HUNDREDTHS.value,
    )
    for flag, name, tool in [
        ("-m", "markoffset", "Mark"),
        ("-c", "cutoffset", "Cut (and notch)"),
        ("-d", "drilloffset", "Drill"),
    ]:
        parser.add_argument(
            flag,
            f"--{name}",
            type=offset,
            default=Point(0, 0),
            metavar="X,Y",
            help=f"{tool} tool offset in inches (default: 0,0).",
        )
    parser.add_argument(
        "-v", "--verbose", help="Display progress to terminal.", action="store_true"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {package_version()}"
    )
    return parser


def package_version() -> str:
    try:
        return version("gerber-to-igor")
    except PackageNotFoundError:
        return "unknown"


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


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    def fail(message: str) -> int:
        print(f"{parser.prog}: error: {message}", file=sys.stderr)
        return 1

    gerber_path: Path = args.gerberfile
    output_path: Path = args.output or default_output_path(gerber_path)

    if output_path.resolve() == gerber_path.resolve():
        return fail(f"output file would overwrite the input file: {output_path}")

    try:
        # Gerber files are ASCII; latin-1 accepts any byte, so stray
        # non-ASCII bytes show up as unrecognized blocks instead of crashing.
        text = gerber_path.read_text(encoding="latin-1")
    except OSError as error:
        return fail(f"can't read {gerber_path}: {error.strerror}")

    try:
        gerber = Gerber(
            str(output_path),
            Units(args.units),
            mark_offset=args.markoffset,
            cut_offset=args.cutoffset,
            drill_offset=args.drilloffset,
        )
    except OSError as error:
        return fail(f"can't write {output_path}: {error.strerror}")

    with gerber:
        for token in gerber_tokenizer(text):
            gerber.command(token)

    logger.debug(f"Wrote {output_path}")
    return 0

import argparse
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Self


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

    # Cut tool offset

    # Drill tool offset

    # Verbose flag
    parser.add_argument("-v", "--verbose", help="Display progress to terminal.")

    return parser


class Units(Enum):
    TENTHS = 1
    HUNDREDTHS = 2
    THOUSANDTHS = 3


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    @staticmethod
    def from_xy(x: int, y: int, units: Units):
        match units:
            case Units.TENTHS:
                return Point(0.0039 * x, 0.0039 * y)
            case Units.HUNDREDTHS:
                return Point(0.01 * x, 0.01 * y)
            case Units.THOUSANDTHS:
                return Point(0.001 * x, 0.001 * y)


class Token:
    code: str
    value: int
    x: int
    y: int
    is_coordinate: bool

    @staticmethod
    def from_command(code: str, value: int | None) -> Self:
        return Token(code=code, value=value)

    @staticmethod
    def from_coordinate(x: int, y: int) -> Self:
        return Token(x=x, y=y)

    def __init__(
        self,
        code: str = "",
        value: int | None = None,
        x: int | None = None,
        y: int | None = None,
    ):
        self.code = code
        self.value = value
        self.x = x
        self.y = y
        self.is_coordinate = x is not None

    def __repr__(self):
        if self.is_coordinate:
            return f"({self.x},{self.y})"
        elif self.value:
            return f"{self.code}{self.value}"
        else:
            return self.code


def gerber_tokenizer(input_string: str) -> Iterator[Token]:
    commands = re.findall(r"([A-W,Z]\d*|X-?\d+Y-?\d+)", input_string)
    for cmd in commands:
        if cmd.startswith("X"):
            x, y = map(int, re.findall(r"-?\d+", cmd))
            yield Token.from_coordinate(x, y)
        else:
            yield Token.from_command(cmd[0], cmd[1:])


class Gerber:
    units: Units

    def __init__(self, units: int):
        match units:
            case 1:
                self.units = Units.TENTHS
            case 3:
                self.units = Units.THOUSANDTHS
            case _:
                # Default to hundredths.
                self.units = Units.HUNDREDTHS


if __name__ == "__main__":
    parser = build_arg_parser()
    args = parser.parse_args()

    gerber = Gerber(args.units)

    with open(args.gerberfile, "r") as gerber:
        for token in gerber_tokenizer(gerber.read()):
            print(token)

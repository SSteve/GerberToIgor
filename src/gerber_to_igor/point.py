from dataclasses import dataclass
from enum import Enum
from typing import Self


class Units(Enum):
    TENTHS = 1
    HUNDREDTHS = 2
    THOUSANDTHS = 3


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    @staticmethod
    def from_xy(x: int, y: int, units: Units) -> Self:
        match units:
            case Units.TENTHS:
                return Point(0.0039 * x, 0.0039 * y)
            case Units.HUNDREDTHS:
                return Point(0.01 * x, 0.01 * y)
            case Units.THOUSANDTHS:
                return Point(0.001 * x, 0.001 * y)

    def from_text(text: str) -> Self:
        x_text, y_text = text.split(",")
        x = float(x_text)
        y = float(y_text)
        return Point(x, y)

    def __add__(self, other: Self) -> Self:
        return Point(self.x + other.x, self.y + other.y)

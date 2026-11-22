from dataclasses import dataclass
from enum import Enum
from typing import Self


class Units(Enum):
    TENTHS = 1
    HUNDREDTHS = 2
    THOUSANDTHS = 3


# Inches per Gerber coordinate unit.
INCHES_PER_UNIT = {
    Units.TENTHS: 0.1 / 25.4,
    Units.HUNDREDTHS: 0.01,
    Units.THOUSANDTHS: 0.001,
}


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    @classmethod
    def from_xy(cls, x: int, y: int, units: Units) -> Self:
        try:
            scale = INCHES_PER_UNIT[units]
        except KeyError:
            raise ValueError(f"Unknown units: {units!r}") from None
        return cls(scale * x, scale * y)

    @classmethod
    def from_text(cls, text: str) -> Self:
        x_text, y_text = text.split(",")
        return cls(float(x_text), float(y_text))

    def __add__(self, other: Self) -> Self:
        return type(self)(self.x + other.x, self.y + other.y)

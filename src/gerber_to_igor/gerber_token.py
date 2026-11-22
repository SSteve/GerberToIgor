from typing import Self


class Token:
    code: str
    value: int | None
    x: int | None
    y: int | None
    is_coordinate: bool

    @classmethod
    def from_command(cls, code: str, value: int | None) -> Self:
        return cls(code=code, value=value)

    @classmethod
    def from_coordinate(cls, x: int, y: int) -> Self:
        return cls(x=x, y=y)

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
        elif self.value is not None:
            return f"{self.code}{self.value}"
        else:
            return self.code

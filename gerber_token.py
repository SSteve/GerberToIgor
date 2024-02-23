from typing import Self


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

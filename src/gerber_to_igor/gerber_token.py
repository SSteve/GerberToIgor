from typing import Self


class Token:
    """A Gerber command (letter + optional number) or an X/Y coordinate.

    Either axis of a coordinate may be omitted (None), meaning "unchanged".
    """

    code: str
    value: int | None
    x: int | None
    y: int | None
    is_coordinate: bool

    @classmethod
    def from_command(cls, code: str, value: int | None) -> Self:
        return cls(code=code, value=value)

    @classmethod
    def from_coordinate(cls, x: int | None, y: int | None) -> Self:
        if x is None and y is None:
            raise ValueError("A coordinate needs at least one of X or Y")
        return cls(x=x, y=y, is_coordinate=True)

    def __init__(
        self,
        code: str = "",
        value: int | None = None,
        x: int | None = None,
        y: int | None = None,
        is_coordinate: bool = False,
    ):
        self.code = code
        self.value = value
        self.x = x
        self.y = y
        self.is_coordinate = is_coordinate

    def __repr__(self):
        if self.is_coordinate:
            x = "_" if self.x is None else self.x
            y = "_" if self.y is None else self.y
            return f"({x},{y})"
        elif self.value is not None:
            return f"{self.code}{self.value}"
        else:
            return self.code

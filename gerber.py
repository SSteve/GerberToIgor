import os
from dataclasses import dataclass
from enum import Enum
from typing import Self

from gerber_token import Token
from igor_writer import Igor
from point import Point, Units


class Tool(Enum):
    NONE = -1
    MARK = 0
    CUT = 1


class Gerber:
    fileName: str
    units: Units
    cutoffset: Point
    markoffset: Point
    drilloffset: Point
    current_path: list[Point]
    current_tool: Tool
    tool_is_down: bool

    igor: Igor

    def tool_up(self):
        self.igor.plot_path(self.current_tool, self.current_path)
        self.current_path = []
        self.current_tool = Tool.NONE
        self.tool_is_down = False

    def __init__(
        self,
        fileName: str,
        units: int,
        cutoffset: str,
        markoffset: str,
        drilloffset: str,
    ):
        basename, _ = os.path.splitext(fileName)
        self.igor = Igor(basename + ".itx")

        match units:
            case 1:
                self.units = Units.TENTHS
            case 3:
                self.units = Units.THOUSANDTHS
            case _:
                # Default to hundredths.
                self.units = Units.HUNDREDTHS

        self.cutoffset = Point.from_text(cutoffset)
        self.markoffset = Point.from_text(markoffset)
        self.drilloffset = Point.from_text(drilloffset)

        self.current_path = []
        self.current_tool = Tool.NONE
        self.tool_is_down = False

    def command(self, cmd: Token):
        print(cmd)

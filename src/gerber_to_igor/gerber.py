import logging
import os
from types import TracebackType
from typing import Self

from .gerber_token import Token
from .igor_writer import Igor
from .point import Point, Units
from .tool import Tool

logger = logging.getLogger(__name__)


class Gerber:
    fileName: str
    units: Units
    offsets: list[Point]

    origin: Point
    current_path: list[Point]
    current_location: Point
    current_tool: Tool
    tool_is_down: bool
    pattern_number = -1
    file_number = -1

    igor: Igor

    def __init__(
        self,
        fileName: str,
        units: Units,
        cutoffset: str,
        markoffset: str,
        drilloffset: str,
    ):
        self.units = units

        # Indexed by Tool.value: MARK = 0, CUT = 1, DRILL = 2.
        self.offsets = [
            Point.from_text(markoffset),
            Point.from_text(cutoffset),
            Point.from_text(drilloffset),
        ]

        self.origin = Point.from_xy(0, 0, self.units)
        self.current_location = self.origin
        self.current_path = []
        self.current_tool = Tool.NONE
        self.tool_is_down = False

        # Open the output last so a bad argument doesn't leave an empty file.
        basename, _ = os.path.splitext(fileName)
        self.igor = Igor(basename + ".itx")

    def close(self) -> None:
        if self.tool_is_down:
            self.tool_up()
        self.igor.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def tool_down(self, tool: Tool):
        if self.tool_is_down:
            if tool == self.current_tool:
                return
            # Switching tools: finish the open path first.
            self.tool_up()
        logger.debug(f"Tool {tool} down.")
        self.current_tool = tool
        self.current_path.append(self.current_location)
        self.tool_is_down = True

    def tool_up(self):
        logger.debug("Tool up.")
        if len(self.current_path):
            self.igor.plot_path(self.current_tool, self.current_path)
        self.current_path = []
        self.current_tool = Tool.NONE
        self.tool_is_down = False

    def move(self, x: int, y: int):
        self.current_location = Point.from_xy(x, y, self.units)
        logger.debug(f"Move to {self.current_location}")
        if self.tool_is_down:
            self.current_path.append(self.current_location)

    def set_origin(self):
        self.origin = self.current_location

    def go_to_origin(self):
        self.current_location = self.origin
        if self.tool_is_down:
            self.current_path.append(self.current_location)

    def set_pattern_number(self, pattern_number: int):
        self.pattern_number = pattern_number

    def set_file_number(self, file_number: int):
        self.file_number = file_number

    def command(self, cmd: Token):
        if cmd.is_coordinate:
            self.move(cmd.x, cmd.y)
            return

        if (
            cmd.code == "A"
            or (cmd.code == "D" and cmd.value == 2)
            or (cmd.code == "M" and cmd.value == 15)
        ):
            self.tool_up()
        elif cmd.code == "B" or (cmd.code == "M" and cmd.value == 14):
            self.tool_down(Tool.CUT)
        elif cmd.code == "D" and cmd.value == 1:
            self.tool_down(Tool.MARK)
        elif cmd.code == "G" and cmd.value == 4:
            self.set_origin()
        elif cmd.code == "H":
            self.set_file_number(cmd.value)
        elif cmd.code == "N":
            self.set_pattern_number(cmd.value)
        elif cmd.code == "M" and cmd.value == 70:
            self.go_to_origin()
        else:
            logger.info(f"Didn't process command {cmd}")

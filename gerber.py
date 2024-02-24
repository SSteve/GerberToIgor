import logging
import os
from enum import Enum

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

    origin: Point
    current_path: list[Point]
    current_location: Point
    current_tool: Tool
    tool_is_down: bool
    pattern_number = -1
    file_number = -1

    igor: Igor

    logger: logging.Logger

    def __init__(
        self,
        fileName: str,
        units: int,
        cutoffset: str,
        markoffset: str,
        drilloffset: str,
        verbose: bool,
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

        logging.basicConfig(format="%(message)s")
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        self.origin = Point.from_xy(0, 0, self.units)
        self.current_path = []
        self.current_tool = Tool.NONE
        self.tool_is_down = False

    def tool_down(self, tool: Tool):
        self.logger.debug(f"Tool {tool} down.")
        self.current_tool = tool
        self.current_path.append(self.current_location)
        self.tool_is_down = True

    def tool_up(self):
        self.logger.debug("Tool up.")
        if len(self.current_path):
            self.igor.plot_path(self.current_tool, self.current_path)
        self.current_path = []
        self.current_tool = Tool.NONE
        self.tool_is_down = False

    def move(self, x: int, y: int):
        self.current_location = Point.from_xy(x, y, self.units)
        self.logger.debug(f"Move to {self.current_location}")
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
        # self.logger.debug(cmd)
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
        elif cmd.code == "M":
            if cmd.value == 70:
                self.go_to_origin()
        else:
            self.logger.info(f"Didn't process command {cmd}")

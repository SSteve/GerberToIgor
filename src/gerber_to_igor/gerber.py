import logging
from types import TracebackType
from typing import Self

from .gerber_token import Token
from .igor_writer import Igor
from .point import Point, Units
from .tool import Tool

logger = logging.getLogger(__name__)

NO_OFFSET = Point(0, 0)

# Commands that control the machine (speed, sharpening, knife intelligence,
# stops, ...) but don't change what is drawn. See GERBER.pdf, table 2-1.
NO_PLOT_EFFECT = {
    ("D", 4),  # Light source
    ("M", 1),  # Optional stop
    ("M", 17),  # Maximum advance
    ("M", 18),  # Inhibit next overcut
    ("M", 19),  # Ignore overcut and advance
    ("M", 20),  # Message stop
    ("M", 25),  # Reduced velocity
    ("M", 26),  # Normal velocity
    ("M", 30),  # Rewind data file
    ("M", 40),  # Enable automatic sharpen
    ("M", 41),  # Disable automatic sharpen
    ("M", 42),  # Sharpen
    ("M", 46),  # Lift and plunge corner
    ("M", 47),  # Knife intelligence off
    ("M", 48),  # Knife intelligence on
    ("M", 51),  # Null knife intelligence
    *(("M", n) for n in range(60, 68)),  # Run at 95% ... 60% velocity
    ("M", 69),  # Conveyor bite
}
# Letter commands, with or without a number, that don't change what is drawn:
# feed rate, slowdown, resume speed, light as tool, bite size.
NO_PLOT_EFFECT_CODES = {"F", "L", "O", "Q", "Z"}


class Gerber:
    units: Units
    offsets: dict[Tool, Point]

    origin: Point
    current_path: list[Point]
    current_location: Point
    current_tool: Tool
    tool_is_down: bool
    finished: bool
    ignored_after_end: int
    pattern_number = -1
    file_number = -1

    igor: Igor

    def __init__(
        self,
        output_path: str,
        units: Units,
        *,
        mark_offset: Point = NO_OFFSET,
        cut_offset: Point = NO_OFFSET,
        drill_offset: Point = NO_OFFSET,
    ):
        """Interpret Gerber commands and write the plot to output_path (.itx).

        Offsets are in inches and are added to everything drawn by that tool.
        """
        self.units = units
        self.offsets = {
            Tool.MARK: mark_offset,
            Tool.CUT: cut_offset,
            Tool.DRILL: drill_offset,
            # Notches are made by the knife.
            Tool.NOTCH: cut_offset,
        }

        self.origin = Point.from_xy(0, 0, self.units)
        self.current_location = self.origin
        self.current_path = []
        self.current_tool = Tool.NONE
        self.tool_is_down = False
        self.finished = False
        self.ignored_after_end = 0

        self.igor = Igor(output_path)

    def close(self) -> None:
        if self.tool_is_down:
            self.tool_up()
        if self.ignored_after_end:
            logger.info(
                f"Ignored {self.ignored_after_end} command(s) after M0 (end of file)"
            )
            self.ignored_after_end = 0
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
            offset = self.offsets[self.current_tool]
            self.igor.plot_path(
                self.current_tool, [point + offset for point in self.current_path]
            )
        self.current_path = []
        self.current_tool = Tool.NONE
        self.tool_is_down = False

    def plot_point(self, tool: Tool):
        logger.debug(f"{tool} at {self.current_location}")
        self.igor.plot_point(tool, self.current_location + self.offsets[tool])

    def move(self, x: int | None, y: int | None):
        # An omitted axis keeps its current value.
        moved = Point.from_xy(x or 0, y or 0, self.units)
        self.current_location = Point(
            self.current_location.x if x is None else moved.x,
            self.current_location.y if y is None else moved.y,
        )
        logger.debug(f"Move to {self.current_location}")
        if self.tool_is_down:
            self.current_path.append(self.current_location)

    def set_units(self, units: Units):
        if units != self.units:
            logger.info(f"File sets units to {units.name.lower()}")
        self.units = units

    def set_origin(self):
        self.origin = self.current_location

    def go_to_origin(self):
        self.current_location = self.origin
        if self.tool_is_down:
            self.current_path.append(self.current_location)

    def end(self):
        logger.debug("End of file.")
        if self.tool_is_down:
            self.tool_up()
        self.finished = True

    def set_pattern_number(self, pattern_number: int):
        self.pattern_number = pattern_number

    def set_file_number(self, file_number: int):
        self.file_number = file_number

    def command(self, cmd: Token):
        if self.finished:
            self.ignored_after_end += 1
            return

        if cmd.is_coordinate:
            self.move(cmd.x, cmd.y)
            return

        match (cmd.code, cmd.value):
            case ("A", _) | ("D", 2) | ("M", 15):
                self.tool_up()
            case ("B", _) | ("M", 14):
                self.tool_down(Tool.CUT)
            case ("D", 1):
                self.tool_down(Tool.MARK)
            case ("R", _) | ("M", 43) | ("M", 44):
                self.plot_point(Tool.DRILL)
            case ("E", _) | ("M", 68):
                self.plot_point(Tool.NOTCH)
            case ("G", 4):
                self.set_origin()
            case ("G", 70):
                self.set_units(Units.THOUSANDTHS)
            case ("G", 71):
                self.set_units(Units.TENTHS)
            case ("G", 91):
                self.set_units(Units.HUNDREDTHS)
            case ("M", 70):
                self.go_to_origin()
            case ("M", 0):
                self.end()
            case ("H", value):
                self.set_file_number(value)
            case ("N", value):
                self.set_pattern_number(value)
            case key if key in NO_PLOT_EFFECT or cmd.code in NO_PLOT_EFFECT_CODES:
                logger.debug(f"Ignoring {cmd} (no effect on the plot)")
            case _:
                logger.info(f"Didn't process command {cmd}")

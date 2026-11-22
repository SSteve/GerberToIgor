import io
import math
from types import TracebackType
from typing import Self

from .point import Point
from .tool import Tool

GRAPH_NAME = "GerberPlot"
GRAPH_TITLE = "Gerber Plot"

# 16-bit RGB colors. Rows 0-2 are used for the mark, cut, and drill tools.
PLOT_COLORS = [
    (0, 65535, 0),
    (65535, 0, 0),
    (48545, 4000, 32768),
    (24000, 24000, 65535),
    (32768, 48545, 4000),
]

# 16-bit RGBA colors.
MARKER_COLORS = [
    (16385, 65535, 36045, 32768),
    (65535, 16385, 36045, 32768),
    (65535, 20000, 48535, 32768),
    # The fourth color is for notches which don't use markers so it's just black
    (0, 0, 0, 65535),
]

WAVE_PREFIX = {
    Tool.MARK: "mark",
    Tool.CUT: "cut",
    Tool.DRILL: "drill",
    Tool.NOTCH: "notch",
}

TOOL_COLOR = {
    Tool.MARK: PLOT_COLORS[0],
    Tool.CUT: PLOT_COLORS[1],
    Tool.DRILL: PLOT_COLORS[2],
    Tool.NOTCH: MARKER_COLORS[3][:3],
}

# Igor marker numbers: 19 = filled circle, 1 = X.
TOOL_MARKER = {
    Tool.DRILL: 19,
    Tool.NOTCH: 1,
}

# Fraction of the plot size added around the data on each side.
AXIS_PADDING = 0.05


class MyTextIOWrapper:
    wrapper: io.TextIOWrapper

    def __init__(self, file: io.TextIOWrapper):
        self.wrapper = file

    def write_line(self, text: str) -> int:
        return self.wrapper.write(text + "\n")


def format_number(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    return f"{value:.6f}"


class Igor:
    """Writes an Igor Pro text file (.itx) that plots tool paths and points.

    Paths and points are collected as they arrive and written, one X/Y wave
    pair per tool, when the file is closed. Paths for the same tool are
    separated by NaN so Igor draws them as separate lines.
    """

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    graph_name: str

    output_file: io.TextIOWrapper
    file: MyTextIOWrapper

    paths: dict[Tool, list[list[Point]]]
    points: dict[Tool, list[Point]]

    def __init__(self, fileName: str):
        self.min_x = float("inf")
        self.max_x = -float("inf")
        self.min_y = float("inf")
        self.max_y = -float("inf")

        self.graph_name = GRAPH_NAME
        self.paths = {Tool.MARK: [], Tool.CUT: []}
        self.points = {Tool.DRILL: [], Tool.NOTCH: []}

        # Closed by close() / the context manager protocol.
        self.output_file = open(fileName, "w")  # noqa: SIM115
        self.file = MyTextIOWrapper(self.output_file)

        self.file.write_line("IGOR")
        # Replace a graph left from an earlier load; otherwise Display would
        # pick a new name and the /W= commands below would target the old one.
        self.file.write_line(f"X DoWindow/K {self.graph_name}")
        self.file.write_line(
            f'X Display /W=(35,45,1797,1294) /N={self.graph_name} as "{GRAPH_TITLE}"'
        )
        self.write_matrix("plotColors", PLOT_COLORS)
        self.write_matrix("markerColors", MARKER_COLORS)
        self.file.write_line("X Variable/G logWaveQuantity=10")

    def write_matrix(self, name: str, rows: list[tuple[int, ...]]):
        self.file.write_line(f"WAVES/O/N=({len(rows)},{len(rows[0])}) {name}")
        self.file.write_line("BEGIN")
        for row in rows:
            self.file.write_line("".join(f"\t{value}" for value in row))
        self.file.write_line("END")

    def update_bounds(self, point: Point):
        self.min_x = min(self.min_x, point.x)
        self.max_x = max(self.max_x, point.x)
        self.min_y = min(self.min_y, point.y)
        self.max_y = max(self.max_y, point.y)

    def plot_path(self, tool: Tool, path: list[Point]):
        if tool not in self.paths:
            raise ValueError(f"{tool} does not draw paths")
        self.paths[tool].append(list(path))
        for point in path:
            self.update_bounds(point)

    def plot_point(self, tool: Tool, point: Point):
        if tool not in self.points:
            raise ValueError(f"{tool} does not draw points")
        self.points[tool].append(point)
        self.update_bounds(point)

    def write_waves(self, tool: Tool, points: list[Point]) -> str:
        """Write an X/Y wave pair and return the name of the Y wave."""
        x_name = f"{WAVE_PREFIX[tool]}X"
        y_name = f"{WAVE_PREFIX[tool]}Y"
        self.file.write_line(f"WAVES/D/O {x_name}, {y_name}")
        self.file.write_line("BEGIN")
        for point in points:
            self.file.write_line(
                f"\t{format_number(point.x)}\t{format_number(point.y)}"
            )
        self.file.write_line("END")

        graph = f"/W={self.graph_name}"
        r, g, b = TOOL_COLOR[tool]
        self.file.write_line(f"X AppendToGraph{graph} {y_name} vs {x_name}")
        self.file.write_line(f"X ModifyGraph{graph} rgb({y_name})=({r},{g},{b})")
        return y_name

    def write_plot(self):
        gap = Point(math.nan, math.nan)
        for tool, paths in self.paths.items():
            if not paths:
                continue
            points: list[Point] = []
            for path in paths:
                if points:
                    points.append(gap)
                points.extend(path)
            self.write_waves(tool, points)

        for tool, points in self.points.items():
            if not points:
                continue
            y_name = self.write_waves(tool, points)
            self.file.write_line(
                f"X ModifyGraph/W={self.graph_name} "
                f"mode({y_name})=3, marker({y_name})={TOOL_MARKER[tool]}"
            )

        self.write_axes()

    def write_axes(self):
        if self.min_x > self.max_x:
            return  # Nothing was plotted.
        graph = f"/W={self.graph_name}"
        pad = AXIS_PADDING * max(self.max_x - self.min_x, self.max_y - self.min_y)
        if pad == 0:
            pad = 1.0  # A single point: show a 2 inch square around it.
        self.file.write_line(
            f"X SetAxis{graph} bottom {self.min_x - pad:.6f},{self.max_x + pad:.6f}"
        )
        self.file.write_line(
            f"X SetAxis{graph} left {self.min_y - pad:.6f},{self.max_y + pad:.6f}"
        )
        # Keep inches the same length on both axes so shapes aren't distorted.
        self.file.write_line(f"X ModifyGraph{graph} width={{Plan,1,bottom,left}}")
        self.file.write_line(f'X Label{graph} bottom "X (in)"')
        self.file.write_line(f'X Label{graph} left "Y (in)"')

    def close(self) -> None:
        if self.output_file.closed:
            return
        self.write_plot()
        self.output_file.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

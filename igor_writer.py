import io
import math

from point import Point


class MyTextIOWrapper:
    # Class that implements write_line so I don't have to add "\n" to the end of every string.
    wrapper: io.TextIOWrapper

    def __init__(self, file: io.TextIOWrapper):
        self.wrapper = file

    def write_line(self, text: str) -> int:
        return self.wrapper.write(text + "\n")

    def write(self, text: str) -> int:
        return self.wrapper.write(text)


class Igor:
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    wave_number: int
    first_wave_graphed: bool
    first_wave_in_graph: list[int]

    graph_name: str

    output_file: io.TextIOWrapper
    file: MyTextIOWrapper

    def __init__(self, fileName: str):
        self.min_x = float("inf")
        self.max_x = -float("inf")
        self.min_y = float("inf")
        self.max_y = -float("inf")

        self.wave_number = 0
        self.first_wave_graphed = False
        self.first_wave_in_graph = [1]

        self.graph_name = "GerberPlot0"

        self.output_file = open(fileName, "w")
        self.file = MyTextIOWrapper(self.output_file)

        self.file.write_line("IGOR")
        self.file.write_line(f"X Display /W=(35,45,1797,1294) /N={self.graph_name}")
        self.file.write_line("WAVES/O/N=(5,3) plotColors")
        self.file.write_line("BEGIN")
        self.file.write_line("\t0\t65535\t0")
        self.file.write_line("\t65535\t0\t0")
        self.file.write_line("\t48545\t4000\t32768")
        self.file.write_line("\t24000\t24000\t65535")
        self.file.write_line("\t32768\t48545\t4000")
        self.file.write_line("END")

        self.file.write_line("WAVES/O/N=(4,4) markerColors")
        self.file.write_line("BEGIN")
        self.file.write_line("\t16385\t65535\t36045\t32768")
        self.file.write_line("\t65535\t16385\t36045\t32768")
        self.file.write_line("\t65535\t20000\t48535\t32768")
        # The fourth color is for notches which don't use markers so it's just black
        self.file.write_line("\t0\t0\t0\t65535")
        self.file.write_line("END")

        self.file.write_line("X Variable/G logWaveQuantity=10")

    def finish(self):
        if math.isnan(self.max_x):
            self.output_file.close()
            return

        self.first_wave_in_graph.append(self.wave_number + 1)
        self.file.write_line("WAVES/O firstWaveNumber")
        self.file.write_line("BEGIN")
        for wave_number in self.first_wave_in_graph:
            self.file.write_line(f"\t{wave_number}")
        self.file.write_line("END")

        x_buffer = abs(self.max_x - self.min_x) / 40.0
        y_buffer = abs(self.max_y - self.min_y) / 40.0
        self.file.write_line(
            f"X SetAxis left {self.min_y - y_buffer}, {self.max_y + y_buffer}"
        )
        self.file.write_line(
            f"X SetAxis bottom {self.min_x - x_buffer}, {self.max_x + x_buffer}"
        )
        self.file.write_line("X ModifyGraph axisEnab(left)={0,0.95}")

        # Add the Next and All buttons.
        self.file.write_line(
            'X Button addWaveButton, pos={5.00,5.00}, size={50.00,20.00}, proc=LogWaveButton, title="Next", userdata="Add"'
        )
        self.file.write_line(
            'X Button addAllWavesButton, pos={60.00,5.00}, size={50.00,20.00}, proc=LogWaveButton, title="All", userData="All"'
        )
        self.file.write_line(
            'X Button removeButton, pos={115.00,5.00}, size={70.00,20.00}, proc=LogWaveButton, title="Remove", userdata="Remove"'
        )
        self.file.write_line(
            'X Button addNWavesButton, pos={190.00,5.00}, size={56.00,20.00}, proc=LogWaveButton, title="Next n", userdata="AddN"'
        )
        self.file.write_line(
            'X Button removeNWavesButton, pos={251.00,5.00}, size={78.00,20.00}, proc=LogWaveButton, title="Remove n", userdata="RemoveN"'
        )
        self.file.write_line(
            'X SetVariable logWaveQuantityControl pos={334.00,5.00}, size={60,20}, value=logWaveQuantity, limits={1,inf,1}, fSize = 12, title="n:"'
        )

        self.file.write_line(
            'X SetVariable lastStartXDisplay,pos={5.00,26.00},size={120.00,17.00},title="Last start:"'
        )
        self.file.write_line("X SetVariable lastStartXDisplay,fSize=12,frame=0")
        self.file.write_line(
            "X SetVariable lastStartXDisplay,limits={-inf,inf,0},value=lastPathEnds[0][0],noedit= 1"
        )
        self.file.write_line(
            "X SetVariable lastStartYDisplay,pos={124.00,26.00},size={120.00,17.00}"
        )
        self.file.write_line("X SetVariable lastStartYDisplay,fSize=12,frame=0")
        self.file.write_line(
            'X SetVariable lastStartYDisplay,limits={-inf,inf,0},value=lastPathEnds[0][1],noedit= 1,title=" "'
        )

        self.file.write_line(
            'X SetVariable lastEndXDisplay,pos={5.00,42.00},size={120.00,17.00},title="Last end:"'
        )
        self.file.write_line("X SetVariable lastEndXDisplay,fSize=12,frame=0")
        self.file.write_line(
            "X SetVariable lastEndXDisplay,limits={-inf,inf,0},value=lastPathEnds[1][0],noedit= 1"
        )
        self.file.write_line(
            "X SetVariable lastEndYDisplay,pos={124.00,42.00},size={120.00,17.00}"
        )
        self.file.write_line("X SetVariable lastEndYDisplay,fSize=12,frame=0")
        self.file.write_line(
            'X SetVariable lastEndYDisplay,limits={-inf,inf,0},value=lastPathEnds[1][1],noedit= 1,title=" "'
        )

        self.file.write_line(
            'X CheckBox showEndsCheckBox,pos={5.00,63.00},size={48.00,16.00},proc=ShowEndsCheckProc,title="Show"'
        )
        self.file.write_line("X CheckBox showEndsCheckBox,fSize=12,value= 0")

        self.output_file.close()

    def write_last_ends_wave(self, start: Point, end: Point):
        self.file.write_line("WAVES/O/N=(2, 2) lastPathEnds")
        self.file.write_line("BEGIN")
        self.file.write_line(f"\t{start.x}\t{start.y}")
        self.file.write_line(f"\t{end.x}\t{end.y}")
        self.file.write_line("END")

        self.file.write_line("WAVES/O/N=(2, 3) lastPathEndColors")
        self.file.write_line("BEGIN")
        self.file.write_line("\t0\t35050\t0")
        self.file.write_line("\t35050\t0\t0")
        self.file.write_line("END")

        self.file.write_line("WAVES/I/U lastPathEndMarkers")
        self.file.write_line("BEGIN")
        self.file.write_line("\t18")
        self.file.write_line("\t55")
        self.file.write_line("END")

    def plot_path(self, tool: int, path: list[Point]):
        self.wave_number += 1

        wave_name = f"path{self.wave_number}"
        marker_number_wave_name = f"markerNumber{self.wave_number}"
        marker_size_wave_name = f"markerSize{self.wave_number}"
        color_index_wave_name = f"colorIndex{self.wave_number}"
        marker_color = (
            "16385,65535,36045,32768" if tool == 0 else "65535,16385,36045,32768"
        )

        # Write the path coordinates.
        self.file.write_line(f"WAVES/O/N=({len(path)}, 2) {wave_name}")
        self.file.write_line("BEGIN")
        for plot_point in path:
            self.file.write_line(f"\t{plot_point.x}\t{plot_point.y}")
            self.min_x = min(self.min_x, plot_point.x)
            self.max_x = max(self.max_x, plot_point.x)
            self.min_y = min(self.min_y, plot_point.y)
            self.max_y = max(self.max_y, plot_point.y)
        self.file.write_line("END")

        # Write the marker numbers (not used for Gerber files, but required in the Igor procedures).
        self.file.write_line(f"WAVES/O {marker_number_wave_name}")
        self.file.write_line("BEGIN")
        for _ in range(len(path)):
            self.file.write_line("\t8")
        self.file.write_line("END")

        # Write the marker sizes.
        self.file.write_line(f"WAVES/O {marker_size_wave_name}")
        self.file.write_line("BEGIN")
        # Starting point is size 5.
        self.file.write_line("\t5")
        for _ in range(len(path) - 2):
            # Midpoints are size 8.
            self.file.write_line("\t8")
        # End point is size 3.
        self.file.write_line("\t3")
        self.file.write_line("END")

        # Write the indexes into the color wave.
        self.file.write_line(f"WAVES/O {color_index_wave_name}")
        self.file.write_line("BEGIN")
        for _ in range(len(path)):
            self.file.write_line(f"\t{tool.value}")
        self.file.write_line("END")

        if not self.first_wave_graphed:
            self.first_wave_graphed = True
            self.file.write_line(
                f"X AppendToGraph /W={self.graph_name} {wave_name}[*][1] vs {wave_name}[*][0]"
            )
            # Index into tool color wave.
            self.file.write(
                f"X ModifyGraph zColor({wave_name})={{{color_index_wave_name},*,*,cindexRGB,0,plotColors}}"
            )
            # Marker specifications.
            self.file.write(
                f", zmrkNum({wave_name})={{{marker_number_wave_name}}}, mrkThick({wave_name})=2"
            )
            self.file.write(
                f", useMrkStrokeRGB({wave_name})=1, mrkStrokeRGB({wave_name})=({marker_color}), mode({wave_name})=4"
            )
            self.file.write_line(
                f", zmrkSize({wave_name})={{{marker_size_wave_name},3,8,3,8}}"
            )
            self.write_last_ends_wave(path[0], path[-1])

    def plot_drill(self, location: Point):
        self.wave_number += 1
        wave_name = f"path{self.wave_number}"
        color_index_wave_name = f"colorIndex{self.wave_number}"

        circle_points = 20

        # Write a circle around a cross.
        self.file.write_line(f"WAVES/O/N=({circle_points + 5}, 2) {wave_name}")
        self.file.write_line("BEGIN")

        # Draw the horizontal leg of the cross.
        self.file.write_line(f"\t{location.x - 0.5}\t{location.y}")
        self.file.write_line(f"\t{location.x + 0.5}\t{location.y}")

        # Draw the circle.
        for point_number in range(circle_points):
            t = math.pi * 2 * (point_number + 1) / circle_points
            circle_point = location + Point(math.cos(t) / 2.0, math.sin(t) / 2.0)
            self.file.write_line(f"\t{circle_point.x}\t{circle_point.y}")

        # Insert NaN point to break the drawing between the end of the circle
        # and the beginning of the vertical leg of the cross.
        self.file.write_line("\tNaN\tNaN")

        # Draw the vertical leg of the cross.
        self.file.write_line(f"\t{location.x}\t{location.y - 0.5}")
        self.file.write_line(f"\t{location.x}\t{location.y + 0.5}")
        self.file.write_line("END")

        # Write the indexes into the color wave. Drill index is 4.
        drill_color_index = 4
        self.file.write_line(f"WAVES/O {color_index_wave_name}")
        self.file.write_line("BEGIN")
        for _ in range(circle_points + 5):
            self.file.write_line(f"\t{drill_color_index}")
        self.file.write_line("END")

        if not self.first_wave_graphed:
            self.first_wave_graphed = True
            self.file.write_line(
                f"X AppendToGraph /W={self.graph_name} {wave_name}[*][1] vs {wave_name}[*][0]"
            )
            # Index into tool color wave
            self.file.write_line(
                f"ModifyGraph zColor({wave_name})={{{color_index_wave_name},*,*,cindexRGB,0,plotColors}}"
            )

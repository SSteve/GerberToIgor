import io

from point import Point


class MyTextIOWrapper:
    wrapper: io.TextIOWrapper

    def __init__(self, file: io.TextIOWrapper):
        self.wrapper = file

    def write_line(self, text: str) -> int:
        return self.wrapper.write(text + "\n")


class Igor:
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    graph_name: str

    output_file: io.TextIOWrapper
    file: MyTextIOWrapper

    def __init__(self, fileName: str):
        self.min_x = float("inf")
        self.max_x = -float("inf")
        self.min_y = float("inf")
        self.max_y = -float("inf")

        self.graph_name = "Gerber Plot"

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

    def plot_path(self, tool: int, path: list[Point]):
        pass

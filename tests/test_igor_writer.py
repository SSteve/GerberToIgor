import math

import pytest

from gerber_to_igor.igor_writer import Igor
from gerber_to_igor.point import Point
from gerber_to_igor.tool import Tool


def write(tmp_path, build) -> list[str]:
    output = tmp_path / "out.itx"
    with Igor(str(output)) as igor:
        build(igor)
    return output.read_text().splitlines()


def wave_block(lines: list[str], header: str) -> list[tuple[float, ...]]:
    """Return the data rows of the WAVES block with the given header line."""
    start = lines.index(header)
    assert lines[start + 1] == "BEGIN"
    end = lines.index("END", start)
    return [tuple(float(v) for v in row.split()) for row in lines[start + 2 : end]]


def test_writes_header(tmp_path):
    lines = write(tmp_path, lambda igor: None)
    assert lines[0] == "IGOR"
    assert lines[1] == "X DoWindow/K GerberPlot"
    assert lines[2] == 'X Display /W=(35,45,1797,1294) /N=GerberPlot as "Gerber Plot"'
    assert wave_block(lines, "WAVES/O/N=(5,3) plotColors")[1] == (65535, 0, 0)
    assert wave_block(lines, "WAVES/O/N=(4,4) markerColors")[3] == (0, 0, 0, 65535)
    assert "X Variable/G logWaveQuantity=10" in lines


def test_empty_plot_has_no_waves_or_axes(tmp_path):
    lines = write(tmp_path, lambda igor: None)
    assert not any(line.startswith("WAVES/D") for line in lines)
    assert not any("SetAxis" in line for line in lines)


def test_paths_for_a_tool_are_separated_by_nan(tmp_path):
    def build(igor):
        igor.plot_path(Tool.CUT, [Point(0, 0), Point(1, 0)])
        igor.plot_path(Tool.CUT, [Point(2, 2), Point(3, 3)])

    lines = write(tmp_path, build)
    rows = wave_block(lines, "WAVES/D/O cutX, cutY")
    assert rows[:2] == [(0, 0), (1, 0)]
    assert all(math.isnan(v) for v in rows[2])
    assert rows[3:] == [(2, 2), (3, 3)]
    assert "X AppendToGraph/W=GerberPlot cutY vs cutX" in lines
    assert "X ModifyGraph/W=GerberPlot rgb(cutY)=(65535,0,0)" in lines


def test_each_tool_gets_its_own_waves_and_color(tmp_path):
    def build(igor):
        igor.plot_path(Tool.MARK, [Point(0, 0), Point(1, 1)])
        igor.plot_path(Tool.CUT, [Point(0, 0), Point(1, 0)])

    lines = write(tmp_path, build)
    assert wave_block(lines, "WAVES/D/O markX, markY") == [(0, 0), (1, 1)]
    assert "X ModifyGraph/W=GerberPlot rgb(markY)=(0,65535,0)" in lines
    assert "X ModifyGraph/W=GerberPlot rgb(cutY)=(65535,0,0)" in lines


def test_points_are_drawn_as_markers(tmp_path):
    def build(igor):
        igor.plot_point(Tool.DRILL, Point(1, 2))
        igor.plot_point(Tool.DRILL, Point(3, 4))
        igor.plot_point(Tool.NOTCH, Point(5, 6))

    lines = write(tmp_path, build)
    assert wave_block(lines, "WAVES/D/O drillX, drillY") == [(1, 2), (3, 4)]
    assert wave_block(lines, "WAVES/D/O notchX, notchY") == [(5, 6)]
    assert "X ModifyGraph/W=GerberPlot mode(drillY)=3, marker(drillY)=19" in lines
    assert "X ModifyGraph/W=GerberPlot mode(notchY)=3, marker(notchY)=1" in lines
    assert "X ModifyGraph/W=GerberPlot rgb(notchY)=(0,0,0)" in lines


def test_axes_cover_all_data_with_padding_and_equal_scale(tmp_path):
    def build(igor):
        igor.plot_path(Tool.CUT, [Point(0, 0), Point(10, 5)])
        igor.plot_point(Tool.DRILL, Point(-10, 0))

    lines = write(tmp_path, build)
    # Data spans 20 x 5; padding is 5% of the larger span (1.0).
    assert "X SetAxis/W=GerberPlot bottom -11.000000,11.000000" in lines
    assert "X SetAxis/W=GerberPlot left -1.000000,6.000000" in lines
    assert "X ModifyGraph/W=GerberPlot width={Plan,1,bottom,left}" in lines
    assert 'X Label/W=GerberPlot bottom "X (in)"' in lines


def test_single_point_gets_default_padding(tmp_path):
    lines = write(tmp_path, lambda igor: igor.plot_point(Tool.DRILL, Point(2, 3)))
    assert "X SetAxis/W=GerberPlot bottom 1.000000,3.000000" in lines
    assert "X SetAxis/W=GerberPlot left 2.000000,4.000000" in lines


def test_plot_commands_come_after_wave_data(tmp_path):
    lines = write(
        tmp_path, lambda igor: igor.plot_path(Tool.MARK, [Point(0, 0), Point(1, 1)])
    )
    assert lines.index("WAVES/D/O markX, markY") < lines.index(
        "X AppendToGraph/W=GerberPlot markY vs markX"
    )


def test_rejects_wrong_kind_of_tool(tmp_path):
    with Igor(str(tmp_path / "out.itx")) as igor:
        with pytest.raises(ValueError):
            igor.plot_path(Tool.DRILL, [Point(0, 0)])
        with pytest.raises(ValueError):
            igor.plot_point(Tool.CUT, Point(0, 0))


def test_close_is_idempotent(tmp_path):
    output = tmp_path / "out.itx"
    igor = Igor(str(output))
    igor.plot_point(Tool.DRILL, Point(1, 1))
    igor.close()
    igor.close()
    assert output.read_text().count("WAVES/D/O drillX, drillY") == 1
    assert igor.output_file.closed

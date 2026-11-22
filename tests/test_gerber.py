import logging

import pytest

from gerber_to_igor.point import Point, Units
from gerber_to_igor.tool import Tool

from .conftest import NOTCH_SAMPLE, SAMPLE, coords, flat


def test_moves_with_tool_up_record_nothing(make_gerber):
    gerber = make_gerber()
    assert gerber.run("X0Y0*X100Y100*X200Y0*") == []
    assert gerber.current_location == Point(2.0, 0.0)


def test_mark_path(make_gerber):
    paths = make_gerber().run("X0Y0*D1*X100Y0*X100Y100*D2*")
    assert [(tool, coords(path)) for tool, path in paths] == [
        (Tool.MARK, [(0, 0), (1, 0), (1, 1)])
    ]


@pytest.mark.parametrize(("down", "up"), [("M14", "M15"), ("B", "A")])
def test_cut_path(make_gerber, down, up):
    paths = make_gerber().run(f"X0Y0*{down}*X100Y0*{up}*")
    assert [(tool, coords(path)) for tool, path in paths] == [
        (Tool.CUT, [(0, 0), (1, 0)])
    ]


@pytest.mark.parametrize("up", ["D2", "M15", "A"])
def test_any_tool_up_command_ends_any_tool(make_gerber, up):
    paths = make_gerber().run(f"D1*X100Y0*{up}*M14*X100Y100*{up}*")
    assert [tool for tool, _ in paths] == [Tool.MARK, Tool.CUT]


def test_tool_up_without_path_records_nothing(make_gerber):
    gerber = make_gerber()
    assert gerber.run("D2*M15*A*") == []
    assert not gerber.tool_is_down
    assert gerber.current_tool == Tool.NONE


def test_switching_tools_flushes_open_path(make_gerber):
    paths = make_gerber().run("X0Y0*D1*X100Y0*M14*X100Y100*D1*X0Y0*D2*")
    assert [(tool, coords(path)) for tool, path in paths] == [
        (Tool.MARK, [(0, 0), (1, 0)]),
        (Tool.CUT, [(1, 0), (1, 1)]),
        (Tool.MARK, [(1, 1), (0, 0)]),
    ]


def test_repeated_tool_down_does_not_duplicate_point(make_gerber):
    paths = make_gerber().run("X0Y0*D1*D1*X100Y0*D1*X100Y100*D2*")
    assert coords(paths[0][1]) == [(0, 0), (1, 0), (1, 1)]


def test_tool_down_before_any_move_starts_at_origin(make_gerber):
    paths = make_gerber().run("D1*X100Y0*D2*")
    assert coords(paths[0][1]) == [(0, 0), (1, 0)]


def test_set_origin_and_return(make_gerber):
    gerber = make_gerber()
    paths = gerber.run("X100Y200*G4*X0Y0*D1*M70*D2*")
    assert gerber.origin == Point(1.0, 2.0)
    assert gerber.current_location == Point(1.0, 2.0)
    assert coords(paths[0][1]) == [(0, 0), (1, 2)]


def test_go_to_origin_with_tool_up_records_nothing(make_gerber):
    gerber = make_gerber()
    assert gerber.run("X100Y100*M70*") == []
    assert gerber.current_location == Point(0, 0)


def test_file_and_pattern_numbers(make_gerber):
    gerber = make_gerber()
    gerber.run("H3*N7*")
    assert gerber.file_number == 3
    assert gerber.pattern_number == 7


def test_unknown_commands_are_logged(make_gerber, caplog):
    with caplog.at_level(logging.INFO, logger="gerber_to_igor"):
        make_gerber().run("G1*M31*M99*")
    assert [r.getMessage() for r in caplog.records] == [
        "Didn't process command G1",
        "Didn't process command M31",
        "Didn't process command M99",
    ]


@pytest.mark.parametrize(
    "command", ["M26", "M25", "L", "O", "M60", "M67", "F20", "Z5", "M42", "D4"]
)
def test_commands_without_plot_effect_are_ignored_quietly(make_gerber, caplog, command):
    gerber = make_gerber()
    with caplog.at_level(logging.INFO, logger="gerber_to_igor"):
        paths = gerber.run(f"X0Y0*M14*{command}*X100Y0*M15*")
    assert caplog.records == []
    assert coords(paths[0][1]) == [(0, 0), (1, 0)]


@pytest.mark.parametrize("command", ["M43", "R", "M44"])
def test_drill(make_gerber, command):
    gerber = make_gerber(drilloffset="0.5,-0.5")
    gerber.run(f"X250Y250*{command}*")
    assert gerber.points == [(Tool.DRILL, Point(3.0, 2.0))]
    assert gerber.paths == []


@pytest.mark.parametrize("command", ["E", "M68"])
def test_notch_uses_cut_offset(make_gerber, command):
    gerber = make_gerber(cutoffset="1,1", markoffset="5,5")
    gerber.run(f"X100Y0*{command}*")
    assert gerber.points == [(Tool.NOTCH, Point(2.0, 1.0))]


def test_drill_while_cutting_does_not_break_path(make_gerber):
    gerber = make_gerber()
    paths = gerber.run("X0Y0*M14*X100Y0*M43*X200Y0*M15*")
    assert coords(paths[0][1]) == [(0, 0), (1, 0), (2, 0)]
    assert gerber.points == [(Tool.DRILL, Point(1.0, 0.0))]


def test_offsets_applied_to_paths_by_tool(make_gerber):
    gerber = make_gerber(markoffset="1,1", cutoffset="2,-2")
    paths = gerber.run("X0Y0*D1*X100Y0*D2*M14*X0Y0*M15*")
    assert [(tool, coords(path)) for tool, path in paths] == [
        (Tool.MARK, [(1, 1), (2, 1)]),
        (Tool.CUT, [(3, -2), (2, -2)]),
    ]


def test_offsets_do_not_change_current_location(make_gerber):
    gerber = make_gerber(cutoffset="2,2")
    gerber.run("X100Y100*M14*X200Y200*M15*")
    assert gerber.current_location == Point(2.0, 2.0)


@pytest.mark.parametrize(
    ("command", "units"),
    [("G70", Units.THOUSANDTHS), ("G71", Units.TENTHS), ("G91", Units.HUNDREDTHS)],
)
def test_file_sets_units(make_gerber, command, units):
    gerber = make_gerber()
    gerber.run(f"N1*{command}*")
    assert gerber.units == units


def test_units_change_applies_to_later_moves(make_gerber):
    gerber = make_gerber()
    paths = gerber.run("X100Y0*M14*G70*X2000Y0*M15*")
    assert flat(paths[0][1]) == pytest.approx([1.0, 0.0, 2.0, 0.0])


def test_end_of_file_stops_processing(make_gerber, caplog):
    gerber = make_gerber()
    with caplog.at_level(logging.INFO, logger="gerber_to_igor"):
        paths = gerber.run("X0Y0*M14*X100Y0*M0*X200Y0*M14*X300Y0*")
        gerber.close()
    assert gerber.finished
    assert [(tool, coords(path)) for tool, path in paths] == [
        (Tool.CUT, [(0, 0), (1, 0)])
    ]
    assert gerber.current_location == Point(1.0, 0.0)
    assert [r.getMessage() for r in caplog.records] == [
        "Ignored 3 command(s) after M0 (end of file)"
    ]


def test_x_only_and_y_only_moves_keep_other_axis(make_gerber):
    paths = make_gerber().run("X100Y200*M14*X300*Y400*M15*")
    assert coords(paths[0][1]) == [(1, 2), (3, 2), (3, 4)]


def test_close_flushes_open_path(make_gerber):
    gerber = make_gerber()
    gerber.run("X0Y0*M14*X100Y0*")
    assert gerber.paths == []
    gerber.close()
    assert [(tool, coords(path)) for tool, path in gerber.paths] == [
        (Tool.CUT, [(0, 0), (1, 0)])
    ]
    assert gerber.igor.output_file.closed


def test_context_manager_closes_output(make_gerber):
    with make_gerber() as gerber:
        pass
    assert gerber.igor.output_file.closed


def test_offsets_by_tool(make_gerber):
    gerber = make_gerber(markoffset="1,1", cutoffset="2,2", drilloffset="3,3")
    assert gerber.offsets == {
        Tool.MARK: Point(1, 1),
        Tool.CUT: Point(2, 2),
        Tool.DRILL: Point(3, 3),
        Tool.NOTCH: Point(2, 2),
    }


@pytest.mark.parametrize(
    ("units", "x", "expected"),
    [
        (Units.TENTHS, 254, 1.0),
        (Units.HUNDREDTHS, 100, 1.0),
        (Units.THOUSANDTHS, 1000, 1.0),
    ],
)
def test_units_apply_to_moves(make_gerber, units, x, expected):
    gerber = make_gerber(units=units)
    gerber.run(f"X{x}Y{x}*")
    assert gerber.current_location.x == pytest.approx(expected)
    assert gerber.current_location.y == pytest.approx(expected)


def test_sample_file_paths(make_gerber):
    paths = make_gerber().run(SAMPLE.read_text())
    assert [tool for tool, _ in paths] == [Tool.MARK, Tool.CUT, Tool.MARK, Tool.CUT]
    expected = [
        [(-0.5, -0.5), (10.5, 0.5)],
        [(10.5, 0.5), (10.5, 10.5)],
        [(10.5, -10.5), (-0.5, 10.5)],
        [(0.5, 10.5), (0.5, 0.5)],
    ]
    for (_, path), want in zip(paths, expected, strict=True):
        assert flat(path) == pytest.approx([c for p in want for c in p])


def test_notch_sample_file_paths(make_gerber):
    gerber = make_gerber(markoffset="1,1", cutoffset="2,2", drilloffset="3,3")
    paths = gerber.run(NOTCH_SAMPLE.read_text())
    assert [tool for tool, _ in paths] == [
        Tool.MARK,
        Tool.CUT,
        Tool.CUT,
        Tool.MARK,
        Tool.CUT,
        Tool.CUT,
        Tool.CUT,
        Tool.CUT,
    ]
    assert all(len(path) == 2 for _, path in paths)
    assert not gerber.tool_is_down
    assert gerber.points == [(Tool.DRILL, Point(5.5, 5.5))]
    # Offsets: mark 1,1; cut 2,2.
    assert flat(paths[0][1]) == pytest.approx([0.5, 0.5, 10.5, 10.5])
    assert flat(paths[1][1]) == pytest.approx([12.25, 7.5, 12.5, 7.63])

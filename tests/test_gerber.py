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


def test_unprocessed_commands_are_logged(make_gerber, caplog):
    with caplog.at_level(logging.INFO, logger="gerber_to_igor"):
        make_gerber().run("M26*M43*M0*G1*")
    assert [r.getMessage() for r in caplog.records] == [
        "Didn't process command M26",
        "Didn't process command M43",
        "Didn't process command M0",
        "Didn't process command G1",
    ]


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


def test_offsets_indexed_by_tool(make_gerber):
    gerber = make_gerber(markoffset="1,1", cutoffset="2,2", drilloffset="3,3")
    assert gerber.offsets[Tool.MARK.value] == Point(1, 1)
    assert gerber.offsets[Tool.CUT.value] == Point(2, 2)
    assert gerber.offsets[Tool.DRILL.value] == Point(3, 3)


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


def test_bad_offset_does_not_create_output(tmp_path, make_gerber):
    with pytest.raises(ValueError):
        make_gerber(cutoffset="bad")
    assert not (tmp_path / "test.itx").exists()


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

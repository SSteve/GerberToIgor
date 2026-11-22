import math
import shutil
import subprocess
import sys

import pytest

from gerber_to_igor.cli import build_arg_parser, main

from .conftest import NOTCH_SAMPLE, SAMPLE
from .test_igor_writer import wave_block

NAN_ROW = (math.nan, math.nan)


def flatten(rows):
    return [v for row in rows for v in row]


def test_defaults():
    args = build_arg_parser().parse_args(["in.gbr"])
    assert args.gerberfile == "in.gbr"
    assert args.units == 2
    assert (args.markoffset, args.cutoffset, args.drilloffset) == ("0,0",) * 3
    assert not args.verbose


def test_units_parsed_as_int():
    args = build_arg_parser().parse_args(["-u", "1", "in.gbr"])
    assert args.units == 1


@pytest.mark.parametrize("units", ["0", "4", "x"])
def test_invalid_units_rejected(units, capsys):
    with pytest.raises(SystemExit):
        build_arg_parser().parse_args(["-u", units, "in.gbr"])
    assert "--units" in capsys.readouterr().err


def run_main(tmp_path, monkeypatch, sample, *extra_args) -> list[str]:
    gerber_file = tmp_path / sample.name
    shutil.copy(sample, gerber_file)
    monkeypatch.setattr(sys, "argv", ["gerber-to-igor", *extra_args, str(gerber_file)])
    main()
    return gerber_file.with_suffix(".itx").read_text().splitlines()


def test_main_sample(tmp_path, monkeypatch):
    lines = run_main(tmp_path, monkeypatch, SAMPLE)
    assert lines[0] == "IGOR"
    # Two mark paths and two cut paths, separated by NaN rows.
    assert flatten(wave_block(lines, "WAVES/D/O markX, markY")) == pytest.approx(
        flatten([(-0.5, -0.5), (10.5, 0.5), NAN_ROW, (10.5, -10.5), (-0.5, 10.5)]),
        nan_ok=True,
    )
    assert flatten(wave_block(lines, "WAVES/D/O cutX, cutY")) == pytest.approx(
        flatten([(10.5, 0.5), (10.5, 10.5), NAN_ROW, (0.5, 10.5), (0.5, 0.5)]),
        nan_ok=True,
    )
    assert "WAVES/D/O drillX, drillY" not in lines
    assert "X SetAxis/W=GerberPlot bottom -1.550000,11.550000" in lines
    assert "X SetAxis/W=GerberPlot left -11.550000,11.550000" in lines


def test_main_notch_sample_with_offsets(tmp_path, monkeypatch):
    lines = run_main(
        tmp_path, monkeypatch, NOTCH_SAMPLE, "-m", "1,1", "-c", "2,2", "-d", "3,3"
    )
    mark = wave_block(lines, "WAVES/D/O markX, markY")
    cut = wave_block(lines, "WAVES/D/O cutX, cutY")
    # 2 mark paths and 6 cut paths of 2 points each, plus NaN separators.
    assert len(mark) == 2 * 2 + 1
    assert len(cut) == 6 * 2 + 5
    # Mark offset 1,1 on the first mark line from (-0.5,-0.5) to (9.5,9.5).
    assert flatten(mark[:2]) == pytest.approx([0.5, 0.5, 10.5, 10.5])
    # Cut offset 2,2 on the outline cut from (8.5,-1.5) to (8.5,8.5).
    assert flatten(cut[12:14]) == pytest.approx([10.5, 0.5, 10.5, 10.5])
    # Drill offset 3,3 on the M43 hole at (2.5,2.5).
    assert wave_block(lines, "WAVES/D/O drillX, drillY") == [(5.5, 5.5)]


def test_console_script(tmp_path):
    gerber_file = tmp_path / "sample.gbr"
    shutil.copy(SAMPLE, gerber_file)
    result = subprocess.run(
        [sys.executable, "-m", "gerber_to_igor", str(gerber_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stderr == ""
    assert (tmp_path / "sample.itx").read_text().startswith("IGOR\n")

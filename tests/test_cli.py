import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gerber_to_igor.cli import build_arg_parser, main
from gerber_to_igor.point import Point

from .conftest import NOTCH_SAMPLE, SAMPLE
from .test_igor_writer import wave_block

NAN_ROW = (math.nan, math.nan)


def flatten(rows):
    return [v for row in rows for v in row]


def test_defaults():
    args = build_arg_parser().parse_args(["in.gbr"])
    assert args.gerberfile == Path("in.gbr")
    assert args.output is None
    assert args.units == 2
    assert (args.markoffset, args.cutoffset, args.drilloffset) == (Point(0, 0),) * 3
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


def copy_sample(tmp_path) -> Path:
    gerber_file = tmp_path / "sample.gbr"
    shutil.copy(SAMPLE, gerber_file)
    return gerber_file


def test_output_option(tmp_path):
    gerber_file = copy_sample(tmp_path)
    output = tmp_path / "out" / "plot.itx"
    output.parent.mkdir()
    assert main(["-o", str(output), str(gerber_file)]) == 0
    assert output.read_text().startswith("IGOR\n")
    assert not (tmp_path / "sample.itx").exists()


def test_default_output_replaces_extension(tmp_path):
    gerber_file = tmp_path / "part.v2.gbr"
    shutil.copy(SAMPLE, gerber_file)
    assert main([str(gerber_file)]) == 0
    assert (tmp_path / "part.v2.itx").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["--markoffset=-1,2"],
        ["-m-1,2"],
        ["-m", "1.5,-2.25"],
    ],
)
def test_negative_and_decimal_offsets(args):
    parsed = build_arg_parser().parse_args([*args, "in.gbr"])
    assert parsed.markoffset in (Point(-1, 2), Point(1.5, -2.25))


@pytest.mark.parametrize("value", ["1", "1,2,3", "a,b", "", "nan,0", "1,inf"])
def test_bad_offset_is_a_usage_error(tmp_path, capsys, value):
    gerber_file = copy_sample(tmp_path)
    with pytest.raises(SystemExit) as exit_info:
        main([f"--cutoffset={value}", str(gerber_file)])
    assert exit_info.value.code == 2
    err = capsys.readouterr().err
    assert "argument -c/--cutoffset: expected X,Y in inches" in err
    assert "Traceback" not in err
    assert not (tmp_path / "sample.itx").exists()


def test_missing_input_file(tmp_path, capsys):
    missing = tmp_path / "missing.gbr"
    assert main([str(missing)]) == 1
    assert capsys.readouterr().err == (
        f"gerber-to-igor: error: can't read {missing}: No such file or directory\n"
    )
    assert not (tmp_path / "missing.itx").exists()


def test_input_is_a_directory(tmp_path, capsys):
    assert main([str(tmp_path)]) == 1
    assert "gerber-to-igor: error: can't read" in capsys.readouterr().err


def test_output_directory_missing(tmp_path, capsys):
    gerber_file = copy_sample(tmp_path)
    output = tmp_path / "nope" / "out.itx"
    assert main(["-o", str(output), str(gerber_file)]) == 1
    assert capsys.readouterr().err == (
        f"gerber-to-igor: error: can't write {output}: No such file or directory\n"
    )


def test_refuses_to_overwrite_input(tmp_path, capsys):
    gerber_file = tmp_path / "sample.itx"
    shutil.copy(SAMPLE, gerber_file)
    assert main([str(gerber_file)]) == 1
    assert "would overwrite the input file" in capsys.readouterr().err
    assert gerber_file.read_text() == SAMPLE.read_text()


def test_non_ascii_bytes_are_skipped_not_fatal(tmp_path, caplog):
    gerber_file = tmp_path / "odd.gbr"
    gerber_file.write_bytes(b"X0Y0*M14*X100Y0*\xff\xfe*M15*M0*")
    assert main([str(gerber_file)]) == 0
    assert any("Skipping unrecognized block" in r.getMessage() for r in caplog.records)
    lines = (tmp_path / "odd.itx").read_text().splitlines()
    assert wave_block(lines, "WAVES/D/O cutX, cutY") == [(0, 0), (1, 0)]


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.startswith("gerber-to-igor ")


def test_console_script_exit_status(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "gerber_to_igor", str(tmp_path / "missing.gbr")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stderr.startswith("gerber-to-igor: error: can't read")

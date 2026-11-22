import shutil
import subprocess
import sys

import pytest

from gerber_to_igor.cli import build_arg_parser, main

from .conftest import NOTCH_SAMPLE, SAMPLE


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


@pytest.mark.parametrize(
    ("sample", "extra_args"),
    [
        (SAMPLE, []),
        (NOTCH_SAMPLE, ["-m", "1,1", "-c", "2,2", "-d", "3,3"]),
    ],
)
def test_main_end_to_end(tmp_path, monkeypatch, sample, extra_args):
    gerber_file = tmp_path / sample.name
    shutil.copy(sample, gerber_file)
    monkeypatch.setattr(sys, "argv", ["gerber-to-igor", *extra_args, str(gerber_file)])

    main()

    output = gerber_file.with_suffix(".itx")
    lines = output.read_text().splitlines()
    assert lines[0] == "IGOR"
    # TODO(Phase 3): check the plotted path data once plot_path is implemented.


def test_console_script(tmp_path):
    gerber_file = tmp_path / "sample.gbr"
    shutil.copy(SAMPLE, gerber_file)
    result = subprocess.run(
        [sys.executable, "-m", "gerber_to_igor", str(gerber_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Didn't process command M26" in result.stderr
    assert (tmp_path / "sample.itx").exists()

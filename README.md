# GerberToIgor

Convert Gerber **cutter** files into Igor Pro text files (`.itx`) that plot
the tool paths, so you can see what a cutting table will mark, cut, drill, and
notch before running a job.

This is the cutting-table Gerber dialect (`H1*M70*D2*M15*N1*…*M0*`), not the
RS-274X format used for printed circuit boards. `GERBER.pdf` in this
repository is the command reference.

## Install

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```sh
# Run from a checkout without installing
uv run gerber-to-igor FILE.gbr

# Or install the gerber-to-igor command on your PATH
uv tool install .
```

## Usage

```sh
gerber-to-igor [options] FILE.gbr
```

Writes `FILE.itx` next to the input unless `-o` is given. Load it in Igor Pro
with **Data ▸ Load Waves ▸ Load Igor Text…** or by dragging it onto Igor.

| Option | Meaning |
|---|---|
| `-o`, `--output PATH` | Igor text file to write (default: input path with `.itx`) |
| `-u`, `--units {1,2,3}` | Coordinate units: `1` tenths of millimeters, `2` hundredths of inches (default), `3` thousandths of inches |
| `-m`, `--markoffset X,Y` | Mark (pen) tool offset in inches |
| `-c`, `--cutoffset X,Y` | Cut (knife) tool offset in inches; also used for notches |
| `-d`, `--drilloffset X,Y` | Drill tool offset in inches |
| `-v`, `--verbose` | Log every move and tool change |
| `--version` | Show the version |

A `G70`, `G71`, or `G91` command in the file overrides `--units` from that
point on.

**Negative offsets**: attach the value to the option, as in
`--cutoffset=-1,2` or `-c-1,2`. The separated form `-c -1,2` works only when
running on Python 3.14 or newer; older versions mistake `-1,2` for an option.

### Example

```sh
gerber-to-igor -m 1,1 -c 2,2 -d 3,3 "Gerber square with notch and offset.gbr"
```

## Output

Opening the `.itx` file creates a graph named `GerberPlot` (replacing an
existing one of that name) with the axes in inches at a 1:1 aspect ratio:

| Tool | Drawn as | Color | Igor waves |
|---|---|---|---|
| Mark (`D1`) | Lines | Green | `markX`, `markY` |
| Cut (`M14` / `B`) | Lines | Red | `cutX`, `cutY` |
| Drill (`M43` / `R`) | Filled circles | Purple | `drillX`, `drillY` |
| Notch (`M68` / `E`) | X markers | Black | `notchX`, `notchY` |

Each tool's offset is added to everything that tool draws. Separate paths for
the same tool are kept in one wave pair, separated by `NaN` rows.

## Messages

- `Didn't process command …` — a command that isn't supported was skipped.
- `Skipping unrecognized block …` — text that isn't a coordinate or command,
  such as label text after `M31`, was skipped.
- `Ignored N command(s) after M0 (end of file)` — data followed the end of
  file marker.
- `gerber-to-igor: error: …` — the conversion couldn't run (missing input,
  unwritable output, bad option). The exit status is nonzero.

Speed, sharpening, and other machine-control commands are ignored without a
message because they don't affect the plot. See `plan.md` for the full
command table and known limitations.

## Development

```sh
uv sync                 # create .venv with dev tools
uv run pytest           # run the tests
uv run ruff check .     # lint
uv run ruff format .    # format
uv run --isolated --python 3.12 pytest   # test on the oldest supported Python
```

The code is in `src/gerber_to_igor/`; `plan.md` describes the design and the
development plan.

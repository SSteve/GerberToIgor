# GerberToIgor — Project Plan

## Overview

GerberToIgor converts cutter/plotter Gerber files (the `H1*M70*D2*M15*N1*…`
command dialect used by cutting tables, not the PCB RS-274X format) into Igor
Pro text files (`.itx`) that plot the mark, cut, and drill tool paths.

### Usage

```sh
uv run gerber-to-igor [-u UNITS] [-m X,Y] [-c X,Y] [-d X,Y] [-v] FILE.gbr
```

| Option | Meaning |
|---|---|
| `-u`, `--units` | 1 = tenths of millimeters, 2 = hundredths of inches (default), 3 = thousandths of inches |
| `-m`, `--markoffset` | Mark tool offset in inches (`x,y`) |
| `-c`, `--cutoffset` | Cut tool offset in inches (`x,y`) |
| `-d`, `--drilloffset` | Drill tool offset in inches (`x,y`) |
| `-v`, `--verbose` | Log progress to the terminal |

Output is written next to the input as `FILE.itx`.

### Tooling

- Managed with **uv**; installable package with a `src/` layout.
- Develop on Python **3.15** (`.python-version`); supports **3.12+** (`requires-python`).
- Lint/format with **ruff** (dev dependency; VS Code formats on save).
- Test with **pytest**: `uv run pytest` (tests in `tests/`).
- Check the oldest supported version with
  `uv run --isolated --python 3.12 gerber-to-igor sample.gbr`.

### Layout

| Module | Role |
|---|---|
| `src/gerber_to_igor/cli.py` | Argument parsing, regex tokenizer, `main()` entry point |
| `src/gerber_to_igor/__main__.py` | Enables `python -m gerber_to_igor` |
| `src/gerber_to_igor/gerber_token.py` | `Token`: a command (letter + optional number) or an X/Y coordinate |
| `src/gerber_to_igor/gerber.py` | `Gerber`: interpreter state machine — tool up/down, position, origin, current path |
| `src/gerber_to_igor/point.py` | `Point` (frozen dataclass), unit conversion to inches, addition |
| `src/gerber_to_igor/tool.py` | `Tool` enum (mark, cut, drill, notch) |
| `src/gerber_to_igor/igor_writer.py` | `Igor`: collects paths and points and writes the `.itx` waves, graph, and axes |

### Command mapping

Per `GERBER.pdf`, table 2-1. Input is split into `*`-terminated blocks; each
block is an optional coordinate (either axis may be omitted) followed by zero
or more commands.

| Command | Action |
|---|---|
| `X…Y…`, `X…`, `Y…` | Move (an omitted axis is unchanged); appended to path if a tool is down |
| `D1` | Mark (pen) down |
| `M14`, `B` | Cut (knife) down |
| `D2`, `M15`, `A` | Tool up (sends the path, with the tool's offset, to Igor) |
| `M43`, `R`, `M44` | Drill at the current location (drill offset) |
| `M68`, `E` | Notch at the current location (cut offset) |
| `G4` | Set origin to current location |
| `M70` | Go to origin |
| `G70` / `G71` / `G91` | Switch to thousandths of inches / tenths of mm / hundredths of inches |
| `M0` | End of file; later commands are counted and reported, not processed |
| `H<n>` | Set file number |
| `N<n>` | Set pattern number |
| Speed, sharpening, knife intelligence, stops (`M25`, `M26`, `L`, `O`, `F`, `M60`–`M67`, …) | Ignored quietly (no effect on the plot) |
| anything else (e.g. `M31`) | Logged as "Didn't process command" |
| unparseable blocks (e.g. label text) | Skipped with a warning |

### Igor output

The `.itx` file opens a graph named `GerberPlot` (replacing any existing one)
and adds one X/Y wave pair per tool: `markX/markY` and `cutX/cutY` as lines
(paths separated by NaN), and `drillX/drillY` and `notchX/notchY` as markers.
Colors come from the `plotColors` table in the header. The axes cover all data
with 5% padding, labeled in inches, at a 1:1 aspect ratio.

### Sample data

- `sample.gbr` — square, uses bare `A`/`B` commands.
- `Gerber square with notch and offset.gbr` — square with notches; options in
  `gerber square with notch and offset.txt` (hundredths; mark 1,1; cut 2,2; drill 3,3).
- `GERBER.pdf` — format reference.

## Current status

Phases 1–3 are complete. Both sample files convert to a full `.itx` plot on
Python 3.15 and 3.12, covered by 93 pytest tests. The output has been checked
for syntax by inspection but not yet opened in Igor Pro. Next up: Phase 4.

## Phase 1 — Bug fixes ✅ Done

All items below are fixed. One extra bug was found and fixed along the way:
unhandled `M` commands were silently dropped instead of logged, so `M26`,
`M43`, and `M0` now appear as "Didn't process command".

Ordered by severity.

1. **Startup crash** — `gerber.py:55`: `offsets` is only annotated on the class,
   never initialized, so `self.offsets.append(...)` raises `AttributeError`.
   Initialize the list in `__init__`.
2. **Tokenizer crash on bare commands** — `cli.py:51`: `int(cmd[1:])` raises
   `ValueError` for `A`/`B` (no number). Use `None` when there is no number.
   Also fix the regex class `[A-W,Z]`, which matches a literal comma; intended
   `[A-WZ]`.
3. **`--units` ignored** — the argument has no `type=int`, so `-u 1` arrives as
   `"1"` and never matches `case 1`. Add `type=int` and `choices=[1, 2, 3]`.
4. **Uninitialized `current_location`** — `tool_down` before any move or `M70`
   raises `AttributeError`. Initialize to the origin.
5. **Tool change without tool up mixes paths** — `tool_down` doesn't flush an
   open path, so switching tools merges segments, and it re-appends the current
   point when already down. Flush first; avoid the duplicate point.
6. **Imprecise metric conversion** — `point.py:21` uses `0.0039`; correct value
   is `0.1 / 25.4 ≈ 0.003937` (~1% error).
7. **Output file never closed** — `Igor` opens the `.itx` in `__init__` and never
   closes it. Add a `close()` / context-manager protocol and use it from `main()`.
   (Also flagged by ruff SIM115.)

### Minor cleanups

- `Token.__repr__`: `elif self.value:` hides `M0`; use `is not None`.
- Use `@classmethod` for the `-> Self` constructors (`Token.from_*`,
  `Point.from_xy`); add the missing decorator on `Point.from_text`.
- `Igor.plot_path` is annotated `tool: int` but receives a `Tool` enum.
- `Point.from_xy` has no default `case`; raise on unknown units.
- Move `logging.basicConfig` from `Gerber.__init__` into `main()`.
- Import `Iterator` from `collections.abc` (ruff UP035).
- Add `*.swp` to `.gitignore` (a Vim swap file was swept into a built wheel).

## Phase 2 — Tests ✅ Done

`tests/conftest.py` provides a `make_gerber` fixture whose `RecordingGerber`
captures paths sent to `Igor.plot_path`, so interpreter tests don't depend on
the output format. The end-to-end tests in `tests/test_cli.py` currently check
only the `.itx` header; extend them when Phase 3 writes path data.

- Add `pytest` as a dev dependency and a `tests/` directory.
- Tokenizer tests: coordinates (including negatives), commands with and
  without numbers, both sample files.
- `Gerber` tests: feed short command strings and assert resulting paths, tool
  states, origin handling, and unit conversion.
- End-to-end test: run on each sample file and check the `.itx` output once
  Phase 3 lands.

## Phase 3 — Features ✅ Done

All items below are done.

Out of scope (decided not to implement):

- **Labels (`M31`)**: label text blocks are skipped with a warning; `M31` is
  logged as unprocessed.
- **Pattern and file numbers** (`N`, `H`) are stored but not used in the output.

Not implemented (follow-ups):

- **`M0` vs `M00`**: the spec lists `M0` as end of file and `M00` as program
  stop, but both parse as 0 and are treated as end of file.
- **Block delete (`/`)**: not supported; such blocks are skipped with a warning.


1. **Implement `Igor.plot_path`** — write each path as Igor waves, apply
   `offsets[tool.value]`, color by tool, and track min/max bounds.
2. **Finish the `.itx` output** — use the bounds to set graph axes; write any
   closing commands; close the file.
3. **Drill support** — determine the drill command (likely `M43`) from
   `GERBER.pdf` and map it to `Tool.DRILL`.
4. **Remaining commands** — decide handling for `M0` (end), `M26`, and others
   per the spec; use `N` (pattern) and `H` (file) numbers, e.g. to name waves
   or separate patterns.
5. **Coordinate edge cases** — check the spec for modal/partial coordinates
   (X-only or Y-only) and support them in the tokenizer if allowed.

## Phase 4 — Polish

- README with usage and examples.
- Option to choose the output path.
- Clear error messages for malformed input instead of tracebacks.

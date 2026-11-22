from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from gerber_to_igor.cli import gerber_tokenizer
from gerber_to_igor.gerber import Gerber
from gerber_to_igor.point import Point, Units
from gerber_to_igor.tool import Tool

REPO_ROOT = Path(__file__).parent.parent
SAMPLE = REPO_ROOT / "sample.gbr"
NOTCH_SAMPLE = REPO_ROOT / "Gerber square with notch and offset.gbr"

type RecordedPath = tuple[Tool, list[Point]]


class RecordingGerber(Gerber):
    """A Gerber that records each path and point sent to Igor."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.paths: list[RecordedPath] = []
        self.points: list[tuple[Tool, Point]] = []
        self.igor.plot_path = lambda tool, path: self.paths.append((tool, list(path)))
        self.igor.plot_point = lambda tool, point: self.points.append((tool, point))

    def run(self, text: str) -> list[RecordedPath]:
        for token in gerber_tokenizer(text):
            self.command(token)
        return self.paths


@pytest.fixture
def make_gerber(tmp_path: Path) -> Iterator[Callable[..., RecordingGerber]]:
    created: list[RecordingGerber] = []

    def make(
        units: Units = Units.HUNDREDTHS,
        cutoffset: str = "0,0",
        markoffset: str = "0,0",
        drilloffset: str = "0,0",
    ) -> RecordingGerber:
        gerber = RecordingGerber(
            str(tmp_path / "test.gbr"), units, cutoffset, markoffset, drilloffset
        )
        created.append(gerber)
        return gerber

    yield make

    for gerber in created:
        gerber.igor.close()


def coords(path: list[Point]) -> list[tuple[float, float]]:
    return [(p.x, p.y) for p in path]


def flat(path: list[Point]) -> list[float]:
    """Flatten a path for comparison with pytest.approx."""
    return [c for p in path for c in (p.x, p.y)]

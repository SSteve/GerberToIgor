import pytest

from gerber_to_igor.point import Point, Units


@pytest.mark.parametrize(
    ("units", "x", "expected"),
    [
        (Units.HUNDREDTHS, 150, 1.5),
        (Units.THOUSANDTHS, 1500, 1.5),
        (Units.TENTHS, 254, 1.0),  # 25.4 mm = 1 inch
    ],
)
def test_from_xy_converts_to_inches(units, x, expected):
    point = Point.from_xy(x, -x, units)
    assert point.x == pytest.approx(expected)
    assert point.y == pytest.approx(-expected)


def test_from_xy_rejects_unknown_units():
    with pytest.raises(ValueError, match="Unknown units"):
        Point.from_xy(1, 1, 2)


def test_from_text():
    assert Point.from_text("1.5,-2") == Point(1.5, -2.0)


def test_from_text_rejects_bad_input():
    with pytest.raises(ValueError):
        Point.from_text("1.5")


def test_add():
    assert Point(1, 2) + Point(0.5, -3) == Point(1.5, -1)


def test_is_immutable():
    with pytest.raises(AttributeError):
        Point(1, 2).x = 3

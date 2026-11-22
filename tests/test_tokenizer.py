import pytest

from gerber_to_igor.cli import gerber_tokenizer
from gerber_to_igor.gerber_token import Token

from .conftest import NOTCH_SAMPLE, SAMPLE


def reprs(text: str) -> list[str]:
    return [repr(token) for token in gerber_tokenizer(text)]


def test_commands_with_numbers():
    tokens = list(gerber_tokenizer("H1*M70*D2*"))
    assert [(t.code, t.value) for t in tokens] == [("H", 1), ("M", 70), ("D", 2)]
    assert not any(t.is_coordinate for t in tokens)


def test_commands_without_numbers():
    tokens = list(gerber_tokenizer("B*A*"))
    assert [(t.code, t.value) for t in tokens] == [("B", None), ("A", None)]


def test_zero_value_is_kept():
    [token] = gerber_tokenizer("M0*")
    assert token.value == 0
    assert repr(token) == "M0"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("X100Y200*", (100, 200)),
        ("X-50Y-50*", (-50, -50)),
        ("X1050Y-1050*", (1050, -1050)),
        ("X0Y0*", (0, 0)),
    ],
)
def test_coordinates(text, expected):
    [token] = gerber_tokenizer(text)
    assert token.is_coordinate
    assert (token.x, token.y) == expected


def test_comma_is_not_a_command():
    assert reprs("M14*,*M15*") == ["M14", "M15"]


def test_ignores_whitespace_between_commands():
    assert reprs("D1*\nX10Y20*\r\nD2*") == ["D1", "(10,20)", "D2"]


def test_token_repr():
    assert repr(Token.from_command("D", 1)) == "D1"
    assert repr(Token.from_command("B", None)) == "B"
    assert repr(Token.from_coordinate(3, -4)) == "(3,-4)"


def test_sample_file():
    assert reprs(SAMPLE.read_text()) == [
        "H1", "M70", "D2", "M15", "N1", "M26",
        "(-50,-50)", "D1", "(1050,50)", "D2",
        "(1050,50)", "B", "(1050,1050)", "A",
        "(1050,-1050)", "D1", "(-50,1050)", "D2",
        "(50,1050)", "M14", "(50,50)", "D2", "M15",
        "M70", "M0",
    ]  # fmt: skip


def test_notch_sample_file():
    tokens = list(gerber_tokenizer(NOTCH_SAMPLE.read_text()))
    assert len(tokens) == 43
    assert sum(t.is_coordinate for t in tokens) == 17
    assert repr(tokens[-1]) == "M0"

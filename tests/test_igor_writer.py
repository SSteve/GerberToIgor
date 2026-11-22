from gerber_to_igor.igor_writer import Igor


def test_writes_header(tmp_path):
    output = tmp_path / "out.itx"
    with Igor(str(output)):
        pass
    lines = output.read_text().splitlines()
    assert lines[0] == "IGOR"
    assert lines[1].startswith("X Display")
    assert "WAVES/O/N=(5,3) plotColors" in lines
    assert "WAVES/O/N=(4,4) markerColors" in lines
    assert lines[-1] == "X Variable/G logWaveQuantity=10"
    assert lines.count("BEGIN") == lines.count("END") == 2


def test_context_manager_closes_file(tmp_path):
    with Igor(str(tmp_path / "out.itx")) as igor:
        assert not igor.output_file.closed
    assert igor.output_file.closed


def test_starts_with_empty_bounds(tmp_path):
    with Igor(str(tmp_path / "out.itx")) as igor:
        assert igor.min_x > igor.max_x
        assert igor.min_y > igor.max_y

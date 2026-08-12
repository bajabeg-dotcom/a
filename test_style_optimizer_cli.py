#!/usr/bin/env python3
"""
KORG PA800 Style Optimizer - CLI Tests
"""

import json
import struct
import sys
import tempfile
from pathlib import Path

import pytest

from style_optimizer_core import StyleOptimizerApp
from style_optimizer_cli import StyleOptimizerCLI, find_default_db_path, main


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def behaviour_db():
    return {
        "style_rules": {
            "DRUM": {
                "part": "DRUM",
                "role": "rhythm foundation",
                "velocity_zones": [
                    {"velocity_range": "1-40", "center": 20, "character": "soft"},
                    {"velocity_range": "41-90", "center": 65, "character": "normal"},
                    {"velocity_range": "91-127", "center": 110, "character": "accent"},
                ],
            }
        }
    }


@pytest.fixture
def db_path(behaviour_db):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(behaviour_db, f)
        return Path(f.name)


@pytest.fixture
def cli(db_path):
    instance = StyleOptimizerCLI.__new__(StyleOptimizerCLI)
    instance.db_path = db_path
    instance.app = StyleOptimizerApp(db_path)
    return instance


def _write_midi(path: Path, with_notes: bool = True):
    with open(path, "wb") as f:
        f.write(b"MThd")
        f.write(struct.pack(">I", 6))
        f.write(struct.pack(">H", 1))
        f.write(struct.pack(">H", 1))
        f.write(struct.pack(">H", 480))

        track = bytearray()
        if with_notes:
            track.extend(b"\x00\xC0\x00")  # Program change, channel 0 -> DRUM
            track.extend(b"\x00\x90\x24\x32")  # Note On, vel 50
            track.extend(b"\x83\x60\x80\x24\x40")  # Note Off
        track.extend(b"\x00\xFF\x2F\x00")

        f.write(b"MTrk")
        f.write(struct.pack(">I", len(track)))
        f.write(bytes(track))


@pytest.fixture
def midi_file(tmp_path):
    path = tmp_path / "input.mid"
    _write_midi(path, with_notes=True)
    return path


@pytest.fixture
def empty_midi_file(tmp_path):
    path = tmp_path / "empty.mid"
    _write_midi(path, with_notes=False)
    return path


# ============================================================================
# DEFAULT DB RESOLUTION
# ============================================================================

class TestFindDefaultDbPath:
    def test_returns_first_existing_candidate(self, monkeypatch, tmp_path):
        existing = tmp_path / "style_behaviour_database.json"
        existing.write_text("{}")
        monkeypatch.setattr(
            "style_optimizer_cli.DEFAULT_DB_CANDIDATES",
            (tmp_path / "missing.json", existing),
        )
        assert find_default_db_path() == existing

    def test_returns_first_candidate_when_none_exist(self, monkeypatch, tmp_path):
        first = tmp_path / "a.json"
        second = tmp_path / "b.json"
        monkeypatch.setattr("style_optimizer_cli.DEFAULT_DB_CANDIDATES", (first, second))
        assert find_default_db_path() == first


# ============================================================================
# OPTIMIZE COMMAND
# ============================================================================

class TestCLIOptimize:
    def test_optimize_success(self, cli, midi_file, tmp_path):
        output = tmp_path / "output.mid"
        assert cli.optimize(str(midi_file), str(output), "AUTHENTIC") is True
        assert output.exists()

    def test_optimize_missing_input(self, cli, tmp_path):
        output = tmp_path / "output.mid"
        assert cli.optimize(str(tmp_path / "missing.mid"), str(output)) is False
        assert not output.exists()

    def test_optimize_invalid_strategy(self, cli, midi_file, tmp_path):
        output = tmp_path / "output.mid"
        assert cli.optimize(str(midi_file), str(output), "NOT_A_STRATEGY") is False

    def test_optimize_empty_midi_reports_failure(self, cli, empty_midi_file, tmp_path):
        output = tmp_path / "output.mid"
        assert cli.optimize(str(empty_midi_file), str(output)) is False


# ============================================================================
# ANALYZE COMMAND
# ============================================================================

class TestCLIAnalyze:
    def test_analyze_success(self, cli, midi_file):
        assert cli.analyze(str(midi_file)) is True

    def test_analyze_missing_input(self, cli, tmp_path):
        assert cli.analyze(str(tmp_path / "missing.mid")) is False

    def test_analyze_empty_midi_still_returns_true(self, cli, empty_midi_file):
        assert cli.analyze(str(empty_midi_file)) is True


# ============================================================================
# BATCH COMMAND
# ============================================================================

class TestCLIBatch:
    def test_batch_success(self, cli, tmp_path):
        input_dir = tmp_path / "in"
        input_dir.mkdir()
        output_dir = tmp_path / "out"

        _write_midi(input_dir / "one.mid", with_notes=True)
        _write_midi(input_dir / "two.mid", with_notes=True)

        assert cli.batch(str(input_dir), str(output_dir), "AUTHENTIC") is True
        assert (output_dir / "one_optimized.mid").exists()
        assert (output_dir / "two_optimized.mid").exists()

    def test_batch_missing_input_dir(self, cli, tmp_path):
        assert cli.batch(str(tmp_path / "missing"), str(tmp_path / "out")) is False

    def test_batch_no_midi_files(self, cli, tmp_path):
        input_dir = tmp_path / "in"
        input_dir.mkdir()
        assert cli.batch(str(input_dir), str(tmp_path / "out")) is False

    def test_batch_invalid_strategy(self, cli, tmp_path):
        input_dir = tmp_path / "in"
        input_dir.mkdir()
        _write_midi(input_dir / "one.mid", with_notes=True)
        assert cli.batch(str(input_dir), str(tmp_path / "out"), "BOGUS") is False

    def test_batch_reports_failed_files(self, cli, tmp_path):
        input_dir = tmp_path / "in"
        input_dir.mkdir()
        output_dir = tmp_path / "out"

        _write_midi(input_dir / "good.mid", with_notes=True)
        _write_midi(input_dir / "empty.mid", with_notes=False)

        assert cli.batch(str(input_dir), str(output_dir), "AUTHENTIC") is False
        assert (output_dir / "good_optimized.mid").exists()
        assert not (output_dir / "empty_optimized.mid").exists()


# ============================================================================
# ARGUMENT PARSING / MAIN ENTRY POINT
# ============================================================================

def _fake_cli_init(db_path):
    def _init(self):
        self.db_path = db_path
        self.app = StyleOptimizerApp(db_path)
    return _init


class TestCLIMain:
    def test_main_no_command_prints_help_and_exits(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["style_optimizer_cli.py"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        assert "usage" in capsys.readouterr().out.lower()

    def test_main_optimize_success_exits_zero(self, monkeypatch, db_path, midi_file, tmp_path):
        output = tmp_path / "output.mid"
        monkeypatch.setattr(
            sys, "argv",
            ["style_optimizer_cli.py", "optimize", str(midi_file), str(output)],
        )
        monkeypatch.setattr(StyleOptimizerCLI, "__init__", _fake_cli_init(db_path))

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        assert output.exists()

    def test_main_analyze_missing_file_exits_one(self, monkeypatch, db_path, tmp_path):
        monkeypatch.setattr(
            sys, "argv",
            ["style_optimizer_cli.py", "analyze", str(tmp_path / "missing.mid")],
        )
        monkeypatch.setattr(StyleOptimizerCLI, "__init__", _fake_cli_init(db_path))

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_cli_init_exits_when_database_missing(self, monkeypatch, tmp_path):
        missing_db = tmp_path / "does_not_exist.json"
        monkeypatch.setattr("style_optimizer_cli.find_default_db_path", lambda: missing_db)
        with pytest.raises(SystemExit) as exc:
            StyleOptimizerCLI()
        assert exc.value.code == 1

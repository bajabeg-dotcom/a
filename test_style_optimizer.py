#!/usr/bin/env python3
"""
KORG PA800 Style Optimizer - Core Engine Test Suite
"""

import json
import struct
import tempfile
from pathlib import Path

import pytest

from midi_optimizer_core import MIDINote, OptimizationResult, OptimizationStrategy
from style_optimizer_core import (
    CHANNEL_TO_STYLE_PART,
    StyleOptimizerApp,
    StylePart,
    StylePartBehaviourOptimizer,
    style_part_for_channel,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_behaviour_db():
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
            },
            "BASS": {
                "part": "BASS",
                "role": "bass",
                "velocity_zones": [
                    {"velocity_range": "1-55", "center": 40, "character": "soft"},
                    {"velocity_range": "56-127", "center": 90, "character": "strong"},
                ],
            },
        }
    }


@pytest.fixture
def db_path(sample_behaviour_db):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_behaviour_db, f)
        return Path(f.name)


def _note(channel=0, velocity=65, note=60, program=0, start_time=0, duration=100):
    return MIDINote(note=note, velocity=velocity, channel=channel, program=program,
                     start_time=start_time, duration=duration)


def _write_midi(path: Path, notes):
    """notes: list of (channel, program, pitch, velocity)"""
    with open(path, "wb") as f:
        f.write(b"MThd")
        f.write(struct.pack(">I", 6))
        f.write(struct.pack(">H", 1))
        f.write(struct.pack(">H", 1))
        f.write(struct.pack(">H", 480))

        track = bytearray()
        for channel, program, pitch, velocity in notes:
            track.extend(bytes([0x00, 0xC0 | channel, program]))
            track.extend(bytes([0x00, 0x90 | channel, pitch, velocity]))
            track.extend(bytes([0x0A, 0x80 | channel, pitch, 0x40]))
        track.extend(b"\x00\xFF\x2F\x00")

        f.write(b"MTrk")
        f.write(struct.pack(">I", len(track)))
        f.write(bytes(track))


# ============================================================================
# CHANNEL -> STYLE PART MAPPING
# ============================================================================

class TestChannelMapping:
    def test_channel_0_is_drum(self):
        assert style_part_for_channel(0) == StylePart.DRUM

    def test_channel_2_is_bass(self):
        assert style_part_for_channel(2) == StylePart.BASS

    def test_channel_7_is_phrase2(self):
        assert style_part_for_channel(7) == StylePart.PHRASE2

    def test_channel_9_is_other(self):
        assert style_part_for_channel(9) == StylePart.OTHER

    def test_all_eight_channels_mapped(self):
        assert set(CHANNEL_TO_STYLE_PART.keys()) == set(range(8))
        assert StylePart.OTHER not in CHANNEL_TO_STYLE_PART.values()


# ============================================================================
# STYLE PART BEHAVIOUR OPTIMIZER
# ============================================================================

class TestStylePartBehaviourOptimizer:
    def test_get_part_behaviour_known(self, sample_behaviour_db):
        optimizer = StylePartBehaviourOptimizer(sample_behaviour_db)
        behaviour = optimizer.get_part_behaviour(StylePart.DRUM)
        assert behaviour["role"] == "rhythm foundation"

    def test_get_part_behaviour_unknown_part(self, sample_behaviour_db):
        optimizer = StylePartBehaviourOptimizer(sample_behaviour_db)
        assert optimizer.get_part_behaviour(StylePart.PAD) is None

    def test_optimize_velocity_no_behaviour_for_part(self, sample_behaviour_db):
        optimizer = StylePartBehaviourOptimizer(sample_behaviour_db)
        note = _note(channel=5, velocity=70)  # channel 5 -> PAD, not in db
        result = optimizer.optimize_velocity(note, OptimizationStrategy.AUTHENTIC)
        assert result.optimized_velocity == 70
        assert result.confidence == "UNKNOWN"

    def test_optimize_velocity_authentic_snaps_to_zone_center(self, sample_behaviour_db):
        optimizer = StylePartBehaviourOptimizer(sample_behaviour_db)
        note = _note(channel=0, velocity=50)  # DRUM, in 41-90 zone -> center 65
        result = optimizer.optimize_velocity(note, OptimizationStrategy.AUTHENTIC)
        assert result.optimized_velocity == 65
        assert result.original_velocity == 50
        assert result.adjustment == 15

    def test_optimize_velocity_balanced_leaves_close_notes(self):
        # BALANCED returns on the first zone whose center is >15 away from the
        # note, so a meaningful "stays unchanged" case needs every zone
        # center within 15 of the note velocity -- use a single-zone db.
        single_zone_db = {
            "style_rules": {
                "DRUM": {
                    "velocity_zones": [
                        {"velocity_range": "41-90", "center": 65, "character": "normal"},
                    ],
                }
            }
        }
        optimizer = StylePartBehaviourOptimizer(single_zone_db)
        note = _note(channel=0, velocity=68)  # close to center 65, delta 3 < 15
        result = optimizer.optimize_velocity(note, OptimizationStrategy.BALANCED)
        assert result.optimized_velocity == 68

    def test_optimize_velocity_balanced_adjusts_far_notes(self, sample_behaviour_db):
        optimizer = StylePartBehaviourOptimizer(sample_behaviour_db)
        note = _note(channel=0, velocity=0)  # >15 away from the first DRUM zone's center (20)
        result = optimizer.optimize_velocity(note, OptimizationStrategy.BALANCED)
        assert result.optimized_velocity == 20

    def test_optimize_velocity_aggressive_pushes_to_extremes(self, sample_behaviour_db):
        optimizer = StylePartBehaviourOptimizer(sample_behaviour_db)
        note = _note(channel=2, velocity=120)  # BASS, high -> should hit zone max
        result = optimizer.optimize_velocity(note, OptimizationStrategy.AGGRESSIVE)
        assert result.optimized_velocity == 127

    def test_optimize_velocity_expressive_biases_high(self, sample_behaviour_db):
        optimizer = StylePartBehaviourOptimizer(sample_behaviour_db)
        note = _note(channel=2, velocity=100)  # BASS, strong band
        result = optimizer.optimize_velocity(note, OptimizationStrategy.EXPRESSIVE)
        assert 56 <= result.optimized_velocity <= 127

    def test_optimize_midi_preserves_note_count_and_pitch(self, sample_behaviour_db):
        optimizer = StylePartBehaviourOptimizer(sample_behaviour_db)
        notes = [_note(channel=0, note=36, velocity=50), _note(channel=2, note=40, velocity=60)]
        optimized, results = optimizer.optimize_midi(notes, OptimizationStrategy.AUTHENTIC)

        assert len(optimized) == 2
        assert len(results) == 2
        assert [n.note for n in optimized] == [36, 40]
        assert all(isinstance(r, OptimizationResult) for r in results)


# ============================================================================
# STYLE OPTIMIZER APP
# ============================================================================

class TestStyleOptimizerApp:
    def test_app_creation_loads_db(self, db_path):
        app = StyleOptimizerApp(db_path)
        assert "style_rules" in app.behaviour_db
        assert isinstance(app.optimizer, StylePartBehaviourOptimizer)

    def test_app_creation_missing_db_falls_back_empty(self, tmp_path):
        app = StyleOptimizerApp(tmp_path / "missing.json")
        assert app.behaviour_db == {"style_rules": {}}

    def test_optimize_file_writes_output(self, db_path, tmp_path):
        input_path = tmp_path / "input.mid"
        output_path = tmp_path / "output.mid"
        _write_midi(input_path, [(0, 0, 36, 50), (2, 34, 40, 60)])

        app = StyleOptimizerApp(db_path)
        result = app.optimize_file(input_path, output_path, OptimizationStrategy.AUTHENTIC)

        assert result["success"] is True
        assert output_path.exists()
        assert result["total_notes"] == 2

    def test_optimize_file_no_notes_reports_error(self, db_path, tmp_path):
        input_path = tmp_path / "empty.mid"
        output_path = tmp_path / "output.mid"
        _write_midi(input_path, [])

        app = StyleOptimizerApp(db_path)
        result = app.optimize_file(input_path, output_path, OptimizationStrategy.AUTHENTIC)

        assert result == {"success": False, "error": "No notes found"}
        assert not output_path.exists()

    def test_analyze_file_groups_by_style_part(self, db_path, tmp_path):
        input_path = tmp_path / "input.mid"
        _write_midi(input_path, [
            (0, 0, 36, 50),   # DRUM
            (0, 0, 38, 60),   # DRUM
            (2, 34, 40, 70),  # BASS
        ])

        app = StyleOptimizerApp(db_path)
        result = app.analyze_file(input_path)

        assert result["total_notes"] == 3
        assert result["parts"]["DRUM"] == 2
        assert result["parts"]["BASS"] == 1
        assert result["velocity_stats"]["DRUM"]["min"] == 50
        assert result["velocity_stats"]["DRUM"]["max"] == 60

    def test_analyze_file_no_notes_reports_error(self, db_path, tmp_path):
        input_path = tmp_path / "empty.mid"
        _write_midi(input_path, [])

        app = StyleOptimizerApp(db_path)
        result = app.analyze_file(input_path)

        assert result == {"error": "No notes found"}


# ============================================================================
# DEFAULT DATABASE SANITY CHECKS
# ============================================================================

class TestDefaultStyleBehaviourDatabase:
    """Sanity-check the shipped style_behaviour_database.json"""

    @pytest.fixture
    def default_db_path(self):
        path = Path(__file__).parent / "style_behaviour_database.json"
        if not path.exists():
            pytest.skip("style_behaviour_database.json not present")
        return path

    def test_all_eight_style_parts_defined(self, default_db_path):
        with open(default_db_path) as f:
            db = json.load(f)

        expected = {p.value for p in StylePart if p != StylePart.OTHER}
        assert expected.issubset(set(db["style_rules"].keys()))

    def test_every_part_has_velocity_zones(self, default_db_path):
        with open(default_db_path) as f:
            db = json.load(f)

        for part_name, rule in db["style_rules"].items():
            assert rule.get("velocity_zones"), f"{part_name} has no velocity_zones"

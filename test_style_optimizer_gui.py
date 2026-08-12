#!/usr/bin/env python3
"""
KORG PA800 Style Optimizer - GUI Tests

Requires a display (real or Xvfb) since tkinter needs one to create widgets,
e.g. run with: xvfb-run -a pytest test_style_optimizer_gui.py
"""

import json
import struct
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import pytest

from style_optimizer_core import StyleOptimizerApp
from style_optimizer_gui import StyleOptimizerGUI


def _tk_root():
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError as e:
        pytest.skip(f"No display available for tkinter: {e}")
    return root


@pytest.fixture
def root():
    r = _tk_root()
    yield r
    r.destroy()


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


def _write_midi(path: Path, with_notes: bool = True):
    with open(path, "wb") as f:
        f.write(b"MThd")
        f.write(struct.pack(">I", 6))
        f.write(struct.pack(">H", 1))
        f.write(struct.pack(">H", 1))
        f.write(struct.pack(">H", 480))

        track = bytearray()
        if with_notes:
            track.extend(b"\x00\xC0\x00")
            track.extend(b"\x00\x90\x24\x32")
            track.extend(b"\x83\x60\x80\x24\x40")
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
def gui(root, db_path):
    with patch("style_optimizer_gui.Path.home", return_value=db_path.parent):
        app = StyleOptimizerGUI(root)
    app.db_path = db_path
    app._load_database()
    return app


# ============================================================================
# INITIALIZATION
# ============================================================================

class TestGUIInit:
    def test_creates_without_error(self, root):
        gui = StyleOptimizerGUI(root)
        assert gui.root is root
        assert gui.current_file is None

    def test_no_database_found_sets_status(self, root):
        with patch("style_optimizer_gui.Path.exists", return_value=False):
            gui = StyleOptimizerGUI(root)
        assert gui.app is None
        assert "not found" in gui.db_status_var.get().lower()


class TestGUIDatabaseLoading:
    def test_load_database_success(self, gui, db_path):
        gui.db_path = db_path
        gui._load_database()
        assert isinstance(gui.app, StyleOptimizerApp)
        assert "loaded" in gui.db_status_var.get().lower()

    def test_load_database_missing_path(self, gui):
        gui.db_path = None
        gui._load_database()
        assert gui.app is None
        assert "not found" in gui.db_status_var.get().lower()

    def test_load_database_invalid_json_falls_back_empty(self, gui, tmp_path):
        bad_db = tmp_path / "bad.json"
        bad_db.write_text("not valid json")
        gui.db_path = bad_db
        gui._load_database()
        assert isinstance(gui.app, StyleOptimizerApp)
        assert gui.app.behaviour_db == {"style_rules": {}}


# ============================================================================
# FILE HANDLING
# ============================================================================

class TestGUIFileHandling:
    def test_load_file_sets_current_file_and_output(self, gui, midi_file):
        gui.load_file(midi_file)
        assert gui.current_file == midi_file
        assert midi_file.name in gui.file_path_var.get()
        assert gui.output_path_var.get().endswith("input_optimized.mid")

    def test_load_missing_file_shows_error(self, gui, tmp_path):
        missing = tmp_path / "missing.mid"
        with patch("style_optimizer_gui.messagebox.showerror") as mock_error:
            gui.load_file(missing)
        mock_error.assert_called_once()
        assert gui.current_file is None

    def test_reset_clears_state(self, gui, midi_file):
        gui.load_file(midi_file)
        gui.reset()
        assert gui.current_file is None
        assert gui.output_path_var.get() == ""
        assert gui.status_var.get() == "Ready"


# ============================================================================
# STRATEGY DESCRIPTION
# ============================================================================

class TestGUIStrategyDescription:
    def test_update_description_known_strategy(self, gui):
        gui.strategy_var.set("EXPRESSIVE")
        assert "dynamics" in gui.description_var.get().lower()

    def test_update_description_unknown_strategy_is_empty(self, gui):
        gui.strategy_var.set("NOT_A_REAL_STRATEGY")
        assert gui.description_var.get() == ""


# ============================================================================
# ANALYZE / OPTIMIZE ACTIONS
# ============================================================================

class TestGUIActions:
    def test_analyze_file_without_database_shows_error(self, gui, midi_file):
        gui.app = None
        gui.current_file = midi_file
        with patch("style_optimizer_gui.messagebox.showerror") as mock_error:
            gui.analyze_file()
        mock_error.assert_called_once()

    def test_analyze_file_without_selection_shows_warning(self, gui):
        gui.current_file = None
        with patch("style_optimizer_gui.messagebox.showwarning") as mock_warn:
            gui.analyze_file()
        mock_warn.assert_called_once()

    def test_analyze_file_runs_in_background_thread(self, gui, midi_file):
        gui.load_file(midi_file)
        with patch("style_optimizer_gui.threading.Thread") as mock_thread_cls:
            gui.analyze_file()
        mock_thread_cls.assert_called_once()
        assert mock_thread_cls.call_args.kwargs.get("daemon") is True

    def test_optimize_without_database_shows_error(self, gui, midi_file):
        gui.app = None
        gui.load_file(midi_file)
        with patch("style_optimizer_gui.messagebox.showerror") as mock_error:
            gui.optimize()
        mock_error.assert_called_once()

    def test_optimize_without_file_shows_warning(self, gui):
        gui.current_file = None
        with patch("style_optimizer_gui.messagebox.showwarning") as mock_warn:
            gui.optimize()
        mock_warn.assert_called_once()

    def test_optimize_without_output_path_shows_warning(self, gui, midi_file):
        gui.current_file = midi_file
        gui.output_path_var.set("")
        with patch("style_optimizer_gui.messagebox.showwarning") as mock_warn:
            gui.optimize()
        mock_warn.assert_called_once()

    def test_optimize_runs_in_background_thread(self, gui, midi_file):
        gui.load_file(midi_file)
        with patch("style_optimizer_gui.threading.Thread") as mock_thread_cls:
            gui.optimize()
        mock_thread_cls.assert_called_once()

    def test_batch_process_without_database_shows_error(self, gui):
        gui.app = None
        with patch("style_optimizer_gui.messagebox.showerror") as mock_error:
            gui.batch_process()
        mock_error.assert_called_once()

    def test_batch_process_no_files_selected_returns_early(self, gui):
        with patch("style_optimizer_gui.filedialog.askopenfilenames", return_value=()):
            with patch("style_optimizer_gui.threading.Thread") as mock_thread_cls:
                gui.batch_process()
        mock_thread_cls.assert_not_called()

    def test_batch_process_no_output_dir_returns_early(self, gui, midi_file):
        with patch("style_optimizer_gui.filedialog.askopenfilenames", return_value=(str(midi_file),)):
            with patch("style_optimizer_gui.filedialog.askdirectory", return_value=""):
                with patch("style_optimizer_gui.threading.Thread") as mock_thread_cls:
                    gui.batch_process()
        mock_thread_cls.assert_not_called()


# ============================================================================
# FILE BROWSING DIALOGS
# ============================================================================

class TestGUIDialogs:
    def test_browse_file_loads_selection(self, gui, midi_file):
        with patch("style_optimizer_gui.filedialog.askopenfilename", return_value=str(midi_file)):
            gui.browse_file()
        assert gui.current_file == midi_file

    def test_browse_file_cancelled_does_nothing(self, gui):
        with patch("style_optimizer_gui.filedialog.askopenfilename", return_value=""):
            gui.browse_file()
        assert gui.current_file is None

    def test_browse_database_updates_and_reloads(self, gui, db_path):
        with patch("style_optimizer_gui.filedialog.askopenfilename", return_value=str(db_path)):
            gui.browse_database()
        assert gui.db_path == db_path
        assert isinstance(gui.app, StyleOptimizerApp)

    def test_browse_output_sets_path(self, gui, tmp_path):
        target = tmp_path / "chosen_output.mid"
        with patch("style_optimizer_gui.filedialog.asksaveasfilename", return_value=str(target)):
            gui.browse_output()
        assert gui.output_path_var.get() == str(target)


# ============================================================================
# TEXT DISPLAY HELPERS
# ============================================================================

class TestGUIDisplayHelpers:
    def test_update_analysis_display_sets_text(self, gui):
        gui._update_analysis_display("hello")
        assert gui.analysis_text.get("1.0", tk.END).strip() == "hello"

    def test_log_result_replaces_text(self, gui):
        gui._log_result("first")
        gui._log_result("second")
        assert gui.results_text.get("1.0", tk.END).strip() == "second"

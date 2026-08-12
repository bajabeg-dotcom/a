# 🎹 KORG PA800 Style Optimizer

Optimizes MIDI Style-pattern files by **Style track role** (Drum, Percussion,
Bass, Chord1, Chord2, Pad, Phrase1, Phrase2) instead of by GM instrument
program the way `midi_optimizer_core.py` does.

## How it differs from the MIDI Optimizer

The MIDI Optimizer looks up each note's velocity rules by its GM **program**
(instrument sound), using `ai_database.json` — a database built from forensic
analysis of factory Style MIDI data.

The Style Optimizer instead looks up rules by the note's **MIDI channel**,
mapped to the conventional 8-channel KORG/Yamaha Style track assignment:

| Channel | Style Part |
|---------|------------|
| 1 | Drum |
| 2 | Percussion |
| 3 | Bass |
| 4 | Chord1 |
| 5 | Chord2 |
| 6 | Pad |
| 7 | Phrase1 |
| 8 | Phrase2 |

Channels 9-16 are treated as `OTHER` (free/original data tracks) and are left
unchanged.

Its rules live in `style_behaviour_database.json`. Unlike `ai_database.json`,
this is a **hand-authored heuristic default profile** per Style part, not
data mined from real factory Styles — tune the `velocity_zones` in that file
to taste.

## Usage

```bash
# Command line
python style_optimizer_cli.py optimize input.mid output.mid --strategy authentic
python style_optimizer_cli.py analyze input.mid
python style_optimizer_cli.py batch /input /output --strategy authentic

# Desktop GUI
python style_optimizer_gui.py

# Python API
from style_optimizer_core import StyleOptimizerApp
from midi_optimizer_core import OptimizationStrategy

app = StyleOptimizerApp(Path("style_behaviour_database.json"))
app.optimize_file(Path("input.mid"), Path("output.mid"), OptimizationStrategy.AUTHENTIC)
```

Strategies (`AUTHENTIC`, `EXPRESSIVE`, `BALANCED`, `AGGRESSIVE`) behave the
same as in the MIDI Optimizer, just applied per Style part rather than per
instrument program.

## Tests

```bash
pytest test_style_optimizer.py test_style_optimizer_cli.py test_style_optimizer_gui.py
```

GUI tests need a display; run with `xvfb-run -a pytest ...` in headless
environments.

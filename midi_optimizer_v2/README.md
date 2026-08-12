# 🎹 KORG PA800 MIDI Optimizer v2.0

**Professional MIDI enhancement using factory sound behavior patterns**

---

## ✨ What's New in v2.0

### Major Enhancements

- **🆕 Two New Strategies**: NATURAL (human-like variations) and PRECISE (exact matching)
- **📊 Comprehensive Statistics**: Detailed performance metrics and velocity distribution analysis
- **⚡ Improved Performance**: Optimized parsing and processing for large files
- **🔍 Enhanced Analysis**: Deeper MIDI structure insights with register distribution
- **📝 Detailed Reports**: Generate comprehensive optimization reports
- **🛡️ Better Error Handling**: Robust error recovery and logging
- **📈 Progress Tracking**: Real-time progress callbacks for batch operations
- **🎼 Track Preservation**: Maintain original track structure and order

### Technical Improvements

- Extended MIDI format support (Format 0, 1, 2)
- MD5 checksum verification for file integrity
- Configurable optimization parameters
- Enhanced GM program name mapping
- Improved velocity zone matching algorithms
- Context-aware optimization options

---

## Quick Start

### Command Line (Recommended)

```bash
# Show information
python midi_optimizer_cli.py info

# Optimize single file
python midi_optimizer_cli.py optimize input.mid output.mid

# Use different strategy
python midi_optimizer_cli.py optimize song.mid song_opt.mid --strategy EXPRESSIVE

# Analyze MIDI structure
python midi_optimizer_cli.py analyze song.mid

# Batch process directory
python midi_optimizer_cli.py batch ./midi_files ./output --strategy NATURAL

# JSON output for automation
python midi_optimizer_cli.py analyze song.mid --json
```

### Python API

```python
from midi_optimizer_core import MIDIOptimizerApp, OptimizationStrategy

# Initialize
app = MIDIOptimizerApp("ai_database.json")

# Optimize
result = app.optimize_file(
    "input.mid", 
    "output.mid", 
    OptimizationStrategy.EXPRESSIVE,
    generate_report=True
)

# Analyze
analysis = app.analyze_file("song.mid")

# Batch process
results = app.batch_optimize("./midi", "./output", OptimizationStrategy.NATURAL)
```

---

## Optimization Strategies

| Strategy | Intensity | Best For | Description |
|----------|-----------|----------|-------------|
| **AUTHENTIC** | 70% | Professional productions | Match factory patterns exactly |
| **EXPRESSIVE** | 85% | Emotional performances | Emphasize dynamics |
| **BALANCED** | 40% | Safe first choice | Conservative adjustments |
| **AGGRESSIVE** | 100% | Bold artistic statements | Maximum character |
| **NATURAL** ⭐ | 60% | Human-like feel | Add subtle variations |
| **PRECISE** | 90% | Exact reproduction | Minimal deviation |

---

## Features

### 🎵 Core Capabilities

- **Smart Velocity Optimization**: AI-powered velocity adjustment based on 107 KORG sound models
- **Multi-Strategy Support**: 6 distinct optimization approaches
- **Batch Processing**: Process entire directories efficiently
- **Detailed Analysis**: Understand your MIDI structure before optimizing
- **Format Preservation**: Maintains original MIDI structure and timing

### 📊 Analytics

- Note count and program usage statistics
- Velocity distribution (soft/medium/loud)
- Register distribution (sub-bass to very-high)
- Per-program velocity ranges
- Track metadata extraction
- Processing performance metrics

### 🔧 Technical Features

- Pure Python implementation (no external dependencies)
- Cross-platform (Windows, macOS, Linux)
- MIDI Format 0, 1, and 2 support
- General MIDI program name mapping
- File integrity verification (MD5)
- Comprehensive error handling
- Logging support

---

## Installation

### Requirements

- **Python**: 3.7 or higher
- **OS**: Windows, macOS, or Linux
- **RAM**: 100 MB minimum
- **Disk**: ~3 MB for application + space for MIDI files

### Setup

1. Copy all files to a directory
2. Ensure `ai_database.json` is present
3. Run from command line:

```bash
cd midi_optimizer_v2
python midi_optimizer_cli.py info
```

---

## Usage Examples

### Example 1: Basic Optimization

```bash
python midi_optimizer_cli.py optimize my_song.mid my_song_optimized.mid
```

### Example 2: Expressive Enhancement

```bash
python midi_optimizer_cli.py optimize ballad.mid ballad_expressive.mid --strategy EXPRESSIVE --report
```

### Example 3: Analyze Before Optimizing

```bash
# First analyze
python midi_optimizer_cli.py analyze complex_arrangement.mid

# Then optimize based on analysis
python midi_optimizer_cli.py optimize complex_arrangement.mid optimized.mid --strategy BALANCED
```

### Example 4: Batch Processing

```bash
# Process entire library
python midi_optimizer_cli.py batch ~/Music/MIDI ~/Music/Optimized --strategy AUTHENTIC

# Process only .MID files (uppercase)
python midi_optimizer_cli.py batch ./input ./output --pattern "*.MID"
```

### Example 5: Automation with JSON

```bash
# Get JSON output for scripting
python midi_optimizer_cli.py analyze song.mid --json > analysis.json

# Parse in your script
python -c "import json; data=json.load(open('analysis.json')); print(data['total_notes'])"
```

---

## API Reference

### MIDIOptimizerApp

```python
from midi_optimizer_core import MIDIOptimizerApp, OptimizationStrategy

app = MIDIOptimizerApp("ai_database.json")

# Optimize single file
result = app.optimize_file(
    input_path=Path("input.mid"),
    output_path=Path("output.mid"),
    strategy=OptimizationStrategy.AUTHENTIC,
    generate_report=False
)

# Analyze file
analysis = app.analyze_file(Path("song.mid"))

# Batch optimize
results = app.batch_optimize(
    input_dir=Path("./midi"),
    output_dir=Path("./output"),
    strategy=OptimizationStrategy.NATURAL,
    pattern="*.mid"
)
```

### OptimizationResult

```python
@dataclass
class OptimizationResult:
    original_velocity: int
    optimized_velocity: int
    reason: str
    confidence: str
    strategy_used: str
    zone_matched: str
    adjustment: int
    timestamp: str
    
    @property
    def improvement_percentage(self) -> float: ...
```

### OptimizationStatistics

```python
@dataclass
class OptimizationStatistics:
    total_notes: int
    adjusted_notes: int
    unchanged_notes: int
    average_adjustment: float
    max_adjustment: int
    min_adjustment: int
    processing_time_ms: float
    notes_per_second: float
    strategy: str
    file_size_original: int
    file_size_optimized: int
    compression_ratio: float
    program_statistics: Dict
    register_statistics: Dict
    velocity_distribution_before: Dict
    velocity_distribution_after: Dict
```

---

## File Structure

```
midi_optimizer_v2/
├── midi_optimizer_core.py      # Core engine
├── midi_optimizer_cli.py       # Command-line interface
├── ai_database.json            # Sound behaviour models (required)
├── phase1_usage_fingerprints.json  # Usage patterns
├── phase2_velocity_behaviour.json  # Velocity analysis
├── sound_behaviour_models.json     # Complete models
├── test_*.py                   # Test suite
├── *.bat                       # Windows batch files
├── *.md                        # Documentation
├── pytest.ini                  # Test configuration
└── requirements-test.txt       # Test dependencies
```

---

## Troubleshooting

### Database Not Found

```
❌ Sound Behaviour Database not found
```

**Solution**: Ensure `ai_database.json` is in the current directory or specify path:

```bash
python midi_optimizer_cli.py --database /path/to/ai_database.json optimize ...
```

### No Notes Found

```
❌ No notes found in MIDI file
```

**Solution**: Verify the MIDI file is valid:

```bash
python midi_optimizer_cli.py analyze problematic_file.mid
```

### Import Error

```
❌ Error: Could not import midi_optimizer_core
```

**Solution**: Ensure both `.py` files are in the same directory:

```bash
ls -la *.py
```

---

## Performance Benchmarks

| File Size | Notes | Processing Time | Throughput |
|-----------|-------|----------------|------------|
| Small (< 10 KB) | < 1,000 | < 50ms | > 20,000 notes/sec |
| Medium (10-100 KB) | 1,000-10,000 | 100-500ms | > 15,000 notes/sec |
| Large (> 100 KB) | > 10,000 | 500ms-2s | > 10,000 notes/sec |

*Benchmarks vary by system and optimization strategy*

---

## License

**MIT License** - Free for personal, educational, and commercial use.

Built using Sound Behaviour Intelligence from forensic analysis of KORG PA800 factory patterns.

---

## Version History

### v2.0 (Current)
- ✅ Added NATURAL and PRECISE strategies
- ✅ Enhanced statistics and reporting
- ✅ Improved MIDI parser with error recovery
- ✅ Added progress callbacks
- ✅ Better track preservation
- ✅ Extended format support
- ✅ JSON output option
- ✅ Comprehensive logging

### v1.0 (Original)
- Initial release
- 4 optimization strategies
- Basic CLI and GUI
- Batch processing

---

## Support & Documentation

- **Quick Start**: This README
- **Full Guide**: See `MIDI_OPTIMIZER_GUIDE.md`
- **Technical Details**: See `FORENSIC_ANALYSIS_REPORT.md`
- **Testing**: See `TEST_GUIDE.md`

---

**🎹 Ready to transform your MIDI? Start with:**

```bash
python midi_optimizer_cli.py info
```

*KORG PA800 MIDI Optimizer v2.0 - Professional MIDI Enhancement*

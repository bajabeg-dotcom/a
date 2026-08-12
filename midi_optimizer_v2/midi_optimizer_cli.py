#!/usr/bin/env python3
"""
KORG PA800 MIDI Optimizer v2.0 - Command Line Interface

Enhanced CLI with advanced features:
- Multiple optimization strategies
- Detailed analysis reports
- Batch processing with progress
- JSON output support
- Verbose logging

Usage:
    python midi_optimizer_cli.py optimize input.mid output.mid [--strategy AUTHENTIC]
    python midi_optimizer_cli.py analyze input.mid [--json]
    python midi_optimizer_cli.py batch /path/to/files/ /path/to/output/ [--strategy NATURAL]
    python midi_optimizer_cli.py info
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

# Import from core module
try:
    from midi_optimizer_core import (
        MIDIOptimizerApp,
        OptimizationStrategy,
        MIDIParser
    )
except ImportError:
    print("❌ Error: Could not import midi_optimizer_core")
    print("   Ensure midi_optimizer_core.py is in the same directory or PYTHONPATH")
    sys.exit(1)


class MIDIOptimizerCLI:
    """Enhanced command-line interface for MIDI Optimizer v2.0"""

    def __init__(self, db_path: Optional[Path] = None, verbose: bool = False):
        self.verbose = verbose
        
        # Default database paths to check
        default_paths = [
            Path("ai_database.json"),
            Path("/mnt/user-data/outputs/ai_database.json"),
            Path.home() / "ai_database.json",
            Path.cwd() / "ai_database.json"
        ]
        
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = None
            for path in default_paths:
                if path.exists():
                    self.db_path = path
                    break
        
        if not self.db_path or not self.db_path.exists():
            print(f"❌ Sound Behaviour Database not found")
            print(f"   Searched:")
            for path in default_paths:
                print(f"     - {path}")
            print(f"\n   Please specify database path with --database option")
            sys.exit(1)
        
        if self.verbose:
            print(f"✅ Using database: {self.db_path}")
        
        try:
            self.app = MIDIOptimizerApp(self.db_path)
        except Exception as e:
            print(f"❌ Error loading application: {e}")
            sys.exit(1)

    def optimize(self, input_file: str, output_file: str, strategy: str = "AUTHENTIC",
                generate_report: bool = False, json_output: bool = False) -> bool:
        """Optimize single MIDI file with enhanced options"""

        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            print(f"❌ Input file not found: {input_path}")
            return False

        # Validate strategy
        try:
            strat = OptimizationStrategy[strategy.upper()]
        except KeyError:
            print(f"❌ Invalid strategy: {strategy}")
            print(f"   Available strategies:")
            for s in OptimizationStrategy:
                print(f"     - {s.name}: {s.description}")
            return False

        if self.verbose:
            print(f"\n🎵 Optimizing: {input_path.name}")
            print(f"   Strategy: {strat.name} - {strat.description}")
            print(f"   Output: {output_path}")

        try:
            result = self.app.optimize_file(input_path, output_path, strat, generate_report)

            if json_output:
                print(json.dumps(result, indent=2))
                return True

            if result.get("success"):
                stats = result.get("statistics", {})
                
                print(f"\n{'='*70}")
                print(f"✅ OPTIMIZATION SUCCESSFUL")
                print(f"{'='*70}")
                print(f"   Input:    {result['input_file']}")
                print(f"   Output:   {result['output_file']}")
                print(f"   Strategy: {result['strategy']}")
                print(f"\n📊 STATISTICS:")
                print(f"   Total notes:     {stats.get('total_notes', 0):,}")
                print(f"   Adjusted:        {stats.get('adjusted_notes', 0):,} ({stats.get('adjusted_notes', 0)*100/max(stats.get('total_notes', 1), 1):.1f}%)")
                print(f"   Unchanged:       {stats.get('unchanged_notes', 0):,}")
                print(f"   Avg adjustment:  {stats.get('average_adjustment', 0):+.2f}")
                print(f"   Max adjustment:  {stats.get('max_adjustment', 0)}")
                print(f"   Min adjustment:  {stats.get('min_adjustment', 0)}")
                print(f"\n⏱️  PERFORMANCE:")
                print(f"   Processing time: {stats.get('processing_time_ms', 0):.2f}ms")
                print(f"   Throughput:      {stats.get('notes_per_second', 0):,.0f} notes/sec")
                
                if generate_report and result.get("report"):
                    print(f"\n📄 REPORT:")
                    print(result["report"])
                
                return True
            else:
                print(f"❌ Optimization failed: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False

    def analyze(self, input_file: str, json_output: bool = False) -> bool:
        """Analyze MIDI file with detailed output"""

        input_path = Path(input_file)

        if not input_path.exists():
            print(f"❌ Input file not found: {input_path}")
            return False

        if self.verbose:
            print(f"\n📊 Analyzing: {input_path.name}")

        try:
            result = self.app.analyze_file(input_path)

            if json_output:
                print(json.dumps(result, indent=2, default=str))
                return True

            if "error" in result:
                print(f"❌ {result['error']}")
                return False

            file_info = result.get("file_info", {})
            
            print(f"\n{'='*70}")
            print(f"📊 MIDI ANALYSIS RESULTS")
            print(f"{'='*70}")
            print(f"File: {input_path.name}")
            print(f"Size: {file_info.get('size_bytes', 0):,} bytes")
            print(f"Format: MIDI {file_info.get('format', 0)}")
            print(f"PPQ: {file_info.get('ppq', 480)}")
            print(f"Tempo: {file_info.get('tempo_bpm', 120):.1f} BPM")
            if file_info.get("parse_errors"):
                print(f"Warnings: {len(file_info['parse_errors'])} issues detected")
            
            print(f"\n🎵 CONTENTS:")
            print(f"   Total notes: {result.get('total_notes', 0):,}")
            print(f"   Programs:    {len(result.get('programs', {}))}")
            
            print(f"\n🎼 PROGRAM DETAILS:")
            print(f"   {'Program':<8} {'Name':<30} {'Notes':>8} {'Velocity':>15}")
            print(f"   {'-'*65}")
            
            programs = result.get("programs", {})
            velocity_stats = result.get("velocity_stats", {})
            
            for prog in sorted(programs.keys(), key=int):
                count = programs[prog]
                vel = velocity_stats.get(str(prog), {})
                vel_min = int(vel.get("min", 0))
                vel_max = int(vel.get("max", 0))
                vel_avg = vel.get("avg", 0)
                
                # Get program name from GM list
                prog_name = MIDIParser.GM_PROGRAM_NAMES.get(int(prog), f"Program {prog}")
                
                print(f"   {prog:<8} {prog_name:<30} {count:>8} {vel_min:>3}-{vel_max:<3} (avg: {vel_avg:.0f})")
            
            registers = result.get("registers", {})
            if registers:
                print(f"\n🎹 REGISTER DISTRIBUTION:")
                total = sum(registers.values())
                for reg, count in sorted(registers.items()):
                    pct = count * 100 / max(total, 1)
                    bar = "█" * int(pct / 5)
                    print(f"   {reg:<15}: {count:>6} ({pct:5.1f}%) {bar}")
            
            tracks = result.get("tracks", [])
            if tracks and self.verbose:
                print(f"\n🎼 TRACK INFORMATION:")
                for track in tracks:
                    print(f"   Track {track['track_index']+1}: {track['name']}")
                    print(f"      Program: {track['program_name']}")
                    print(f"      Notes: {track['note_count']}, Velocity: {track['velocity_min']}-{track['velocity_max']}")
            
            return True

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False

    def batch(self, input_dir: str, output_dir: str, strategy: str = "AUTHENTIC",
             pattern: str = "*.mid") -> bool:
        """Batch process directory of MIDI files with progress"""

        input_path = Path(input_dir)
        output_path = Path(output_dir)

        if not input_path.is_dir():
            print(f"❌ Input directory not found: {input_path}")
            return False

        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
            if self.verbose:
                print(f"   Created output directory: {output_path}")

        try:
            strat = OptimizationStrategy[strategy.upper()]
        except KeyError:
            print(f"❌ Invalid strategy: {strategy}")
            return False

        # Find all MIDI files
        midi_files = list(input_path.glob(pattern))
        midi_files.extend(list(input_path.glob(pattern.upper())))
        midi_files = list(set(midi_files))

        if not midi_files:
            print(f"❌ No MIDI files found matching '{pattern}' in {input_path}")
            return False

        print(f"\n{'='*70}")
        print(f"📦 BATCH PROCESSING")
        print(f"{'='*70}")
        print(f"   Input:    {input_path}")
        print(f"   Output:   {output_path}")
        print(f"   Strategy: {strat.name}")
        print(f"   Pattern:  {pattern}")
        print(f"   Files:    {len(midi_files)}")
        print(f"{'='*70}")

        successful = 0
        failed = 0
        total_notes = 0
        total_adjusted = 0

        for i, midi_file in enumerate(sorted(midi_files), 1):
            output_file = output_path / f"{midi_file.stem}_optimized.mid"

            # Progress indicator
            progress = f"[{i}/{len(midi_files)}]"
            print(f"\n{progress} Processing: {midi_file.name}", end=" ")

            try:
                result = self.app.optimize_file(midi_file, output_file, strat)

                if result.get("success"):
                    stats = result.get("statistics", {})
                    notes = stats.get("total_notes", 0)
                    adjusted = stats.get("adjusted_notes", 0)
                    total_notes += notes
                    total_adjusted += adjusted
                    
                    pct = adjusted * 100 / max(notes, 1)
                    print(f"→ {adjusted:,}/{notes:,} notes ({pct:.1f}%) ✅")
                    successful += 1
                else:
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                    failed += 1

            except Exception as e:
                print(f"❌ Error: {str(e)}")
                failed += 1

        # Summary
        print(f"\n{'='*70}")
        print(f"📊 BATCH SUMMARY")
        print(f"{'='*70}")
        print(f"   Total files:     {len(midi_files)}")
        print(f"   Successful:      {successful} ✅")
        print(f"   Failed:          {failed} ❌")
        print(f"   Success rate:    {successful*100/max(len(midi_files), 1):.1f}%")
        print(f"\n   Total notes:     {total_notes:,}")
        print(f"   Total adjusted:  {total_adjusted:,} ({total_adjusted*100/max(total_notes, 1):.1f}%)")
        print(f"\n   Output saved to: {output_path}")
        print(f"{'='*70}")

        return failed == 0

    def show_info(self):
        """Display application information"""
        print(f"\n{'='*70}")
        print(f"🎹 KORG PA800 MIDI OPTIMIZER v2.0")
        print(f"{'='*70}")
        print(f"\n📖 DESCRIPTION:")
        print(f"   Professional MIDI optimization using factory sound behavior patterns")
        print(f"   extracted from forensic analysis of KORG PA800 factory styles.")
        
        print(f"\n🎯 OPTIMIZATION STRATEGIES:")
        for strategy in OptimizationStrategy:
            print(f"   {strategy.name:<12} - {strategy.description}")
            print(f"                  Intensity: {strategy.intensity*100:.0f}%")
        
        print(f"\n📁 DATABASE:")
        print(f"   Path: {self.db_path}")
        db = self.app.behaviour_db
        print(f"   Version: {db.get('version', 'unknown')}")
        print(f"   Sounds:  {len(db.get('sound_rules', {}))} programs")
        print(f"   Engine:  {db.get('engine', 'unknown')}")
        
        print(f"\n💡 USAGE EXAMPLES:")
        print(f"   Optimize single file:")
        print(f"     python midi_optimizer_cli.py optimize song.mid song_opt.mid")
        print(f"     python midi_optimizer_cli.py optimize song.mid song_opt.mid --strategy EXPRESSIVE")
        print(f"\n   Analyze MIDI file:")
        print(f"     python midi_optimizer_cli.py analyze song.mid")
        print(f"     python midi_optimizer_cli.py analyze song.mid --json")
        print(f"\n   Batch process directory:")
        print(f"     python midi_optimizer_cli.py batch ./midi_files ./output")
        print(f"     python midi_optimizer_cli.py batch ./midi ./out --strategy NATURAL --pattern '*.MID'")
        
        print(f"\n{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="KORG PA800 MIDI Optimizer v2.0 - Professional MIDI enhancement tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s optimize song.mid output.mid
  %(prog)s optimize song.mid output.mid --strategy EXPRESSIVE
  %(prog)s analyze song.mid --json
  %(prog)s batch ./input ./output --strategy NATURAL
  %(prog)s info
        """
    )

    parser.add_argument("--version", action="version", version="%(prog)s 2.0")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--database", "-d", type=Path, help="Path to AI database JSON file")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Optimize single MIDI file")
    optimize_parser.add_argument("input", help="Input MIDI file")
    optimize_parser.add_argument("output", help="Output MIDI file")
    optimize_parser.add_argument("--strategy", "-s", default="AUTHENTIC",
                               choices=[s.name for s in OptimizationStrategy],
                               help="Optimization strategy (default: AUTHENTIC)")
    optimize_parser.add_argument("--report", "-r", action="store_true",
                               help="Generate detailed optimization report")
    optimize_parser.add_argument("--json", "-j", action="store_true",
                               help="Output results as JSON")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze MIDI file structure")
    analyze_parser.add_argument("input", help="Input MIDI file")
    analyze_parser.add_argument("--json", "-j", action="store_true",
                              help="Output results as JSON")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch process MIDI files")
    batch_parser.add_argument("input_dir", help="Input directory")
    batch_parser.add_argument("output_dir", help="Output directory")
    batch_parser.add_argument("--strategy", "-s", default="AUTHENTIC",
                            choices=[s.name for s in OptimizationStrategy],
                            help="Optimization strategy (default: AUTHENTIC)")
    batch_parser.add_argument("--pattern", "-p", default="*.mid",
                            help="File pattern to match (default: *.mid)")

    # Info command
    info_parser = subparsers.add_parser("info", help="Show application information")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Create CLI instance
    cli = MIDIOptimizerCLI(db_path=args.database, verbose=args.verbose)

    # Execute command
    if args.command == "optimize":
        success = cli.optimize(
            args.input, 
            args.output, 
            args.strategy,
            generate_report=args.report,
            json_output=args.json
        )
        sys.exit(0 if success else 1)

    elif args.command == "analyze":
        success = cli.analyze(args.input, json_output=args.json)
        sys.exit(0 if success else 1)

    elif args.command == "batch":
        success = cli.batch(args.input_dir, args.output_dir, args.strategy, args.pattern)
        sys.exit(0 if success else 1)

    elif args.command == "info":
        cli.show_info()
        sys.exit(0)


if __name__ == "__main__":
    main()

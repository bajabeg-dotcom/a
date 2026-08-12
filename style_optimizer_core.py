#!/usr/bin/env python3
"""
KORG PA800 Style Optimizer

Optimize MIDI Style-pattern files using velocity behaviour profiles keyed by
Style track role (Drum, Percussion, Bass, Chord1, Chord2, Pad, Phrase1,
Phrase2) instead of by GM instrument program, the way midi_optimizer_core
optimizes by program.

Style track -> MIDI channel follows the conventional KORG/Yamaha Style
assignment order (channels 1-8, one part per channel):

    Channel 1: Drum        Channel 5: Chord2
    Channel 2: Percussion  Channel 6: Pad
    Channel 3: Bass        Channel 7: Phrase1
    Channel 4: Chord1      Channel 8: Phrase2

Channels 9-16 are treated as OTHER (free/original data tracks).

Features:
- Analyze Style MIDI structure by track role
- Apply velocity optimization per Style part
- Batch processing
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
from enum import Enum

from midi_optimizer_core import (
    MIDINote,
    MIDIParser,
    OptimizationResult,
    OptimizationStrategy,
)


class StylePart(Enum):
    """Canonical KORG Style track roles"""
    DRUM = "DRUM"
    PERCUSSION = "PERCUSSION"
    BASS = "BASS"
    CHORD1 = "CHORD1"
    CHORD2 = "CHORD2"
    PAD = "PAD"
    PHRASE1 = "PHRASE1"
    PHRASE2 = "PHRASE2"
    OTHER = "OTHER"


# MIDI channel (0-indexed) -> Style part, per the conventional 8-channel
# Style track assignment described in the module docstring.
CHANNEL_TO_STYLE_PART: Dict[int, StylePart] = {
    0: StylePart.DRUM,
    1: StylePart.PERCUSSION,
    2: StylePart.BASS,
    3: StylePart.CHORD1,
    4: StylePart.CHORD2,
    5: StylePart.PAD,
    6: StylePart.PHRASE1,
    7: StylePart.PHRASE2,
}


def style_part_for_channel(channel: int) -> StylePart:
    """Map a MIDI channel (0-15) to its conventional Style part"""
    return CHANNEL_TO_STYLE_PART.get(channel, StylePart.OTHER)


class StylePartBehaviourOptimizer:
    """Optimize MIDI notes using per-Style-part velocity behaviour profiles"""

    def __init__(self, behaviour_db: Dict):
        self.behaviour_db = behaviour_db

    def get_part_behaviour(self, part: StylePart) -> Dict:
        """Get behaviour profile for a Style part"""
        return self.behaviour_db.get("style_rules", {}).get(part.value)

    def optimize_velocity(self, note: MIDINote, strategy: OptimizationStrategy) -> OptimizationResult:
        """Optimize a single note's velocity based on its Style part"""

        part = style_part_for_channel(note.channel)
        behaviour = self.get_part_behaviour(part)

        if not behaviour:
            return OptimizationResult(
                original_velocity=note.velocity,
                optimized_velocity=note.velocity,
                reason=f"No behaviour profile for {part.value}",
                confidence="UNKNOWN",
            )

        zones = behaviour.get("velocity_zones", [])

        if not zones:
            return OptimizationResult(
                original_velocity=note.velocity,
                optimized_velocity=note.velocity,
                reason="No velocity zones defined",
                confidence="UNKNOWN",
            )

        if strategy == OptimizationStrategy.AUTHENTIC:
            optimized = self._optimize_authentic(note, zones)
        elif strategy == OptimizationStrategy.EXPRESSIVE:
            optimized = self._optimize_expressive(note, zones)
        elif strategy == OptimizationStrategy.BALANCED:
            optimized = self._optimize_balanced(note, zones)
        elif strategy == OptimizationStrategy.AGGRESSIVE:
            optimized = self._optimize_aggressive(note, zones)
        else:
            optimized = note.velocity

        return OptimizationResult(
            original_velocity=note.velocity,
            optimized_velocity=optimized,
            reason=f"{strategy.value} optimization for {part.value}",
            confidence="DEFAULT",
        )

    @staticmethod
    def _zone_bounds(zone: Dict) -> Tuple[int, int]:
        vel_min, vel_max = map(int, zone.get("velocity_range", "0-0").split("-"))
        return vel_min, vel_max

    def _optimize_authentic(self, note: MIDINote, zones: List[Dict]) -> int:
        """Snap velocity to the matching (or nearest) zone centre"""

        for zone in zones:
            vel_min, vel_max = self._zone_bounds(zone)
            if vel_min <= note.velocity <= vel_max:
                return (vel_min + vel_max) // 2

        distances = []
        for zone in zones:
            vel_min, vel_max = self._zone_bounds(zone)
            center = (vel_min + vel_max) // 2
            distances.append((abs(note.velocity - center), center))

        if distances:
            return min(distances, key=lambda x: x[0])[1]

        return note.velocity

    def _optimize_expressive(self, note: MIDINote, zones: List[Dict]) -> int:
        """Emphasize dynamics: push toward the top of the matched zone"""

        zones_sorted = sorted(zones, key=lambda z: self._zone_bounds(z)[0])
        if not zones_sorted:
            return note.velocity

        if note.velocity < 45:
            target_zone = zones_sorted[0]
        elif note.velocity < 95:
            target_zone = zones_sorted[len(zones_sorted) // 2]
        else:
            target_zone = zones_sorted[-1]

        vel_min, vel_max = self._zone_bounds(target_zone)
        return int(vel_min + (vel_max - vel_min) * 0.7)

    def _optimize_balanced(self, note: MIDINote, zones: List[Dict]) -> int:
        """Only adjust when the note is far from any zone centre"""

        for zone in zones:
            vel_min, vel_max = self._zone_bounds(zone)
            center = (vel_min + vel_max) // 2
            if abs(note.velocity - center) > 15:
                return center

        return note.velocity

    def _optimize_aggressive(self, note: MIDINote, zones: List[Dict]) -> int:
        """Maximize character: push to zone extremes"""

        zones_sorted = sorted(zones, key=lambda z: self._zone_bounds(z)[0])
        if not zones_sorted:
            return note.velocity

        if note.velocity < 50:
            vel_min, _ = self._zone_bounds(zones_sorted[0])
            return vel_min
        elif note.velocity < 90:
            vel_min, vel_max = self._zone_bounds(zones_sorted[len(zones_sorted) // 2])
            return int(vel_min + (vel_max - vel_min) * 0.5)
        else:
            _, vel_max = self._zone_bounds(zones_sorted[-1])
            return vel_max

    def optimize_midi(self, notes: List[MIDINote],
                       strategy: OptimizationStrategy = OptimizationStrategy.AUTHENTIC
                       ) -> Tuple[List[MIDINote], List[OptimizationResult]]:
        """Optimize all notes in a Style MIDI file"""

        optimized_notes = []
        results = []

        for note in notes:
            result = self.optimize_velocity(note, strategy)

            optimized_notes.append(MIDINote(
                note=note.note,
                velocity=result.optimized_velocity,
                channel=note.channel,
                program=note.program,
                start_time=note.start_time,
                duration=note.duration,
            ))
            results.append(result)

        return optimized_notes, results


class StyleOptimizerApp:
    """Main Style Optimizer Application"""

    def __init__(self, behaviour_db_path: Path):
        self.behaviour_db_path = behaviour_db_path
        self.behaviour_db = self._load_behaviour_db()
        self.optimizer = StylePartBehaviourOptimizer(self.behaviour_db)

    def _load_behaviour_db(self) -> Dict:
        """Load the Style Behaviour Database"""
        try:
            with open(self.behaviour_db_path) as f:
                return json.load(f)
        except Exception:
            print(f"⚠️  Could not load style behaviour database from {self.behaviour_db_path}")
            return {"style_rules": {}}

    def optimize_file(self, input_path: Path, output_path: Path,
                       strategy: OptimizationStrategy = OptimizationStrategy.AUTHENTIC) -> Dict:
        """Optimize a Style MIDI file"""

        print(f"\n\U0001f3b9 Optimizing Style: {input_path.name}")
        print(f"   Strategy: {strategy.value}")

        notes, _ = MIDIParser.parse_midi_file(input_path)

        if not notes:
            print("   ❌ No notes found in MIDI file")
            return {"success": False, "error": "No notes found"}

        print(f"   • Found {len(notes)} notes")

        optimized_notes, results = self.optimizer.optimize_midi(notes, strategy)

        MIDIParser.write_midi_file(optimized_notes, output_path)

        total_adjustments = len([r for r in results if r.adjustment != 0])
        avg_adjustment = sum(r.adjustment for r in results) / len(results) if results else 0

        print(f"   ✅ Optimization complete!")
        print(f"      Total notes: {len(notes)}")
        print(f"      Adjusted: {total_adjustments} ({total_adjustments * 100 / len(notes):.1f}%)")

        return {
            "success": True,
            "input_file": str(input_path),
            "output_file": str(output_path),
            "total_notes": len(notes),
            "adjusted_notes": total_adjustments,
            "average_adjustment": avg_adjustment,
            "strategy": strategy.value,
        }

    def analyze_file(self, input_path: Path) -> Dict:
        """Analyze a Style MIDI file, grouped by Style part rather than program"""

        print(f"\n\U0001f4ca Analyzing Style: {input_path.name}")

        notes, _ = MIDIParser.parse_midi_file(input_path)

        if not notes:
            return {"error": "No notes found"}

        parts = defaultdict(int)
        velocity_stats = defaultdict(lambda: {"min": 127, "max": 0, "sum": 0, "count": 0})

        for note in notes:
            part = style_part_for_channel(note.channel).value
            parts[part] += 1
            stats = velocity_stats[part]
            stats["min"] = min(stats["min"], note.velocity)
            stats["max"] = max(stats["max"], note.velocity)
            stats["sum"] += note.velocity
            stats["count"] += 1

        print(f"   Total notes: {len(notes)}")
        print(f"   Style parts used: {len(parts)}")

        return {
            "total_notes": len(notes),
            "parts": dict(parts),
            "velocity_stats": {
                part: {
                    "min": stats["min"],
                    "max": stats["max"],
                    "avg": stats["sum"] / stats["count"] if stats["count"] > 0 else 0,
                }
                for part, stats in velocity_stats.items()
            },
        }

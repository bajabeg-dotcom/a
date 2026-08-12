#!/usr/bin/env python3
"""
KORG PA800 STYLE OPTIMIZER
Desktop GUI Application

Features:
- Browse/select Style MIDI files
- Analyze notes by Style part (Drum, Bass, Chord1/2, Pad, Phrase1/2, ...)
- Multiple optimization strategies
- Batch processing
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
from datetime import datetime

from midi_optimizer_core import OptimizationStrategy
from style_optimizer_core import StyleOptimizerApp


class StyleOptimizerGUI:
    """Desktop GUI for the Style Optimizer"""

    def __init__(self, root):
        self.root = root
        self.root.title("KORG PA800 Style Optimizer")
        self.root.geometry("900x750")
        self.root.resizable(True, True)

        self.db_path = None
        self.app = None

        default_paths = [
            Path("style_behaviour_database.json"),
            Path.home() / "style_behaviour_database.json",
            Path.cwd() / "style_behaviour_database.json",
        ]

        for path in default_paths:
            if path.exists():
                self.db_path = path
                break

        self.current_file = None
        self.analysis_data = None

        self._create_ui()
        self._load_database()

    def _create_ui(self):
        """Create user interface"""

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        title = ttk.Label(main_frame, text="\U0001f3b9 KORG PA800 Style Optimizer",
                           font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, pady=10)

        db_frame = ttk.LabelFrame(main_frame, text="Style Behaviour Database", padding="10")
        db_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=10)

        self.db_status_var = tk.StringVar(value="⏳ Loading database...")
        self.db_label = ttk.Label(db_frame, textvariable=self.db_status_var, foreground="gray")
        self.db_label.grid(row=0, column=0, sticky="w", padx=5)

        browse_db_btn = ttk.Button(db_frame, text="Browse Database",
                                    command=self.browse_database)
        browse_db_btn.grid(row=0, column=1, padx=5)

        refresh_db_btn = ttk.Button(db_frame, text="Reload",
                                     command=self._load_database)
        refresh_db_btn.grid(row=0, column=2, padx=5)

        subtitle = ttk.Label(main_frame, text="Optimize Style tracks by part role (Drum, Bass, Chord, Pad, Phrase)",
                              font=("Arial", 10))
        subtitle.grid(row=1, column=0, columnspan=3, pady=5)

        file_frame = ttk.LabelFrame(main_frame, text="Input Style MIDI File", padding="10")
        file_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)

        self.file_path_var = tk.StringVar(value="Click Browse to select a Style MIDI file")
        self.file_label = ttk.Label(file_frame, textvariable=self.file_path_var,
                                     foreground="gray", relief="solid", borderwidth=2)
        self.file_label.grid(row=0, column=0, sticky="ew", pady=10)
        file_frame.columnconfigure(0, weight=1)

        button_frame = ttk.Frame(file_frame)
        button_frame.grid(row=1, column=0, sticky="ew")

        browse_btn = ttk.Button(button_frame, text="Browse MIDI File",
                                 command=self.browse_file)
        browse_btn.pack(side="left", padx=5)

        analyze_btn = ttk.Button(button_frame, text="Analyze File",
                                  command=self.analyze_file)
        analyze_btn.pack(side="left", padx=5)

        analysis_frame = ttk.LabelFrame(main_frame, text="File Analysis", padding="10")
        analysis_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)

        self.analysis_text = tk.Text(analysis_frame, height=6, width=80,
                                      state="disabled", relief="solid", borderwidth=1)
        self.analysis_text.grid(row=0, column=0, sticky="ew")

        scrollbar = ttk.Scrollbar(analysis_frame, orient="vertical",
                                   command=self.analysis_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.analysis_text.config(yscrollcommand=scrollbar.set)

        analysis_frame.columnconfigure(0, weight=1)

        strategy_frame = ttk.LabelFrame(main_frame, text="Optimization Strategy", padding="10")
        strategy_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)

        self.strategy_var = tk.StringVar(value="AUTHENTIC")

        strategies = [
            ("\U0001f3af Authentic - Match default Style-part profile", "AUTHENTIC"),
            ("\U0001f3a8 Expressive - Emphasize dynamics", "EXPRESSIVE"),
            ("⚖️  Balanced - Conservative adjustments", "BALANCED"),
            ("\U0001f4aa Aggressive - Maximize character", "AGGRESSIVE"),
        ]

        for text, value in strategies:
            rb = ttk.Radiobutton(strategy_frame, text=text, variable=self.strategy_var,
                                  value=value)
            rb.pack(anchor="w", pady=5)

        self.description_var = tk.StringVar()
        desc_label = ttk.Label(strategy_frame, textvariable=self.description_var,
                                foreground="blue", font=("Arial", 9))
        desc_label.pack(anchor="w", pady=5)

        self.strategy_var.trace_add("write", self._update_description)

        output_frame = ttk.LabelFrame(main_frame, text="Output Options", padding="10")
        output_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=10)

        ttk.Label(output_frame, text="Output File:").pack(side="left", padx=5)

        self.output_path_var = tk.StringVar(value="")
        output_entry = ttk.Entry(output_frame, textvariable=self.output_path_var,
                                  state="readonly", width=50)
        output_entry.pack(side="left", padx=5, expand=True, fill="x")

        browse_output_btn = ttk.Button(output_frame, text="Browse",
                                        command=self.browse_output)
        browse_output_btn.pack(side="left", padx=5)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=10)

        self.progress = ttk.Progressbar(progress_frame, mode="indeterminate")
        self.progress.pack(side="left", expand=True, fill="x", padx=5)

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(side="left", padx=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=20)

        optimize_btn = ttk.Button(button_frame, text="\U0001f680 Optimize Style",
                                   command=self.optimize)
        optimize_btn.pack(side="left", padx=10, pady=5)

        batch_btn = ttk.Button(button_frame, text="\U0001f4e6 Batch Process",
                                command=self.batch_process)
        batch_btn.pack(side="left", padx=10, pady=5)

        reset_btn = ttk.Button(button_frame, text="\U0001f504 Reset",
                                command=self.reset)
        reset_btn.pack(side="left", padx=10, pady=5)

        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=10)
        main_frame.rowconfigure(8, weight=1)

        self.results_text = tk.Text(results_frame, height=8, width=80,
                                     state="disabled", relief="solid", borderwidth=1)
        self.results_text.pack(side="left", fill="both", expand=True)

        results_scroll = ttk.Scrollbar(results_frame, orient="vertical",
                                        command=self.results_text.yview)
        results_scroll.pack(side="right", fill="y")
        self.results_text.config(yscrollcommand=results_scroll.set)

    def _load_database(self):
        """Load database with status indication"""
        if not self.db_path or not self.db_path.exists():
            self.db_status_var.set("❌ Database not found")
            self.db_label.config(foreground="red")
            self.app = None
            return

        try:
            self.app = StyleOptimizerApp(self.db_path)
            self.db_status_var.set(f"✅ Loaded: {self.db_path.name}")
            self.db_label.config(foreground="green")
        except Exception as e:
            self.db_status_var.set(f"❌ Error loading database: {str(e)}")
            self.db_label.config(foreground="red")
            self.app = None

    def browse_database(self):
        """Browse and select database file"""
        filename = filedialog.askopenfilename(
            title="Select Style Behaviour Database",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(Path.home()),
        )

        if filename:
            self.db_path = Path(filename)
            self._load_database()

    def _update_description(self, *args):
        """Update strategy description"""
        descriptions = {
            "AUTHENTIC": "Snap velocities to the default profile for each Style part.",
            "EXPRESSIVE": "Enhance dynamics while preserving musicality.",
            "BALANCED": "Conservative adjustments. Safe option that preserves original intent.",
            "AGGRESSIVE": "Maximize part character. Bold adjustments for pronounced effect.",
        }
        self.description_var.set(descriptions.get(self.strategy_var.get(), ""))

    def browse_file(self):
        """Browse and select MIDI file"""
        filename = filedialog.askopenfilename(
            title="Select Style MIDI file",
            filetypes=[("MIDI files", "*.mid"), ("All files", "*.*")],
        )
        if filename:
            self.load_file(Path(filename))

    def load_file(self, filepath: Path):
        """Load a Style MIDI file"""
        if not filepath.exists():
            messagebox.showerror("Error", f"File not found: {filepath}")
            return

        self.current_file = filepath
        self.file_path_var.set(f"📁 {filepath.name}")
        self.file_label.config(foreground="black")

        output_file = filepath.parent / f"{filepath.stem}_optimized.mid"
        self.output_path_var.set(str(output_file))

        self.status_var.set(f"Loaded: {filepath.name}")

    def browse_output(self):
        """Browse and select output file"""
        filename = filedialog.asksaveasfilename(
            title="Save optimized Style MIDI as",
            filetypes=[("MIDI files", "*.mid")],
            defaultextension=".mid",
        )
        if filename:
            self.output_path_var.set(filename)

    def analyze_file(self):
        """Analyze the selected Style MIDI file"""
        if not self.app:
            messagebox.showerror("Error", "Style Behaviour Database not loaded!\n\nPlease:\n1. Click 'Browse Database'\n2. Select style_behaviour_database.json\n3. Try again")
            return

        if not self.current_file:
            messagebox.showwarning("Warning", "Please select a Style MIDI file first")
            return

        self._log_analysis("Analyzing Style file...\n")

        def _analyze():
            try:
                self.analysis_data = self.app.analyze_file(self.current_file)

                analysis_text = f"File: {self.current_file.name}\n"
                analysis_text += f"Size: {self.current_file.stat().st_size} bytes\n"
                analysis_text += f"Total Notes: {self.analysis_data.get('total_notes', 0)}\n"
                analysis_text += f"Style Parts Used: {len(self.analysis_data.get('parts', {}))}\n"
                analysis_text += f"\nStyle Part Details:\n"

                for part, count in sorted(self.analysis_data.get('parts', {}).items()):
                    vel_stats = self.analysis_data.get('velocity_stats', {}).get(part, {})
                    analysis_text += f"  {part:9s}: {count:5d} notes, "
                    analysis_text += f"Vel {vel_stats.get('min', 0):3d}-{vel_stats.get('max', 0):3d}\n"

                self._update_analysis_display(analysis_text)
                self.status_var.set("Analysis complete")

            except Exception as e:
                messagebox.showerror("Error", f"Analysis failed: {str(e)}")
                self.status_var.set("Error during analysis")

        thread = threading.Thread(target=_analyze, daemon=True)
        thread.start()

    def optimize(self):
        """Optimize the Style MIDI file"""
        if not self.app:
            messagebox.showerror("Error", "Style Behaviour Database not loaded!\n\nPlease:\n1. Click 'Browse Database'\n2. Select style_behaviour_database.json\n3. Try again")
            return

        if not self.current_file:
            messagebox.showwarning("Warning", "Please select a Style MIDI file first")
            return

        if not self.output_path_var.get():
            messagebox.showwarning("Warning", "Please specify output file")
            return

        output_file = Path(self.output_path_var.get())
        strategy = OptimizationStrategy[self.strategy_var.get()]

        self._log_result("Starting optimization...\n")
        self.progress.start()
        self.status_var.set("Optimizing...")

        def _optimize():
            try:
                result = self.app.optimize_file(self.current_file, output_file, strategy)

                if result.get("success"):
                    result_text = f"✅ Optimization successful!\n\n"
                    result_text += f"Input:  {result['input_file']}\n"
                    result_text += f"Output: {result['output_file']}\n"
                    result_text += f"Strategy: {result['strategy']}\n\n"
                    result_text += f"Total Notes: {result['total_notes']}\n"
                    result_text += f"Adjusted: {result['adjusted_notes']} "
                    result_text += f"({result['adjusted_notes']*100/result['total_notes']:.1f}%)\n"
                    result_text += f"Avg Velocity Change: {result['average_adjustment']:.1f}\n"
                    result_text += f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

                    self._log_result(result_text)
                    self.status_var.set("✅ Optimization complete!")
                else:
                    self._log_result(f"❌ {result.get('error', 'Unknown error')}\n")
                    self.status_var.set("Error during optimization")

            except Exception as e:
                messagebox.showerror("Error", f"Optimization failed: {str(e)}")
                self.status_var.set("Error")

            finally:
                self.progress.stop()

        thread = threading.Thread(target=_optimize, daemon=True)
        thread.start()

    def batch_process(self):
        """Batch process multiple Style MIDI files"""
        if not self.app:
            messagebox.showerror("Error", "Style Behaviour Database not loaded!\n\nPlease:\n1. Click 'Browse Database'\n2. Select style_behaviour_database.json\n3. Try again")
            return

        files = filedialog.askopenfilenames(
            title="Select Style MIDI files to batch process",
            filetypes=[("MIDI files", "*.mid"), ("All files", "*.*")],
        )

        if not files:
            return

        output_dir = filedialog.askdirectory(title="Select output directory")
        if not output_dir:
            return

        output_dir = Path(output_dir)
        strategy = OptimizationStrategy[self.strategy_var.get()]

        self._log_result(f"Batch processing {len(files)} files...\n\n")
        self.progress.start()

        def _batch():
            results = []
            for i, filepath in enumerate(files):
                try:
                    input_path = Path(filepath)
                    output_path = output_dir / f"{input_path.stem}_optimized.mid"

                    self.status_var.set(f"Processing {i+1}/{len(files)}: {input_path.name}")

                    result = self.app.optimize_file(input_path, output_path, strategy)
                    results.append((input_path.name, result.get("success")))

                except Exception:
                    results.append((filepath, False))

            summary = f"\n{'='*60}\n"
            summary += f"BATCH PROCESSING COMPLETE\n"
            summary += f"{'='*60}\n\n"
            summary += f"Total files: {len(results)}\n"
            summary += f"Successful: {sum(1 for _, s in results if s)}\n"
            summary += f"Failed: {sum(1 for _, s in results if not s)}\n\n"

            for filename, success in results:
                status = "✅" if success else "❌"
                summary += f"{status} {filename}\n"

            self._log_result(summary)
            self.status_var.set(f"Batch complete: {len(results)} files")
            self.progress.stop()

        thread = threading.Thread(target=_batch, daemon=True)
        thread.start()

    def reset(self):
        """Reset application"""
        self.current_file = None
        self.file_path_var.set("Click Browse to select a Style MIDI file")
        self.output_path_var.set("")
        self._update_analysis_display("")
        self._log_result("")
        self.status_var.set("Ready")

    def _update_analysis_display(self, text: str):
        self.analysis_text.config(state="normal")
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, text)
        self.analysis_text.config(state="disabled")

    def _log_analysis(self, text: str):
        self.analysis_text.config(state="normal")
        self.analysis_text.insert(tk.END, text)
        self.analysis_text.config(state="disabled")

    def _log_result(self, text: str):
        self.results_text.config(state="normal")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, text)
        self.results_text.config(state="disabled")


def main():
    root = tk.Tk()
    app = StyleOptimizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

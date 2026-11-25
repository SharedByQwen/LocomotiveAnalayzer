from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parents[1]
TRAIN_SCRIPT = ROOT / "training" / "train_model.py"
DEFAULT_DATASET = ROOT / "training" / "data" / "LocomotivDataSet.xlsx"


class TrainerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Locomotive Analyzer | Local Model Trainer")
        self.root.geometry("820x590")
        self.root.minsize(680, 460)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None

        container = ttk.Frame(root, padding=16)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="Local Model Trainer", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text="Train, evaluate and export the ONNX model on this computer.",
        ).pack(anchor="w", pady=(2, 14))

        file_row = ttk.Frame(container)
        file_row.pack(fill="x")
        self.dataset = tk.StringVar(value=str(DEFAULT_DATASET))
        ttk.Entry(file_row, textvariable=self.dataset).pack(side="left", fill="x", expand=True)
        ttk.Button(file_row, text="Choose Excel…", command=self.choose_dataset).pack(side="left", padx=(8, 0))

        self.status = tk.StringVar(value="Ready")
        ttk.Label(container, textvariable=self.status).pack(anchor="w", pady=(12, 4))
        self.progress = ttk.Progressbar(container, mode="indeterminate")
        self.progress.pack(fill="x")

        self.log = tk.Text(container, wrap="word", height=22, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=12)
        buttons = ttk.Frame(container)
        buttons.pack(fill="x")
        self.start_button = ttk.Button(buttons, text="Start training", command=self.start_training)
        self.start_button.pack(side="left")
        ttk.Button(buttons, text="Open training folder", command=self.open_training_folder).pack(side="left", padx=8)
        ttk.Button(buttons, text="Close", command=self.root.destroy).pack(side="right")

        self.root.after(100, self.poll_events)
        self.append_log("Dataset expected columns and training parameters are documented in training/README.md.\n")

    def choose_dataset(self) -> None:
        path = filedialog.askopenfilename(
            title="Select locomotive dataset",
            filetypes=[("Excel workbook", "*.xlsx *.xls"), ("All files", "*.*")],
            initialdir=str(ROOT / "training" / "data"),
        )
        if path:
            self.dataset.set(path)

    def append_log(self, value: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", value)
        self.log.see("end")
        self.log.configure(state="disabled")

    def start_training(self) -> None:
        dataset = Path(self.dataset.get()).expanduser()
        if not dataset.is_file():
            messagebox.showerror("Dataset not found", f"Select an existing Excel file:\n{dataset}")
            return
        if self.process and self.process.poll() is None:
            return

        self.start_button.configure(state="disabled")
        self.status.set("Training in progress…")
        self.progress.start(10)
        self.append_log(f"\n{'=' * 72}\nStarting: {dataset}\n")
        threading.Thread(target=self.run_process, args=(dataset,), daemon=True).start()

    def run_process(self, dataset: Path) -> None:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        try:
            self.process = subprocess.Popen(
                [sys.executable, str(TRAIN_SCRIPT), "--dataset", str(dataset)],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.events.put(("log", line))
            code = self.process.wait()
            self.events.put(("done", str(code)))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def poll_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.append_log(value)
                elif kind == "done":
                    self.progress.stop()
                    self.start_button.configure(state="normal")
                    if value == "0":
                        self.status.set("Training completed successfully")
                        self.append_log("\nSUCCESS: ONNX model, ZIP bundle and README report were updated.\n")
                        messagebox.showinfo("Training complete", "Model export and README update completed.")
                    else:
                        self.status.set(f"Training failed (exit code {value})")
                        self.append_log(f"\nFAILED: process exited with code {value}\n")
                        messagebox.showerror("Training failed", f"Exit code: {value}\nSee the log above.")
                elif kind == "error":
                    self.progress.stop()
                    self.start_button.configure(state="normal")
                    self.status.set("Could not start training")
                    self.append_log(f"\nERROR: {value}\n")
                    messagebox.showerror("Training error", value)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_events)

    def open_training_folder(self) -> None:
        os.startfile(str(ROOT / "training"))


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista" if sys.platform == "win32" else "clam")
    except tk.TclError:
        pass
    TrainerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

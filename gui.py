"""Desktop GUI for background-noise reduction (DeepFilterNet).

Drag audio files onto the window (or use the Browse button), then click
"Reduce noise". Cleaned files are written next to the originals as
``<name>_clean.wav``. Designed to be packaged into a Windows .exe with
PyInstaller.
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

# Drag-and-drop is provided by the optional `tkinterdnd2` package. We fall back
# to a plain window (Browse button only) if it is unavailable.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _DND = True
except Exception:  # pragma: no cover - optional dependency
    _DND = False

from main import load_model, suppress_noise

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac", ".wma"}


class NoiseApp:
    def __init__(self, root):
        self.root = root
        root.title("Noise Reducer")
        root.geometry("560x460")
        root.minsize(480, 400)

        self.files: list[str] = []
        self.model_state = None
        self.events: queue.Queue = queue.Queue()

        pad = {"padx": 12, "pady": 6}

        header = ttk.Label(
            root,
            text="Drag audio files here, or use Browse",
            font=("", 13, "bold"),
        )
        header.pack(**pad)

        # File list inside a labeled, drop-enabled frame.
        list_frame = ttk.LabelFrame(root, text="Files")
        list_frame.pack(fill="both", expand=True, padx=12, pady=4)

        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scroll.pack(side="right", fill="y", pady=6)
        self.listbox.config(yscrollcommand=scroll.set)

        if _DND:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self._on_drop)

        # Buttons row.
        btns = ttk.Frame(root)
        btns.pack(fill="x", padx=12, pady=4)
        ttk.Button(btns, text="Browse…", command=self._browse).pack(side="left")
        ttk.Button(btns, text="Remove selected", command=self._remove_selected).pack(
            side="left", padx=6
        )
        ttk.Button(btns, text="Clear", command=self._clear).pack(side="left")

        # Attenuation control.
        opts = ttk.Frame(root)
        opts.pack(fill="x", padx=12, pady=4)
        ttk.Label(opts, text="Noise attenuation:").pack(side="left")
        self.atten = tk.StringVar(value="Full")
        ttk.Combobox(
            opts,
            textvariable=self.atten,
            values=["Full", "30 dB", "20 dB", "12 dB"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=6)

        # Run button + progress + status.
        self.run_btn = ttk.Button(root, text="Reduce noise", command=self._run)
        self.run_btn.pack(pady=8)

        self.progress = ttk.Progressbar(root, mode="determinate")
        self.progress.pack(fill="x", padx=12)

        self.status = ttk.Label(root, text="Ready.", anchor="w")
        self.status.pack(fill="x", padx=12, pady=(4, 10))

        self.root.after(100, self._poll_events)

    # ---- file management -------------------------------------------------
    def _add_files(self, paths):
        added = 0
        for p in paths:
            p = os.path.abspath(p)
            if os.path.isfile(p) and os.path.splitext(p)[1].lower() in AUDIO_EXTS:
                if p not in self.files:
                    self.files.append(p)
                    self.listbox.insert(tk.END, p)
                    added += 1
        if added:
            self._set_status(f"{len(self.files)} file(s) queued.")

    def _on_drop(self, event):
        # tkinterdnd2 returns a brace-wrapped, space-separated list for paths
        # that may contain spaces. splitlist handles the quoting correctly.
        self._add_files(self.root.tk.splitlist(event.data))

    def _browse(self):
        paths = filedialog.askopenfilenames(
            title="Select audio files",
            filetypes=[("Audio", " ".join(f"*{e}" for e in sorted(AUDIO_EXTS))), ("All", "*.*")],
        )
        self._add_files(paths)

    def _remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)
            del self.files[i]

    def _clear(self):
        self.listbox.delete(0, tk.END)
        self.files.clear()
        self._set_status("Ready.")

    # ---- processing ------------------------------------------------------
    def _atten_db(self):
        v = self.atten.get()
        return None if v == "Full" else float(v.split()[0])

    def _run(self):
        if not self.files:
            self._set_status("Add some audio files first.")
            return
        self.run_btn.config(state="disabled")
        self.progress.config(maximum=len(self.files), value=0)
        atten = self._atten_db()
        files = list(self.files)
        threading.Thread(target=self._worker, args=(files, atten), daemon=True).start()

    def _worker(self, files, atten_lim_db):
        """Runs off the UI thread. Communicates back via the event queue."""
        try:
            if self.model_state is None:
                self.events.put(("status", "Loading model (first run downloads it)…"))
                self.model_state = load_model()
        except Exception as exc:  # pragma: no cover
            self.events.put(("error", f"Failed to load model: {exc}"))
            self.events.put(("done", None))
            return

        done = 0
        for path in files:
            base, ext = os.path.splitext(path)
            out = f"{base}_clean{ext or '.wav'}"
            self.events.put(("status", f"Processing {os.path.basename(path)}…"))
            try:
                suppress_noise(path, out, atten_lim_db=atten_lim_db, model_state=self.model_state)
                done += 1
                self.events.put(("progress", done))
            except Exception as exc:
                self.events.put(("error", f"{os.path.basename(path)}: {exc}"))
        self.events.put(("status", f"Done. Cleaned {done}/{len(files)} file(s)."))
        self.events.put(("done", None))

    def _poll_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self._set_status(payload)
                elif kind == "progress":
                    self.progress.config(value=payload)
                elif kind == "error":
                    self._set_status(payload)
                elif kind == "done":
                    self.run_btn.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _set_status(self, text):
        self.status.config(text=text)


def main():
    root = TkinterDnD.Tk() if _DND else tk.Tk()
    NoiseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

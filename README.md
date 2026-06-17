# supression

Reduce background noise from audio files using [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) (DeepFilterNet3).

## Setup

```bash
uv sync
```

> Note: `torch` and `torchaudio` are pinned to `2.0.1` / `2.0.2` for compatibility
> with DeepFilterNet 0.5.6. The DeepFilterNet3 model weights download automatically
> on first run.

## Usage

```bash
# Writes the result next to the input as <name>_clean.wav
uv run python main.py /path/to/noisy.wav

# Custom output path
uv run python main.py /path/to/noisy.wav -o /path/to/clean.wav

# Keep some of the original ambience (limit attenuation to 12 dB)
uv run python main.py /path/to/noisy.wav --atten-lim-db 12
```

Audio is resampled to 48 kHz (the model's sample rate) if needed and saved as
16-bit PCM WAV.

## Desktop app (drag-and-drop GUI)

```bash
uv run python gui.py
```

Drag audio files onto the window (or click **Browse…**), pick the attenuation
level, and click **Reduce noise**. Cleaned files are written next to the
originals as `<name>_clean.wav`. Batch processing is supported; the model loads
once and is reused across files.

## Building a Windows .exe

A GitHub Actions workflow (`.github/workflows/build-windows.yml`) builds the GUI
into a standalone Windows app with PyInstaller — no Windows machine needed on
macOS, since PyInstaller cannot cross-compile.

1. Push this repo to GitHub.
2. Open the **Actions** tab → **Build Windows app** → it runs automatically on
   push, or click **Run workflow**.
3. When it finishes, download the **NoiseReducer-windows** artifact (a zip).

Give the zip to your friend. They unzip it and run **`NoiseReducer.exe`** inside
the folder — no Python install required. The bundle is large (~1–2 GB, mostly
PyTorch) and the **first launch needs internet once** to download the
DeepFilterNet model (cached afterwards, then works offline).

To build locally on a Windows machine instead:

```bat
uv sync --dev
uv run pyinstaller noise_reducer.spec
:: result: dist\NoiseReducer\NoiseReducer.exe
```

> Note: these platforms **cannot** host this app — GitHub Pages (static only),
> Vercel/Netlify (serverless size + time limits can't fit PyTorch). For a hosted
> web version, use Hugging Face Spaces or Streamlit Community Cloud instead.

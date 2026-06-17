# PyInstaller spec for the Noise Reducer desktop app.
# Build (on Windows):  pyinstaller noise_reducer.spec
#
# Produces a one-folder app at dist/NoiseReducer/NoiseReducer.exe. One-folder is
# used (rather than one-file) because the torch payload is large; one-folder
# starts faster and avoids antivirus false-positives from temp self-extraction.

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# Native/data-bearing packages that PyInstaller's default analysis misses:
#  - torch/torchaudio: large native libs + data
#  - libdf / deepfilterlib: the Rust DeepFilter extension
#  - soundfile: bundles libsndfile
#  - tkinterdnd2: ships the tkdnd platform binaries (needed for drag-and-drop)
for pkg in ("torch", "torchaudio", "libdf", "deepfilterlib", "soundfile", "tkinterdnd2"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# init_df() picks a model class (deepfilternet3, etc.) by name at runtime, so
# those submodules are imported dynamically and must be forced in.
hiddenimports += collect_submodules("df")

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NoiseReducer",
    console=False,  # GUI app: no console window
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="NoiseReducer",
)

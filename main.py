"""Reduce background noise from a WAV file using DeepFilterNet."""

import argparse
import os

from df.enhance import enhance, init_df
from df.io import load_audio, save_audio


def load_model():
    """Load the DeepFilterNet model and DF state once.

    Returns:
        A (model, df_state, sr) tuple. Loading is slow, so reuse this across
        files instead of calling it per file.
    """
    model, df_state, _ = init_df(log_file=None)
    return model, df_state, df_state.sr()


def suppress_noise(
    input_path: str,
    output_path: str,
    atten_lim_db: float | None = None,
    model_state=None,
) -> str:
    """Run DeepFilterNet noise suppression on `input_path` and write `output_path`.

    Args:
        input_path: Path to the noisy input audio file.
        output_path: Path where the cleaned audio is written.
        atten_lim_db: Optional attenuation limit in dB. If set, only this much
            noise is removed (e.g. 12 keeps the result sounding more natural).
        model_state: Optional preloaded (model, df_state, sr) tuple from
            `load_model()`. If None, the model is loaded on demand.

    Returns:
        The output path that was written.
    """
    # DeepFilterNet operates at 48 kHz.
    model, df_state, sr = model_state if model_state is not None else load_model()

    # Load audio, resampling to the model sample rate if needed. Shape: [C, T].
    audio, _ = load_audio(input_path, sr=sr)

    enhanced = enhance(model, df_state, audio, atten_lim_db=atten_lim_db)

    save_audio(output_path, enhanced, sr)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Reduce background noise from an audio file.")
    parser.add_argument("input", help="Path to the noisy input WAV file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output path. Defaults to '<input>_clean.wav' next to the input.",
    )
    parser.add_argument(
        "--atten-lim-db",
        type=float,
        default=None,
        help="Limit noise attenuation to this many dB (omit for full suppression).",
    )
    args = parser.parse_args()

    output = args.output
    if output is None:
        base, ext = os.path.splitext(args.input)
        output = f"{base}_clean{ext or '.wav'}"

    out = suppress_noise(args.input, output, atten_lim_db=args.atten_lim_db)
    print(f"Cleaned audio written to: {out}")


if __name__ == "__main__":
    main()

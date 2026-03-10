#!/usr/bin/env python3
"""ASR-based verification of TTS output.

Uses OpenAI gpt-4o-mini-transcribe API for transcription.
Reads OPENAI_API_KEY from .env file or environment.

Usage:
    python verify_tts.py --audio output.wav --expected-text "Hello world"
    python verify_tts.py --audio output.wav --expected-text "Hello world" --skip-asr
"""

import argparse
import os
import re
import sys
import wave
from pathlib import Path


def load_env():
    """Load .env file from project root."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def check_audio_valid(audio_path: Path) -> dict:
    """Basic audio validity checks."""
    result = {"path": str(audio_path), "exists": audio_path.exists()}

    if not audio_path.exists():
        return {**result, "valid": False, "error": "File does not exist"}

    size = audio_path.stat().st_size
    result["size_bytes"] = size

    if size < 1000:
        return {**result, "valid": False, "error": f"File too small ({size} bytes)"}

    try:
        with wave.open(str(audio_path), "rb") as wf:
            result["channels"] = wf.getnchannels()
            result["sample_rate"] = wf.getframerate()
            result["frames"] = wf.getnframes()
            result["duration_seconds"] = wf.getnframes() / wf.getframerate()

        if result["duration_seconds"] < 0.1:
            return {**result, "valid": False, "error": f"Audio too short ({result['duration_seconds']:.3f}s)"}

        import numpy as np
        import soundfile as sf
        data, _ = sf.read(str(audio_path))
        rms = float(np.sqrt(np.mean(data ** 2)))
        result["rms_energy"] = rms
        if rms < 1e-5:
            return {**result, "valid": False, "error": f"Audio is all silence (RMS={rms:.2e})"}

        result["valid"] = True
        return result

    except Exception as e:
        return {**result, "valid": False, "error": f"Invalid audio: {e}"}


def normalize(text: str) -> str:
    """Normalize text for WER computation."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def compute_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate via Levenshtein distance."""
    ref_words = normalize(reference).split()
    hyp_words = normalize(hypothesis).split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = 1 + min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1])

    return d[len(ref_words)][len(hyp_words)] / len(ref_words)


def transcribe(audio_path: str) -> str:
    """Transcribe audio using OpenAI gpt-4o-mini-transcribe."""
    from openai import OpenAI

    client = OpenAI()  # reads OPENAI_API_KEY from env

    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f,
        )

    return result.text.strip()


def main():
    load_env()

    parser = argparse.ArgumentParser(description="Verify TTS output with ASR")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--expected-text", required=True, help="Expected text content")
    parser.add_argument("--wer-threshold", type=float, default=0.3, help="Max acceptable WER")
    parser.add_argument("--skip-asr", action="store_true", help="Only check audio validity")
    args = parser.parse_args()

    audio_path = Path(args.audio)

    # Step 1: Audio validity
    print(f"[1/3] Checking audio validity: {audio_path}")
    audio_check = check_audio_valid(audio_path)

    if not audio_check["valid"]:
        print(f"FAIL: {audio_check['error']}")
        sys.exit(1)

    print(f"  Duration: {audio_check['duration_seconds']:.2f}s")
    print(f"  Sample rate: {audio_check['sample_rate']} Hz")
    print(f"  RMS energy: {audio_check['rms_energy']:.4f}")
    print(f"  Size: {audio_check['size_bytes']} bytes")

    if args.skip_asr:
        print("PASS (audio valid, ASR skipped)")
        sys.exit(0)

    # Step 2: Transcribe
    print("[2/3] Transcribing with gpt-4o-mini-transcribe...")
    transcription = transcribe(str(audio_path))
    print(f"  Transcription: {transcription}")
    print(f"  Expected:      {args.expected_text}")

    # Step 3: Compute WER
    wer = compute_wer(args.expected_text, transcription)
    print(f"[3/3] Word Error Rate: {wer:.3f} (threshold: {args.wer_threshold})")

    if wer <= args.wer_threshold:
        print(f"PASS (WER={wer:.3f})")
        sys.exit(0)
    else:
        print(f"FAIL (WER={wer:.3f} > {args.wer_threshold})")
        sys.exit(1)


if __name__ == "__main__":
    main()

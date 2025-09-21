from typing import List, Tuple
import json
from pydub import AudioSegment
from faster_whisper import WhisperModel
import torch
import os
from backend import get_levantine_whisper

# --- Load audio and prepare ---
audio = AudioSegment.from_file(audio_path)
audio = audio.set_channels(1).set_frame_rate(16000)

# --- Load Whisper model ---
model = get_levantine_whisper()

def transcribe_arabic(
    audio_path: str,
    segments: List[Dict],
    device: str = "cuda",
    compute_type: str = "float16",
    beam_size: int = 5,
) -> List[Tuple[str, str]]:
    """
    Transcribe Arabic audio with speaker diarization.

    Args:
        audio_path (str): Path to the input audio file (MP3/M4A/etc.).
        diarization_json (str): Path to the JSON file containing diarization segments.
        device (str): Device for Whisper model ("cuda" or "cpu").
        compute_type (str): Compute type for Whisper model ("float16", "int8", etc.).
        beam_size (int): Beam size for transcription.

    Returns:
        List[Tuple[str, str]]: List of tuples (speaker, transcribed text).
    """

    turns: List[Tuple[str, str]] = []
    total_segments = len(segments)

    for idx, seg in enumerate(segments, start=1):
        speaker = seg["speaker"]
        start_ms = int(seg["start"] * 1000)
        end_ms = int(seg["end"] * 1000)

        print(f"[{idx}/{total_segments}] Processing segment... "
              f"Speaker: {speaker}, Start: {seg['start']:.2f}s, End: {seg['end']:.2f}s")

        snippet = audio[start_ms:end_ms]
        snippet_path = f"segment_{idx:03d}.wav"
        snippet.export(snippet_path, format="wav")

        w_segments, _ = model.transcribe(
            snippet_path,
            language="ar",
            beam_size=beam_size,
        )

        text = " ".join(s.text.strip() for s in w_segments).strip()
        if text:
            turns.append((speaker, text))
            print(f"   ✅ Done, text length: {len(text)} chars")
        else:
            print("   ⚠️ No text detected")

        # Optional: clean up snippet file to save space
        os.remove(snippet_path)

    print(f"\n📄 Transcription completed | total turns: {len(turns)}")
    return turns

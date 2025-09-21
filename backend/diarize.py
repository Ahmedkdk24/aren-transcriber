from typing import List, Dict
import os
import torch
import json
from pydub import AudioSegment
from pyannote.audio import Pipeline
from backend import get_pyannote_pipeline


# Convert input audio → WAV
print("🔁 Converting audio to WAV...")
audio = AudioSegment.from_file(file_path)
audio.export(wav_path, format="wav")

# Load PyAnnote Pipeline
pipeline = get_pyannote_pipeline()

def diarize_audio(file_path: str, moderator_first: bool = False, speakers: int = 1) -> List[Dict]:
    """
    Perform speaker diarization on an audio file.

    Args:
        file_path (str): Path to the input audio file (MP3/M4A/etc.).
        moderator_first (bool): Whether the first speaker is the moderator. Default False.
        speakers (int): Number of speakers expected. Default 1.

    Returns:
        List[Dict]: List of diarized segments with start, end, and speaker labels.
    """
    
    # Run diarization
    print("🧠 Running diarization...")
    diarization = pipeline(wav_path, num_speakers=speakers)

    # Extract raw segments
    raw_segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        raw_segments.append({
            "start": float(turn.start),
            "end": float(turn.end),
            "speaker": speaker
        })

    # --- Resolve overlaps ---
    def resolve_overlaps(segments):
        segments = sorted(segments, key=lambda x: x["start"])
        output = []

        for seg in segments:
            if not output:
                output.append(seg)
                continue

            last = output[-1]

            # Case 1: No overlap
            if seg["start"] >= last["end"]:
                output.append(seg)

            # Case 2: seg fully inside last → split last into 3 parts
            elif seg["end"] <= last["end"]:
                if seg["start"] > last["start"]:
                    before = {"start": last["start"], "end": seg["start"], "speaker": last["speaker"]}
                    output[-1] = before
                output.append(seg)
                if seg["end"] < last["end"]:
                    after = {"start": seg["end"], "end": last["end"], "speaker": last["speaker"]}
                    output.append(after)

            # Case 3: Partial overlap
            else:
                if seg["start"] > last["start"]:
                    output[-1] = {"start": last["start"], "end": seg["start"], "speaker": last["speaker"]}
                output.append(seg)

        return output

    non_overlapping_segments = resolve_overlaps(raw_segments)

    # --- Assign Moderator (M) and Respondents (R) ---
    moderator_speaker_id = non_overlapping_segments[0]["speaker"] if non_overlapping_segments else None
    for seg in non_overlapping_segments:
        if moderator_first:
            seg["speaker"] = "M" if seg["speaker"] == moderator_speaker_id else f"R{seg['speaker']}"
        else:
            seg["speaker"] = "M" if seg["speaker"] == moderator_speaker_id else "R"

    # --- Merge short segments (< 0.6s) ---
    min_duration = 0.6
    def merge_short_segments(segments, min_duration):
        if not segments:
            return []
        merged = [segments[0]]
        for seg in segments[1:]:
            last = merged[-1]
            seg_duration = seg["end"] - seg["start"]
            if seg_duration < min_duration:
                if seg["speaker"] == last["speaker"]:
                    last["end"] = seg["end"]
                else:
                    last["end"] = seg["end"]
            else:
                merged.append(seg)
        return merged

    shortmerged_segments = merge_short_segments(non_overlapping_segments, min_duration)

    # --- Merge gaps into previous speaker ---
    gapinclusive_segments = []
    gap_threshold = 3.0
    for i, seg in enumerate(shortmerged_segments):
        if i > 0:
            prev = gapinclusive_segments[-1]
            gap = seg["start"] - prev["end"]
            if gap > min_duration and gap <= gap_threshold:
                prev["end"] = seg["start"]
        gapinclusive_segments.append(seg)

    # --- Merge adjacent same-speaker segments ---
    def merge_adjacent_segments(segments, gap_tolerance=1):
        if not segments:
            return []
        merged = [segments[0]]
        for seg in segments[1:]:
            last = merged[-1]
            if seg["speaker"] == last["speaker"] and seg["start"] - last["end"] <= gap_tolerance:
                merged[-1]["end"] = max(last["end"], seg["end"])
            else:
                merged.append(seg)
        return merged

    merged_segments = merge_adjacent_segments(gapinclusive_segments)

    print(f"✅ {len(merged_segments)} segments kept (after filtering + gap filling)")

    return merged_segments

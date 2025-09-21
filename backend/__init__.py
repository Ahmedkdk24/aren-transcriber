# __init__.py

import os
import torch
from typing import List, Dict, Tuple
import json
import re
import pickle
from dotenv import load_dotenv

# Third-party imports
from pydub import AudioSegment
from pyannote.audio import Pipeline
from faster_whisper import WhisperModel
from docx import Document
from docx.shared import RGBColor, Pt
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline as hf_pipeline,
    BitsAndBytesConfig,
)

# Expose key classes and modules
__all__ = [
    "torch",
    "AudioSegment",
    "Pipeline",
    "WhisperModel",
    "Document",
    "RGBColor",
    "Pt",
    "AutoModelForCausalLM",
    "AutoTokenizer",
    "hf_pipeline",
    "BitsAndBytesConfig",
    "os",
    "json",
    "re",
    "pickle",
    "get_pyannote_pipeline",
    "get_levantine_whisper",
    "get_large_whisper",
    "get_text_gen_pipeline",
]

load_dotenv()

# --------------------------
# Lazy initialization globals
# --------------------------
_HF_TOKEN = os.environ.get("HF_TOKEN")  # you can set your token in env vars
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_compute_type = "float16"  # adjust if needed

_pyannote_pipeline = None
_levantine_whisper = None
_large_whisper = None
_text_gen_pipeline = None

# --------------------------
# Lazy initialization funcs
# --------------------------

def get_pyannote_pipeline():
    """Return a globally loaded PyAnnote speaker diarization pipeline."""
    global _pyannote_pipeline
    if _pyannote_pipeline is None:
        _pyannote_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=_HF_TOKEN
        )
        _pyannote_pipeline.to(_device)
    return _pyannote_pipeline

def get_levantine_whisper():
    """Return the Levantine Whisper model."""
    global _levantine_whisper
    if _levantine_whisper is None:
        _levantine_whisper = WhisperModel(
            "HebArabNlpProject/WhisperLevantine",
            device=_device,
            compute_type=_compute_type
        )
    return _levantine_whisper

def get_large_whisper():
    """Return the large-v3 Whisper model."""
    global _large_whisper
    if _large_whisper is None:
        _large_whisper = WhisperModel("large-v3", device=_device)
    return _large_whisper

def get_text_gen_pipeline():
    """Return the HuggingFace text-generation pipeline with ALLaM-7B-Instruct-preview model."""
    global _text_gen_pipeline
    if _text_gen_pipeline is None:
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)
        tokenizer = AutoTokenizer.from_pretrained("ALLaM-AI/ALLaM-7B-Instruct-preview")
        model = AutoModelForCausalLM.from_pretrained(
            "ALLaM-AI/ALLaM-7B-Instruct-preview",
            device_map="auto",
            quantization_config=bnb_config
        )
        _text_gen_pipeline = hf_pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer
        )
    return _text_gen_pipeline

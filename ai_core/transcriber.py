# ai_core/transcriber.py

from faster_whisper import WhisperModel
import os

# Initialize model once (Download happens on first run)
# 'tiny' is fast and good enough for simple queries. Use 'base' for better accuracy.
model_size = "medium" 

# Run on CPU (or "cuda" if you have an NVIDIA GPU set up)
model = WhisperModel(model_size, device="cpu", compute_type="int8")

def transcribe_audio(file_path: str) -> str:
    """
    Takes a path to an audio file and returns the transcribed text.
    The 'medium' model automatically handles multilingual transcription.
    """
    try:
        segments, info = model.transcribe(file_path, beam_size=5)
        
        full_text = ""
        for segment in segments:
            full_text += segment.text + " "
            
        return full_text.strip()
    except Exception as e:
        print(f"Transcription Error: {e}")
        return ""
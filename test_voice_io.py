
























































































































































































































































































import os
import sys
from agentic_system.src.voice import VoiceInterface

def test_voice_io():
    print("Testing VoiceInterface I/O...")
    voice = VoiceInterface()
    
    # Test TTS
    text = "Hello, this is a test."
    print(f"Generating audio for: '{text}'")
    audio_path = voice.text_to_speech_file(text)
    
    if audio_path and os.path.exists(audio_path):
        print(f"PASS: Audio generated at {audio_path}")
    else:
        print("FAIL: Audio generation failed")
        sys.exit(1)
        
    # Test Transcribe (using the generated file)
    print(f"Transcribing audio from {audio_path}...")
    # Note: SpeechRecognition might fail if it can't handle the mp3 directly or if no internet for Google API
    # But we want to test the mechanism.
    # gTTS saves as mp3. SpeechRecognition prefers wav/aiff/flac.
    # We might need to convert it, or ensure VoiceInterface handles it.
    # VoiceInterface uses sr.AudioFile which supports WAV, AIFF, AIFF-C, FLAC.
    # MP3 support in sr depends on pydub/ffmpeg.
    
    # Let's check if we need conversion in VoiceInterface or if we should just test TTS here.
    # For now, let's try. If it fails on format, we know we need to add conversion to VoiceInterface.
    
    transcribed = voice.transcribe_file(audio_path)
    print(f"Transcribed: '{transcribed}'")
    
    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)

if __name__ == "__main__":
    test_voice_io()

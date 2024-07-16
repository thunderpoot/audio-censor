#!/usr/bin/env python3

import argparse
import csv
from pydub import AudioSegment
from pydub.generators import Sine
import wave
import os
from datetime import datetime
from vosk import Model, KaldiRecognizer, SetLogLevel
import json

# Reduce Vosk logging verbosity
SetLogLevel(0)

# Function to transcribe audio to text with timestamps using Vosk
def transcribe_audio_with_timestamps(audio_segment, model_path):
    temp_filename = "temp.wav"
    # Ensure correct format: 16kHz, mono, 16-bit PCM
    audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio_segment.export(temp_filename, format="wav")
    print(f"Exported audio to {temp_filename}")  # Debug statement

    # Verify the content and properties of the temp.wav file
    with wave.open(temp_filename, 'rb') as wf:
        print(f"temp.wav properties: channels={wf.getnchannels()}, sample_width={wf.getsampwidth()}, frame_rate={wf.getframerate()}, frames={wf.getnframes()}")

    model = Model(model_path)
    recognizer = KaldiRecognizer(model, 16000)
    recognizer.SetWords(True)  # Ensure recognizer is set to capture word-level timestamps

    # Read the audio file
    wf = open(temp_filename, "rb")
    wf.read(44)  # Skip the header

    results = []
    while True:
        data = wf.read(4000)
        if len(data) == 0:
            break
        print(f"Read {len(data)} bytes from WAV file, first 20 bytes: {data[:20]}")  # Debug statement
        if recognizer.AcceptWaveform(data):
            results.append(json.loads(recognizer.Result()))
        else:
            results.append(json.loads(recognizer.PartialResult()))

    results.append(json.loads(recognizer.FinalResult()))
    wf.close()
    os.remove(temp_filename)

    transcript = ""
    words = []
    for result in results:
        if "text" in result:
            transcript += result["text"] + " "
        if "result" in result:
            words.extend(result["result"])

    return transcript.strip(), words

# Function to find bad words and their timestamps in the transcribed text
def find_bad_word_timestamps(words, bad_words):
    bad_word_timestamps = []
    for word_info in words:
        word = word_info['word'].lower()
        print(f"Checking word: {word}")  # Debug statement
        if word in bad_words:
            print(f"Found bad word: {word}")  # Debug statement
            start_time = word_info['start'] * 1000  # Convert to milliseconds
            end_time = word_info['end'] * 1000  # Convert to milliseconds
            bad_word_timestamps.append((start_time, end_time))
    return bad_word_timestamps

# Function to censor bad words in the transcript
def censor_transcript(transcript, bad_words):
    words = transcript.split()
    for i, word in enumerate(words):
        if word.lower() in bad_words:
            words[i] = "\033[7m[redacted]\033[m"
    return ' '.join(words)

# Function to replace bad words with beeps
def beep_out_bad_words(audio_segment, bad_word_timestamps, beep_volume_reduction=20):
    for start_time, end_time in bad_word_timestamps:
        start_ms = int(start_time)
        end_ms = int(end_time)
        duration_ms = end_ms - start_ms
        beep = Sine(1000).to_audio_segment(duration=duration_ms).apply_gain(-beep_volume_reduction)
        print(f"Beeping from {start_ms} to {end_ms}")  # Debug statement
        audio_segment = audio_segment[:start_ms] + beep + audio_segment[end_ms:]
    return audio_segment

# Function to load bad words from CSV file
def load_bad_words(bad_words_file):
    bad_words = []
    with open(bad_words_file, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            for word in row:
                bad_words.append(word.strip().lower())
    return bad_words

# Main function to handle command line arguments and processing
def main():
    parser = argparse.ArgumentParser(description="Beep out bad words from an audio file.")
    parser.add_argument("audio_file", help="Input audio file")
    parser.add_argument("bad_words_file", help="CSV file containing bad words")
    parser.add_argument("output_format", help="Output audio format (e.g., wav, mp3, etc.)")
    parser.add_argument("model_path", help="Path to the Vosk model directory")
    parser.add_argument("--transcribe-only", action="store_true", help="Only transcribe the audio without beeping out bad words")
    args = parser.parse_args()

    audio_file = args.audio_file
    bad_words_file = args.bad_words_file
    output_format = args.output_format
    model_path = args.model_path
    transcribe_only = args.transcribe_only

    # Load the input audio file with pydub
    try:
        audio_segment = AudioSegment.from_file(audio_file)
        print(f"Loaded audio file {audio_file}, duration: {len(audio_segment)} ms")  # Debug statement
    except Exception as e:
        print(f"Error loading audio file {audio_file}: {e}")
        return

    # Load bad words from CSV file
    try:
        bad_words = load_bad_words(bad_words_file)
        print(f"Loaded bad words: {bad_words}")  # Debug statement
    except Exception as e:
        print(f"Error loading bad words from file {bad_words_file}: {e}")
        return

    # Transcribe the audio to text with timestamps
    try:
        transcript, words = transcribe_audio_with_timestamps(audio_segment, model_path)
        print("Transcript:", transcript)  # Debug statement
        print("Words with timestamps:", words)  # Debug statement
    except Exception as e:
        print(f"Error during transcription: {e}")
        return

    if transcribe_only:
        # Output the censored transcript
        censored_transcript = censor_transcript(transcript, bad_words)
        print("Censored Transcript:")
        print(censored_transcript)
        return

    # Find positions of bad words in the transcript
    try:
        bad_word_timestamps = find_bad_word_timestamps(words, bad_words)
        print(f"Bad word timestamps: {bad_word_timestamps}")  # Debug statement
    except Exception as e:
        print(f"Error finding bad words: {e}")
        return

    # Replace bad words with beeps in the audio
    try:
        cleaned_audio = beep_out_bad_words(audio_segment, bad_word_timestamps)
    except Exception as e:
        print(f"Error beeping out bad words: {e}")
        return

    # Output the censored transcript
    censored_transcript = censor_transcript(transcript, bad_words)
    print("Censored Transcript:")
    print(censored_transcript)

    # Generate output file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_file_name, _ = os.path.splitext(os.path.basename(audio_file))
    output_file = f"{input_file_name}_cleaned_{timestamp}.{output_format}"

    # Save the cleaned audio file
    try:
        cleaned_audio.export(output_file, format=output_format)
        print(f"Saved cleaned audio to {output_file}")  # Debug statement
    except Exception as e:
        print(f"Error saving cleaned audio to {output_file}: {e}")

if __name__ == "__main__":
    main()

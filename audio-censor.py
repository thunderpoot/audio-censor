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

# Function to transcribe audio to text with timestamps using Vosk
def transcribe_audio_with_timestamps(audio_segment, model_path, verbose=False):
    temp_filename = "temp.wav"
    # Ensure correct format: 16kHz, mono, 16-bit PCM
    audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    # Debug: Check the duration and frame count of the audio segment before exporting
    print(f"Audio segment before export: duration={len(audio_segment)} ms, frame_count={audio_segment.frame_count()}")

    if len(audio_segment) == 0:
        print("Error: Audio segment is empty before export.")
        return "", []

    audio_segment.export(temp_filename, format="wav")
    print(f"Exported audio to {temp_filename}")

    # Verify the content and properties of the temp.wav file
    with wave.open(temp_filename, 'rb') as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frame_rate = wf.getframerate()
        frames = wf.getnframes()
        print(f"temp.wav properties: channels={channels}, sample_width={sample_width}, frame_rate={frame_rate}, frames={frames}")

    if frames == 0:
        print("Error: Exported temp.wav file has zero frames.")
        return "", []

    model = Model(model_path)
    recognizer = KaldiRecognizer(model, 16000) # 16kHz
    recognizer.SetWords(True)  # Ensure recognizer is set to capture word-level timestamps

    # Read the audio file
    wf = open(temp_filename, "rb")
    wf.read(44)  # Skip the WAV's RIFF header which is always 44 bytes

    results = []
    while True:
        data = wf.read(4000)
        if len(data) == 0:
            break
        if verbose:
            print(f"Read {len(data)} bytes from WAV file, first 20 bytes: {data[:20]}")  # Debug
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

    print(f'Tx:{words}')
    return transcript.strip(), words

# Function to find bad words and their timestamps in the transcribed text
def find_bad_word_timestamps(words, bad_words, verbose=False):
    bad_word_timestamps = []
    for word_info in words:
        word = word_info['word'].lower()
        if verbose:
            print(f"Checking word: {word}")  # Debug
        if word in bad_words:
            if verbose:
                print(f"Found bad word: {word}")  # Debug
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
def beep_out_bad_words(audio_segment, bad_word_timestamps, beep_volume_reduction, verbose=False):
    for start_time, end_time in bad_word_timestamps:
        start_ms = int(start_time)
        end_ms = int(end_time)
        duration_ms = end_ms - start_ms
        beep = Sine(1000).to_audio_segment(duration=duration_ms).apply_gain(-beep_volume_reduction)
        if verbose:
            print(f"Beeping from {start_ms} to {end_ms}")  # Debug
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

# Function to load new transcript from text file
def load_new_transcript(transcript_file):
    with open(transcript_file, 'r') as file:
        new_transcript = file.read().strip().split()
    return new_transcript

# Function to rearrange audio segments based on new transcript
def rearrange_audio_segments(audio_segment, words, new_transcript, verbose):
    segments = []
    word_dict = {word_info['word']: word_info for word_info in words}

    if verbose:
        print("Original words with timestamps:")
        for word_info in words:
            print(f"{word_info['word']}: start={word_info['start']}, end={word_info['end']}")

    for word in new_transcript:
        lower_word = word.lower()  # Ensure comparison is case-insensitive
        if lower_word in word_dict:
            word_info = word_dict[lower_word]
            start_time = word_info['start'] * 1000  # Convert to milliseconds
            end_time = word_info['end'] * 1000  # Convert to milliseconds
            segment = audio_segment[start_time:end_time]
            segments.append(segment)
            if verbose:
                print(f"Added segment for word '{word}': start_time={start_time}, end_time={end_time}")
        else:
            print(f"Word '{word}' not found in the original transcript.")

    if not segments:
        print("No segments found. Generating silent audio segment.")
        return AudioSegment.silent(duration=len(audio_segment))

    return sum(segments)

# Main function to handle command line arguments and processing
def main(**kwargs):
    # Reduce Vosk logging verbosity by default
    SetLogLevel(-1)

    audio_file = kwargs.get('audio_file')
    bad_words_file = kwargs.get('bad_words_file')
    output_format = kwargs.get('output_format')
    nocensor = kwargs.get('nocensor', False)
    new_transcript = kwargs.get('new_transcript', False)
    transcribe_only = kwargs.get('transcribe_only')
    model_path = kwargs.get('model_path')
    transcript_json_path = kwargs.get('transcript_json_path')
    verbose = kwargs.get('verbose')

    if verbose:
        SetLogLevel(0)

    print(f"Audio file: {audio_file}")
    print(f"Model path: {model_path}")

    # Determine the output format
    input_format = os.path.splitext(audio_file)[1][1:]
    output_format = output_format if output_format else input_format

    # Load the input audio file with pydub
    try:
        audio_segment = AudioSegment.from_file(audio_file)
        print(f"Loaded audio file {audio_file}, duration: {len(audio_segment)} ms, frame_count={audio_segment.frame_count()}")  # Debug
    except Exception as e:
        print(f"Error loading audio file {audio_file}: {e}")
        return

    if len(audio_segment) == 0:
        print("Error: Loaded audio segment is empty.")
        return

    if transcribe_only:
        transcript, words = transcribe_audio_with_timestamps(audio_segment, model_path, verbose)
        print("Transcript:")
        print(transcript)
        return

    try:
        if transcript_json_path:
            jsonfile = open(transcript_json_path)
            words = json.load(jsonfile)
            jsonfile.close()
            # words = json.loads(manual_words_json)
            transcript = ' '.join(word["word"] for word in words)
        else:
            transcript, words = transcribe_audio_with_timestamps(audio_segment, model_path, verbose)
        print("Raw transcript:")
        print(transcript)
        if verbose:
            print("Words with timestamps:", words)  # Debug
    except Exception as e:
        print(f"Error during transcription: {e}")
        return

    if not bad_words_file and not ( transcribe_only or nocensor):
        print("Error: --bad_words_file is required unless --transcribe_only or nocensor are set.")
        return

    if bad_words_file:
        try:
            bad_words = load_bad_words(bad_words_file)
            print(f"Loaded bad words: {bad_words}")  # Debug
        except Exception as e:
            print(f"Error loading bad words from file {bad_words_file}: {e}")
            return
    else:
        bad_words = []

    if new_transcript:
        try:
            new_transcript = load_new_transcript(new_transcript)
            print(f"Loaded new transcript: {new_transcript}")  # Debug
            audio_segment = rearrange_audio_segments(audio_segment, words, new_transcript, verbose)
            # Retranscribe the rearranged audio to get new timestamps
            transcript, words = transcribe_audio_with_timestamps(audio_segment, model_path, verbose=False)
            print("New Transcript:", transcript)  # Debug
            if verbose:
                print("New Words with timestamps:", words)  # Debug
        except Exception as e:
            print(f"Error rearranging audio: {e}")
            return

    if nocensor:
        print("Transcript Without Censoring:")
        print(transcript)
        # Generate output file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_file_name, _ = os.path.splitext(os.path.basename(audio_file))
        output_file = f"{input_file_name}_rearranged_{timestamp}.{output_format}"
        # Save the rearranged audio file
        try:
            audio_segment.export(output_file, format=output_format)
            print(f"Saved rearranged audio to {output_file}")  # Debug
        except Exception as e:
            print(f"Error saving rearranged audio to {output_file}: {e}")
        return

    if bad_words:
        try:
            bad_word_timestamps = find_bad_word_timestamps(words, bad_words, verbose)
            if verbose:
                print(f"Bad word timestamps: {bad_word_timestamps}")  # Debug
        except Exception as e:
            print(f"Error finding bad words: {e}")
            return

        # Replace bad words with beeps in the audio
        try:
            cleaned_audio = beep_out_bad_words(audio_segment, bad_word_timestamps, 10, verbose)
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
            print(f"Saved cleaned audio to {output_file}")
        except Exception as e:
            print(f"Error saving cleaned audio to {output_file}: {e}")
    else:
        print("No bad words provided for censoring.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio Censoring Script")
    parser.add_argument('--audio_file', type=str, required=True, help='Path to the input audio file')
    parser.add_argument('--bad_words_file', type=str, help='Path to the bad words CSV file')
    parser.add_argument('--output_format', type=str, default='mp3', help='Desired output format of the audio file')
    parser.add_argument('--nocensor', action='store_true', help='Flag to output transcript without censoring')
    parser.add_argument('--model_path', type=str, required=True, help='Path to the Vosk model')
    parser.add_argument('--transcript_json_path', type=str, help='Path to JSON transcript data')
    parser.add_argument('--verbose', action='store_true', help='Increase output verbosity')
    parser.add_argument('--transcribe_only', action='store_true', help='Transcribe without generating new audio')
    parser.add_argument('--new_transcript', type=str, help='Path to .txt file with desired output words')

    args = parser.parse_args()
    kwargs = vars(args)

    main(**kwargs)

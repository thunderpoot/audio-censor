# Speech Censoring & Manipulation

Here's a [very rudimentary](https://www.google.com/search?q=define:jank) program for censoring and rearranging speech sounds in an audio file.  It supports multiple input formats and has several options.

This program processes an audio file, identifies specified words, and censors them by replacing them with beeps. Optionally, the [words may be rearranged](https://youtu.be/LzoNAsXELBk?t=1369) by supplying a text file with the desired speech output. The transcript can be returned without censoring if desired.

## Requirements

- Python 3
- [pydub](https://pypi.org/project/pydub/)
- [vosk](https://alphacephei.com/vosk/)
    - The smallest (40M) en-US model can be used (YMMV). The larger (1.8G) model might be more accurate.  Download the desired model from [here](https://alphacephei.com/vosk/models), and put it in the project directory.
- argparse
- wave
- datetime
- json

## Installation

Install the required Python libraries using `pip`:

```sh
pip install pydub vosk argparse
```

## Usage

To run the script:

```sh
python audio-censor.py --audio_file inputfile.mp3 --bad_words_file badwords.csv --model_path vosk-model-small-en-us-0.15/ --output_format aiff --verbose
```

(Or whichever model path you want.  The larger ones take longer to use, obviously)

## Examples

Here are some examples, which use this example audio from the Speech Synthesis group at [Kungliga Tekniska Högskolan](https://www.speech.kth.se/) (KTH):

<audio src="examples/mat.mp3" controls></audio>

```text
it had established periodic regular review of the status of four hundred individuals
```

### Example 1 command

We will censor the words "established", "review", "status", and "individuals".

```sh
python audio-censor.py --audio_file examples/mat.mp3 --bad_words_file examples/mat_redact.csv --model_path vosk-model-small-en-us-0.15/ --output_format aiff
```

### Example 1 output

```text
Audio file: examples/mat.mp3
Bad words file: examples/mat_redact.csv
Model path: vosk-model-small-en-us-0.15/
Loaded audio file examples/mat.mp3, duration: 5515 ms
Loaded bad words: ['established', 'review', 'status', 'individuals']
Exported audio to temp.wav
temp.wav properties: channels=1, sample_width=2, frame_rate=16000, frames=88236
Transcript: it had established periodic regular review of the status of four hundred individuals
Censored Transcript:
it had [redacted] periodic regular [redacted] of the [redacted] of four hundred [redacted]
Saved cleaned audio to mat_cleaned_20240716_162852.aiff
```

<audio src="examples/mat_cleaned_20240716_162852.aiff" controls></audio>

![Figure_1](examples/Figure_1.png)
![Figure_2](examples/Figure_2.png)

### Example 2 command

We will rearrange the words to say something else"

```text
it had established review of this periodic regular status of four hundred established individuals review status periodic it had
```

```sh
python audio-censor.py --audio_file examples/mat.mp3 --bad_words examples/mat_redact.csv --transcribe_only --model_path vosk-model-small-en-us-0.15/ --new_transcript examples/mat_new.txt --nocensor
```

### Example 2 output

```text
Audio file: examples/mat.mp3
Bad words file: examples/mat_redact.csv
Model path: vosk-model-small-en-us-0.15/
Loaded audio file examples/mat.mp3, duration: 5515 ms
Loaded bad words: ['established', 'review', 'status', 'individuals']
Exported audio to temp.wav
temp.wav properties: channels=1, sample_width=2, frame_rate=16000, frames=88236
Raw transcript:
it had established periodic regular review of the status of four hundred individuals
Loaded new transcript: ['it', 'had', 'established', 'review', 'of', 'the', 'periodic', 'regular', 'status', 'of', 'four', 'hundred', 'established', 'individuals', 'review', 'status', 'periodic', 'it', 'had']
Exported audio to temp.wav
temp.wav properties: channels=1, sample_width=2, frame_rate=16000, frames=129600
New Transcript: it had established review of this periodic regular status of four hundred established individuals review status periodic it had
Transcript Without Censoring:
it had established review of this periodic regular status of four hundred established individuals review status periodic it had
Saved rearranged audio to mat_rearranged_20240716_164629.mp3
```

<audio src="examples/mat_rearranged_20240716_164629.mp3" controls></audio>

The supplied "new transcript" is gibberish but demonstrates the rearrangement functionality.

### Example 3 command

We will attempt to make Orson Welles' job a bit easier.

```sh
python audio-censor.py --audio_file examples/orson.mp3 --transcribe_only --model_path vosk-model-en-us-0.22/ --bad_words examples/mat_redact.csv --new_transcript examples/orson_new.txt
```

#### Input file

<audio src="examples/orson.mp3" controls></audio>

```text
because Findus freeze the cod at sea and then add a crumb crisp ooh crumb crisp coating ah that's tough crumb crisp coating
```

### Example 3 output

```text
Audio file: examples/orson.mp3
Bad words file: examples/mat_redact.csv
Model path: vosk-model-en-us-0.22/
Loaded audio file examples/orson.mp3, duration: 12584 ms
Loaded bad words: ['established', 'review', 'status', 'individuals']
Exported audio to temp.wav
temp.wav properties: channels=1, sample_width=2, frame_rate=16000, frames=201340
Raw transcript:
it's an endless freeze the car to see and then add crumb crust crumb crisp coating let's cut from crisp coating
Loaded new transcript: ['because', 'Findus', 'freeze', 'the', 'cod', 'at', 'sea', 'and', 'then', 'add', 'a', 'crisp', 'coating']
Exported audio to temp.wav
temp.wav properties: channels=1, sample_width=2, frame_rate=16000, frames=33600
New Transcript: i use them and add coffee
Censored Transcript:
i use them and add coffee
Saved cleaned audio to orson_cleaned_20240716_170952.mp3
```

As you can see, the recognition does not really understand Orson Welles and parses his speech incorrectly.

<audio src="examples/orson_cleaned_20240716_170952.mp3" controls></audio>

## Errata

Probably many. Raise an issue in this repository if you want, but there's no guarantee it will ever be fixed.
The argument parsing and a bunch of other things need improvement but for a prototype [this is fine](https://knowyourmeme.com/memes/this-is-fine)

## License & Whatever

Copyright (c) 2024 T E Vaughan

[Schrödinger License](license.md)

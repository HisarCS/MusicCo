# Music Note Parser

This repository contains a script to parse musical note data stored in a custom text-based protocol format. The parsed data includes the note name, octave, start time, duration, and volume, and organizes it into a structured table for further analysis.

## Custom Protocol Description

The custom protocol uses a simple format where each note is described in the following structure:

```txt
<Note><Octave>-<Start Time>-<Duration>-<Volume>
```


### Parameters
- **`<Note>`**: The musical note name (e.g., `Do`, `Re`, `Mi`, etc.).
- **`<Octave>`**: The octave of the note, written as an integer immediately after the note name (e.g., `4` for middle C's octave).
- **`<Start Time>`**: The time (in seconds) when the note begins.
- **`<Duration>`**: The length of time (in seconds) the note is played.
- **`<Volume>`**: The volume or intensity of the note, represented as an integer.

### Example

Here’s an example of the input data stored in a txt:

```txt
Do4-0.0-0.5-100 Re4-0.5-0.5-100 Mi4-1.0-0.5-100 Fa6-1.5-0.5-100 Sol4-2.0-0.5-100 La5-2.5-0.5-100 Si3-3.0-0.5-100
```


### Explanation of Example
- `Do4-0.0-0.5-100`: Note `Do`, Octave `4`, starts at `0.0` seconds, lasts for `0.5` seconds, with volume `100`.
- `Re4-0.5-0.5-100`: Note `Re`, Octave `4`, starts at `0.5` seconds, lasts for `0.5` seconds, with volume `100`.

## Script Usage

### Requirements
- Python 3.x
- pandas

### How to Run
1. Place your musical note data in a text file named `music.txt` in the same directory as the script.
2. Run the script using Python:
   ```bash
   python music_parser.py



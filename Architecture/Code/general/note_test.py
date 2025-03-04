import pygame
import numpy as np
import time
from music_parser import parse_music_data  # Importing the parser function

# Constants
SAMPLE_RATE = 44100
VOLUME = 0.8
DURATION_BUFFER = 0.1
OCTAVE_OFFSET = 4

# Frequency Mapping (Octave 4)
FREQS = {
    "Do": 261.63, "Re": 293.66, "Mi": 329.63, "Fa": 349.23,
    "Sol": 392.00, "La": 440.00, "Si": 493.88
}

def generate_piano_wave_stereo(frequency, duration, pan=0.5, sample_rate=SAMPLE_RATE):
    """
    Generates a piano-like waveform with harmonics in stereo.
    
    Args:
        frequency: Note frequency in Hz
        duration: Note duration in seconds
        pan: Panning value between 0.0 (full left) and 1.0 (full right), default is 0.5 (center)
        sample_rate: Sample rate in Hz
    
    Returns:
        2D numpy array with shape (samples, 2) for stereo output
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    sine_wave = np.sin(2 * np.pi * frequency * t)
    harmonics = (
        sine_wave * 0.6 +
        np.sin(2 * np.pi * frequency * 2 * t) * 0.2 +
        np.sin(2 * np.pi * frequency * 3 * t) * 0.1
    )
    
    # Apply envelope to reduce clicks at start/end
    envelope = np.ones_like(t)
    attack = int(0.02 * sample_rate)  # 20ms attack
    release = int(0.05 * sample_rate)  # 50ms release
    
    if attack > 0:
        envelope[:attack] = np.linspace(0, 1, attack)
    if release > 0 and len(envelope) > release:
        envelope[-release:] = np.linspace(1, 0, release)
        
    harmonics = harmonics * envelope
    
    # Calculate left and right channel values
    left_vol = 1.0 - pan
    right_vol = pan
    
    # Convert to int16 for each channel separately
    left_channel = (harmonics * left_vol * 32767).astype(np.int16)
    right_channel = (harmonics * right_vol * 32767).astype(np.int16)
    
    # Create stereo array (samples, 2)
    stereo = np.column_stack((left_channel, right_channel))
    
    return stereo


def play_note(note, octave, duration, volume, pan=0.5):
    """
    Plays a note using pygame sound in stereo.
    
    Args:
        note: Musical note (Do, Re, Mi, etc.)
        octave: Octave number
        duration: Duration in seconds
        volume: Volume (0-100)
        pan: Panning value between 0.0 (full left) and 1.0 (full right)
    """
    if note in FREQS:
        frequency = FREQS[note] * (2 ** (octave - OCTAVE_OFFSET))
        wave = generate_piano_wave_stereo(frequency, duration, pan)

        # Ensure mixer is correctly initialized for stereo
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
        elif pygame.mixer.get_init()[2] != 2:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)

        sound = pygame.sndarray.make_sound(wave)
        sound.set_volume(volume / 100)
        sound.play()


def play_song(file_path):
    """Reads and plays a song from track.txt with stereo panning."""
    with open(file_path, 'r') as file:
        input_data = file.read()

    song_data = parse_music_data(input_data)
    start_time = time.time()
    
    # Sort by start time to ensure correct playback order
    song_data.sort(key=lambda x: x['Start Time'])
    
    # Calculate panning for each note based on pitch
    # Higher notes will be more to the right, lower notes more to the left
    all_octaves = [note['Octave'] for note in song_data]
    min_octave = min(all_octaves)
    max_octave = max(all_octaves)
    octave_range = max(1, max_octave - min_octave)
    
    for note_data in song_data:
        note_start = note_data['Start Time']
        note_duration = note_data['Duration']
        volume = note_data['Volume']
        
        # Calculate pan value (0.0 = left, 1.0 = right)
        # Lower notes to the left, higher notes to the right
        if octave_range > 1:
            pan = 0.1 + 0.8 * ((note_data['Octave'] - min_octave) / octave_range)
        else:
            # If all notes are the same octave, pan based on note within octave
            note_index = list(FREQS.keys()).index(note_data['Note'])
            pan = 0.1 + 0.8 * (note_index / (len(FREQS) - 1))

        # Wait until it's time to play this note
        while time.time() - start_time < note_start:
            time.sleep(0.01)

        play_note(note_data['Note'], note_data['Octave'], note_duration, volume, pan)
        
        # For sequential play (comment this if you want concurrent play)
        time.sleep(note_duration + DURATION_BUFFER)

# Initialize the mixer before calling play_song
pygame.init()
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
play_song('track.txt')  # Play the song from track.txt

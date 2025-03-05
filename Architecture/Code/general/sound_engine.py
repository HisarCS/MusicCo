# sound_engine.py - Functions for generating and playing sounds

import pygame
import numpy as np
from constants import SAMPLE_RATE, FREQS, OCTAVE_OFFSET

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


def generate_error_sound(duration=0.3, sample_rate=SAMPLE_RATE):
    """Generate an unpleasant error sound"""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate dissonant frequencies
    wave1 = np.sin(2 * np.pi * 440 * t) * 0.3
    wave2 = np.sin(2 * np.pi * 466 * t) * 0.3  # Dissonant with 440
    wave3 = np.sin(2 * np.pi * 380 * t) * 0.3  # More dissonance
    
    # Add some noise
    noise = np.random.normal(0, 0.2, len(t))
    
    # Combine and apply envelope
    envelope = np.ones_like(t)
    release = int(0.1 * sample_rate)
    if release > 0 and len(envelope) > release:
        envelope[-release:] = np.linspace(1, 0, release)
    
    combined = (wave1 + wave2 + wave3 + noise) * envelope
    
    # Convert to stereo int16
    left_channel = (combined * 32767 * 0.5).astype(np.int16)
    right_channel = (combined * 32767 * 0.5).astype(np.int16)
    
    return np.column_stack((left_channel, right_channel))


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


def play_error_sound(volume=80):
    """Play the error sound"""
    wave = generate_error_sound()
    sound = pygame.sndarray.make_sound(wave)
    sound.set_volume(volume / 100)
    sound.play()


# Initialize pygame mixer when this module is imported
pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
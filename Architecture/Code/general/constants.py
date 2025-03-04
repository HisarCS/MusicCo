# constants.py - Shared constants for the music game

# Audio Constants
SAMPLE_RATE = 44100
VOLUME = 0.8
DURATION_BUFFER = 0.1
OCTAVE_OFFSET = 4

# Frequency Mapping (Octave 4)
FREQS = {
    "Do": 261.63, "Re": 293.66, "Mi": 329.63, "Fa": 349.23,
    "Sol": 392.00, "La": 440.00, "Si": 493.88
}

# Visualization Constants
WIDTH, HEIGHT = 800, 400
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
NOTE_SPEED = 150  # Pixels per second
THRESHOLD_X = 200  # Notes play after passing this x-coordinate
NOTE_POSITIONS = {
    "Do": 300, "Re": 270, "Mi": 240, "Fa": 210,
    "Sol": 180, "La": 150, "Si": 120
}

# Keyboard Mappings
# constants.py - Shared constants for the music game

# Audio Constants
SAMPLE_RATE = 44100
VOLUME = 0.8
DURATION_BUFFER = 0.1
OCTAVE_OFFSET = 4

# Frequency Mapping (Octave 4)
FREQS = {
    "Do": 261.63, "Re": 293.66, "Mi": 329.63, "Fa": 349.23,
    "Sol": 392.00, "La": 440.00, "Si": 493.88
}

# Visualization Constants
WIDTH, HEIGHT = 1600, 800
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
NOTE_SPEED = 150  # Pixels per second
THRESHOLD_X = 200  # Notes play after passing this x-coordinate
NOTE_POSITIONS = {
    "Do": 300, "Re": 270, "Mi": 240, "Fa": 210,
    "Sol": 180, "La": 150, "Si": 120
}

# Keyboard Mappings
import pygame
KEY_MAPPINGS = {
    pygame.K_1: "Do",
    pygame.K_2: "Re", 
    pygame.K_3: "Mi", 
    pygame.K_4: "Fa",
    pygame.K_5: "Sol", 
    pygame.K_6: "La", 
    pygame.K_7: "Si"
}

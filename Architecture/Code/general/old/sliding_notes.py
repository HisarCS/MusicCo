import pygame
import numpy as np
import time
from music_parser import parse_music_data

# Import sound functions from note_test.py
from note_test import (
    generate_piano_wave_stereo,
    play_note,
    SAMPLE_RATE,
    FREQS,
    OCTAVE_OFFSET
)

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

def play_song_with_visuals(file_path):
    """Reads and plays a song with synchronized sliding notes after passing threshold."""
    # Initialize pygame and mixer for stereo
    pygame.init()
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
    
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Sliding Notes - Stereo Edition")
    font = pygame.font.Font(None, 36)
    clock = pygame.time.Clock()
    
    with open(file_path, 'r') as file:
        input_data = file.read()
        
    song_data = parse_music_data(input_data)
    
    # Pre-calculate the expected appearance time for each note
    # We need notes to appear from the right side of the screen
    # and reach the threshold line exactly at their start time
    for note in song_data:
        # How long it takes for a note to reach the threshold from offscreen
        travel_time = (WIDTH - THRESHOLD_X) / NOTE_SPEED
        # When the note should first appear on screen
        note['appear_time'] = note['Start Time'] - travel_time
    
    # Calculate pan values based on pitch
    all_octaves = [note['Octave'] for note in song_data]
    min_octave = min(all_octaves)
    max_octave = max(all_octaves)
    octave_range = max(1, max_octave - min_octave)
    
    # For visualization
    note_colors = {}
    for note_name in FREQS.keys():
        note_index = list(FREQS.keys()).index(note_name)
        hue = int(note_index * 255 / (len(FREQS) - 1))
        color = pygame.Color(0, 0, 0)
        color.hsva = (hue, 100, 100, 100)
        note_colors[note_name] = color
    
    # Get total song duration for auto-exit
    last_note_time = max([n['Start Time'] + n['Duration'] for n in song_data]) if song_data else 0
    
    # Start game loop
    start_time = time.time()
    running = True
    played_notes = set()  # Track played notes to prevent repeats
    
    while running:
        screen.fill(BG_COLOR)
        current_time = time.time() - start_time
        
        # Draw vertical threshold line
        pygame.draw.line(screen, (100, 100, 100), (THRESHOLD_X, 0), (THRESHOLD_X, HEIGHT), 2)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
                
        # Draw note labels on left side
        for note_name, y_pos in NOTE_POSITIONS.items():
            label = font.render(note_name, True, note_colors[note_name])
            screen.blit(label, (20, y_pos))
        
        # Draw and process notes
        visible_notes = [note for note in song_data if current_time >= note['appear_time']]
        
        for note_data in visible_notes:
            note_start = note_data['Start Time']
            note_duration = note_data['Duration']
            volume = note_data['Volume']
            note_name = note_data['Note']
            octave = note_data['Octave']
            
            # Calculate panning based on octave and note
            if octave_range > 1:
                pan = 0.1 + 0.8 * ((octave - min_octave) / octave_range)
            else:
                note_index = list(FREQS.keys()).index(note_name)
                pan = 0.1 + 0.8 * (note_index / (len(FREQS) - 1))
            
            # Calculate note position
            # Time elapsed since the note should have appeared
            elapsed_since_appear = current_time - note_data['appear_time']
            # Position based on elapsed time and speed
            x_pos = WIDTH - int(elapsed_since_appear * NOTE_SPEED)
            
            y_pos = NOTE_POSITIONS.get(note_name, HEIGHT // 2)
            
            # Calculate width based on duration
            note_width = int(note_duration * NOTE_SPEED)
            
            # Only draw if at least partially visible
            if x_pos + note_width > 0 and x_pos < WIDTH:
                # Draw the note as a rectangle
                color = note_colors[note_name]
                pygame.draw.rect(screen, color, (x_pos, y_pos, note_width, 30))
                
                # Add note label
                text_surface = font.render(f"{note_name}{octave}", True, TEXT_COLOR)
                if note_width > 40:  # Only add text if there's enough space
                    screen.blit(text_surface, (x_pos + 5, y_pos + 5))
                
                # Show left/right indicator based on pan value
                pan_indicator = "L" if pan < 0.4 else ("R" if pan > 0.6 else "C")
                pan_text = font.render(pan_indicator, True, TEXT_COLOR)
                if note_width > 20:
                    screen.blit(pan_text, (x_pos + note_width - 15, y_pos + 5))
            
            # Play note only when crossing the threshold
            note_id = (note_name, note_start)
            threshold_crossing = (x_pos <= THRESHOLD_X) and (x_pos + NOTE_SPEED/60 > THRESHOLD_X)
            
            if threshold_crossing and note_id not in played_notes:
                play_note(note_name, octave, note_duration, volume, pan)
                played_notes.add(note_id)
        
        # Display current time
        time_text = font.render(f"Time: {current_time:.2f}s", True, TEXT_COLOR)
        screen.blit(time_text, (WIDTH - 150, 10))
        
        pygame.display.flip()
        clock.tick(60)
        
        # End if all notes have been played and sufficient time has elapsed
        if current_time > last_note_time + 2:
            running = False
    
    pygame.quit()

# Run the visualized song player

play_song_with_visuals("track.txt")

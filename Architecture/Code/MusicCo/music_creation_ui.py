# music_creation_ui.py - UI components for music creation

import pygame
from constants import (
    WIDTH, HEIGHT, BG_COLOR, TEXT_COLOR, FREQS, 
    NOTE_POSITIONS, NOTE_SPEED, INSTRUMENTS, INSTRUMENT_NAMES
)
from music_creation import NOTE_SELECTION, LENGTH_SELECTION, POSITION_SELECTION, NOTE_LENGTHS

def calculate_note_colors():
    """Generate colors for each note type"""
    note_colors = {}
    for note_name in FREQS.keys():
        note_index = list(FREQS.keys()).index(note_name)
        hue = int(note_index * 255 / (len(FREQS) - 1))
        color = pygame.Color(0, 0, 0)
        color.hsva = (hue, 100, 100, 100)
        note_colors[note_name] = color
    return note_colors

def draw_note_ribbon(creator):
    """Draw a ribbon showing all notes in the composition"""
    # Sort notes by position
    sorted_notes = sorted(creator.composition, key=lambda x: x['Start Time'])
    
    # Draw timeline
    timeline_y = HEIGHT - 100
    timeline_start = 50
    timeline_end = WIDTH - 50
    timeline_length = timeline_end - timeline_start
    
    # Calculate scale: pixels per second
    pixels_per_second = timeline_length / creator.max_position
    
    # Draw the timeline
    pygame.draw.line(creator.screen, (150, 150, 150), 
                     (timeline_start, timeline_y), 
                     (timeline_end, timeline_y), 2)
    
    # Draw time markers
    for i in range(0, int(creator.max_position) + 1, 1):
        marker_x = timeline_start + i * pixels_per_second
        pygame.draw.line(creator.screen, (100, 100, 100),
                       (marker_x, timeline_y - 5),
                       (marker_x, timeline_y + 5), 1)
        
        # Add time labels for whole seconds
        if i % 2 == 0:  # Only show every other second to avoid crowding
            time_label = creator.small_font.render(f"{i}s", True, (150, 150, 150))
            creator.screen.blit(time_label, (marker_x - 10, timeline_y + 10))
    
    # Draw each note as a colored rectangle
    note_height = 20
    for note in sorted_notes:
        start_x = timeline_start + note['Start Time'] * pixels_per_second
        width = note['Duration'] * pixels_per_second
        
        # Y position based on note pitch
        y_offset = list(FREQS.keys()).index(note['Note']) * (note_height + 5)
        note_y = timeline_y - 50 - y_offset
        
        # Get base color
        base_color = creator.note_colors[note['Note']]
        
        # Determine color based on instrument
        if note.get('Instrument', INSTRUMENTS["PIANO"]) == INSTRUMENTS["ELECTRO_GUITAR"]:
            # Electro guitar gets a more intense color
            color = pygame.Color(
                min(255, base_color.r + 40),
                base_color.g,
                min(255, base_color.b + 40)
            )
            
            # Add a small guitar icon or indicator
            pygame.draw.polygon(creator.screen, (255, 255, 255), 
                              [(start_x + 2, note_y + 2), 
                               (start_x + 7, note_y + 10), 
                               (start_x + 2, note_y + 18)])
        else:
            color = base_color
        
        # Draw note rectangle
        pygame.draw.rect(creator.screen, color, (start_x, note_y, width, note_height))
        
        # Add note label
        label = creator.small_font.render(f"{note['Note']}{note['Octave']}", True, TEXT_COLOR)
        if width > label.get_width() + 10:  # Only show label if enough space
            creator.screen.blit(label, (start_x + 5, note_y + 2))
    
    # Draw position marker for current position
    if creator.state == POSITION_SELECTION:
        marker_x = timeline_start + creator.position * pixels_per_second
        pygame.draw.line(creator.screen, (255, 255, 0), 
                        (marker_x, timeline_y - 70), 
                        (marker_x, timeline_y + 20), 2)

def draw_keyboard_guide(creator):
    """Draw a guide showing which keys correspond to which notes"""
    guide_y = 50
    for i, (note_name, y_pos) in enumerate(NOTE_POSITIONS.items()):
        # Find the key that maps to this note
        key_name = None
        for key, note in creator.key_to_note.items():
            if note == note_name:
                key_name = pygame.key.name(key).upper()
                break
        
        if key_name:
            # Draw key name
            key_text = creator.font.render(f"Press '{key_name}' for {note_name}", True, creator.note_colors[note_name])
            creator.screen.blit(key_text, (50, guide_y + i * 30))

def draw_state_info(creator):
    """Draw information about the current state and selection"""
    # Always show current instrument
    instrument_text = creator.font.render(f"Instrument: {INSTRUMENT_NAMES[creator.selected_instrument]}", True, (200, 200, 100))
    creator.screen.blit(instrument_text, (WIDTH - 300, 20))
    
    if creator.state == NOTE_SELECTION:
        state_text = creator.font.render("Select a note (number keys)", True, TEXT_COLOR)
        creator.screen.blit(state_text, (WIDTH//2 - 150, 20))
        
        instrument_hint = creator.small_font.render("Press 'A' to toggle instrument", True, (200, 200, 100))
        creator.screen.blit(instrument_hint, (WIDTH//2 - 150, 60))
        
        octave_text = creator.font.render(f"Current Octave: {creator.selected_octave} (↑/↓ to change)", True, TEXT_COLOR)
        creator.screen.blit(octave_text, (WIDTH//2 - 150, 90))
        
    elif creator.state == LENGTH_SELECTION:
        state_text = creator.font.render(f"Select note length: {NOTE_LENGTHS[creator.length_index]}s", True, TEXT_COLOR)
        creator.screen.blit(state_text, (WIDTH//2 - 150, 20))
        
        hint_text = creator.small_font.render("Press 'A' to cycle through lengths, SPACE to confirm", True, TEXT_COLOR)
        creator.screen.blit(hint_text, (WIDTH//2 - 200, 60))
        
        cancel_text = creator.small_font.render("Press BACKSPACE or DELETE to cancel", True, TEXT_COLOR)
        creator.screen.blit(cancel_text, (WIDTH//2 - 150, 90))
        
        # Show the different length options
        options_y = 130
        for i, length in enumerate(NOTE_LENGTHS):
            color = (255, 255, 0) if i == creator.length_index else (150, 150, 150)
            option_text = creator.font.render(f"{length}s", True, color)
            creator.screen.blit(option_text, (50 + i * 100, options_y))
        
    elif creator.state == POSITION_SELECTION:
        state_text = creator.font.render(f"Select position: {creator.position:.1f}s", True, TEXT_COLOR)
        creator.screen.blit(state_text, (WIDTH//2 - 150, 20))
        
        hint_text = creator.small_font.render("Press 'A' to move position, SPACE to add note", True, TEXT_COLOR)
        creator.screen.blit(hint_text, (WIDTH//2 - 200, 60))
        
        cancel_text = creator.small_font.render("Press BACKSPACE or DELETE to cancel", True, TEXT_COLOR)
        creator.screen.blit(cancel_text, (WIDTH//2 - 150, 90))

def draw_controls_guide(creator):
    """Draw a guide for the controls"""
    controls_y = HEIGHT - 40
    controls_text = creator.small_font.render(
        "BACKSPACE: Delete last note | CTRL+S: Save | ESC: Exit", 
        True, (200, 200, 200)
    )
    creator.screen.blit(controls_text, (WIDTH//2 - controls_text.get_width()//2, controls_y))

def draw_interface(creator):
    """Draw the complete interface"""
    # Clear screen
    creator.screen.fill(BG_COLOR)
    
    # Draw keyboard guide
    draw_keyboard_guide(creator)
    
    # Draw state-specific information
    draw_state_info(creator)
    
    # Draw the note ribbon
    draw_note_ribbon(creator)
    
    # Draw controls guide
    draw_controls_guide(creator)
    
    # Update display
    pygame.display.flip()
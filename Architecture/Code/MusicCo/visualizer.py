# visualizer.py - Enhanced visualization with pre-play support and instrument separation

import pygame
import time
from constants import (
    WIDTH, HEIGHT, BG_COLOR, TEXT_COLOR, 
    NOTE_SPEED, THRESHOLD_X, NOTE_POSITIONS, FREQS,
    INSTRUMENTS, INSTRUMENT_NAMES
)

# Define separate positions for piano and guitar notes
# Piano notes are in the top half, guitar notes in the bottom half
PIANO_NOTE_POSITIONS = {
    "Do": 100, "Re": 130, "Mi": 160, "Fa": 190,
    "Sol": 220, "La": 250, "Si": 280
}

GUITAR_NOTE_POSITIONS = {
    "Do": 450, "Re": 480, "Mi": 510, "Fa": 540,
    "Sol": 570, "La": 600, "Si": 630
}

# Section divider position
SECTION_DIVIDER_Y = 350

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

def init_pygame_window():
    """Initialize pygame window and return screen and fonts"""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SlidePlay - Hit the notes!")
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()
    return screen, font, small_font, clock

def prepare_song_data(song_data):
    """Prepare song data with appearance times and status flags"""
    for note in song_data:
        # How long it takes for a note to reach the threshold from offscreen
        travel_time = (WIDTH - THRESHOLD_X) / NOTE_SPEED
        # When the note should first appear on screen
        note['appear_time'] = note['Start Time'] - travel_time
        # Track if the note has been played/missed/wrong
        note['played'] = False
        note['missed'] = False
        note['wrong'] = False  # Add property to track wrong key presses
        # Beat accuracy properties
        note['expected_duration'] = note['Duration']
        note['actual_duration'] = 0
        note['beat_accuracy'] = 0
        # Make sure instrument is defined (for backward compatibility)
        if 'Instrument' not in note:
            note['Instrument'] = INSTRUMENTS["PIANO"]
    return song_data

def get_visible_notes(song_data, current_time):
    """Get notes that should be visible on screen"""
    return [note for note in song_data if current_time >= note['appear_time']]

def update_missed_notes(visible_notes, current_time, missed_notes_count):
    """Check and update status of missed notes"""
    for note in visible_notes:
        # Calculate position
        elapsed_since_appear = current_time - note['appear_time']
        x_pos = WIDTH - int(elapsed_since_appear * NOTE_SPEED)
        note_width = int(note['Duration'] * NOTE_SPEED)
        
        # Check if note was missed (passed threshold without being played)
        if not note['played'] and not note['missed'] and not note['wrong'] and (x_pos + note_width < THRESHOLD_X - 40):
            note['missed'] = True
            missed_notes_count += 1
    
    return missed_notes_count

def get_note_y_position(note_name, instrument):
    """Get the Y position for a note based on its name and instrument"""
    if instrument == INSTRUMENTS["PIANO"]:
        return PIANO_NOTE_POSITIONS.get(note_name, 190)  # Default position if note not found
    else:  # ELECTRO_GUITAR
        return GUITAR_NOTE_POSITIONS.get(note_name, 540)  # Default position if note not found

def draw_section_divider(screen, font):
    """Draw a divider between piano and guitar sections with labels"""
    # Draw horizontal divider line
    pygame.draw.line(screen, (100, 100, 100), (0, SECTION_DIVIDER_Y), (WIDTH, SECTION_DIVIDER_Y), 2)
    
    # Draw section labels
    piano_label = font.render("Piano", True, (200, 200, 200))
    guitar_label = font.render("Electro Guitar", True, (200, 200, 100))
    
    # Position labels on the left side
    screen.blit(piano_label, (20, SECTION_DIVIDER_Y - 40))
    screen.blit(guitar_label, (20, SECTION_DIVIDER_Y + 10))

def draw_instruction_screen(screen, font, small_font, key_display, note_colors, instruction_box):
    """Draw the instruction screen"""
    pygame.draw.rect(screen, (50, 50, 50), instruction_box)
    pygame.draw.rect(screen, (200, 200, 200), instruction_box, 2)
    
    title = font.render("SlidePlay - Instructions", True, TEXT_COLOR)
    screen.blit(title, (WIDTH//4 + 10, HEIGHT//4 + 10))
    
    # Draw piano note keys
    y_pos = HEIGHT//4 + 50
    screen.blit(font.render("Piano Notes:", True, (200, 200, 200)), (WIDTH//4 + 20, y_pos))
    y_pos += 30
    
    for i, note_name in enumerate(NOTE_POSITIONS.keys()):
        key_name = pygame.key.name(key_display.get(note_name, pygame.K_SPACE)).upper()
        instr = small_font.render(f"Press '{key_name}' for {note_name}", True, note_colors[note_name])
        screen.blit(instr, (WIDTH//4 + 40, y_pos + i*25))
    
    # Move down for additional instructions
    y_pos += len(NOTE_POSITIONS) * 25 + 20
    
    hint1 = small_font.render("Hit the notes as they cross the vertical line!", True, TEXT_COLOR)
    screen.blit(hint1, (WIDTH//4 + 20, y_pos))
    
    hint2 = small_font.render("Hold keys for the right duration for better beat accuracy!", True, TEXT_COLOR)
    screen.blit(hint2, (WIDTH//4 + 20, y_pos + 30))
    
    hint3 = small_font.render("You'll hear a demo of the song before you play", True, TEXT_COLOR)
    screen.blit(hint3, (WIDTH//4 + 20, y_pos + 60))
    
    hint4 = small_font.render("Press 'W' to toggle between Piano and Electro Guitar", True, (200, 200, 100))
    screen.blit(hint4, (WIDTH//4 + 20, y_pos + 90))
    
    hint5 = small_font.render("Piano notes are displayed on top, Electro Guitar notes on bottom", True, (200, 200, 100))
    screen.blit(hint5, (WIDTH//4 + 20, y_pos + 120))

def draw_pre_play_screen(screen, font, small_font, note_colors, current_time, visible_notes, last_played_index):
    """Draw the pre-play demonstration screen"""
    screen.fill(BG_COLOR)
    
    # Draw title
    title_text = font.render("Pre-Play Demonstration", True, TEXT_COLOR)
    screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 20))
    
    subtitle_text = small_font.render("Listen to how the song should sound", True, TEXT_COLOR)
    screen.blit(subtitle_text, (WIDTH//2 - subtitle_text.get_width()//2, 60))
    
    # Draw skip instructions
    skip_text = small_font.render("Press SPACE to skip", True, (200, 200, 200))
    screen.blit(skip_text, (WIDTH//2 - skip_text.get_width()//2, HEIGHT - 30))
    
    # Draw vertical threshold line
    pygame.draw.line(screen, (200, 200, 200), (THRESHOLD_X, 0), (THRESHOLD_X, HEIGHT), 2)
    
    # Draw section divider
    draw_section_divider(screen, small_font)
    
    # Draw note labels on left side for piano
    for note_name, y_pos in PIANO_NOTE_POSITIONS.items():
        label = font.render(f"{note_name}", True, note_colors[note_name])
        screen.blit(label, (20, y_pos))
    
    # Draw note labels on left side for guitar
    for note_name, y_pos in GUITAR_NOTE_POSITIONS.items():
        label = font.render(f"{note_name}", True, note_colors[note_name])
        screen.blit(label, (20, y_pos))
    
    # Draw notes
    for note_data in visible_notes:
        # Calculate position
        elapsed_since_appear = current_time - note_data['appear_time']
        x_pos = WIDTH - int(elapsed_since_appear * NOTE_SPEED)
        
        note_name = note_data['Note']
        octave = note_data['Octave']
        instrument = note_data.get('Instrument', INSTRUMENTS["PIANO"])
        
        # Get y position based on instrument and note name
        y_pos = get_note_y_position(note_name, instrument)
        note_duration = note_data['Duration']
        
        # Calculate width based on duration
        note_width = int(note_duration * NOTE_SPEED)
        
        # Only draw if at least partially visible
        if x_pos + note_width > 0 and x_pos < WIDTH:
            # Determine color based on status
            base_color = note_colors[note_name]
            if instrument == INSTRUMENTS["ELECTRO_GUITAR"]:
                # Electro guitar gets a more intense color
                color = pygame.Color(
                    min(255, base_color.r + 40),
                    base_color.g,
                    min(255, base_color.b + 40)
                )
                
                # Draw a small indicator for electro guitar
                if note_width > 20:
                    pygame.draw.polygon(screen, (255, 255, 255), 
                                      [(x_pos + 2, y_pos + 2), 
                                       (x_pos + 7, y_pos + 10), 
                                       (x_pos + 2, y_pos + 18)])
            else:
                color = base_color
                
            if note_data.get('demo_played', False):
                # Highlight the note if it has been played in the demo
                if x_pos < THRESHOLD_X:
                    # Already passed the threshold
                    brightness = 200  # More saturated for played notes
                    if color.r > 0: color.r = min(255, color.r + brightness)
                    if color.g > 0: color.g = min(255, color.g + brightness)
                    if color.b > 0: color.b = min(255, color.b + brightness)
            
            # Draw the note as a rectangle
            pygame.draw.rect(screen, color, (x_pos, y_pos, note_width, 30))
            
            # Add note label
            text_surface = font.render(f"{note_name}{octave}", True, TEXT_COLOR)
            if note_width > 40:  # Only add text if there's enough space
                screen.blit(text_surface, (x_pos + 5, y_pos + 5))
    
    # Display current time
    time_text = small_font.render(f"Time: {current_time:.2f}s", True, TEXT_COLOR)
    screen.blit(time_text, (10, 10))
    
    # Show which note is currently playing
    if last_played_index >= 0 and len(visible_notes) > 0:
        now_playing_text = font.render("Now Playing:", True, TEXT_COLOR)
        screen.blit(now_playing_text, (WIDTH - 300, 100))
        
        # Find the last played note
        played_notes = [n for n in visible_notes if n.get('demo_played', False)]
        if played_notes:
            last_note = played_notes[-1]
            instrument = INSTRUMENT_NAMES.get(last_note.get('Instrument', INSTRUMENTS["PIANO"]), "Piano")
            note_text = font.render(f"{last_note['Note']}{last_note['Octave']} ({instrument})", True, note_colors[last_note['Note']])
            screen.blit(note_text, (WIDTH - 300, 140))

def get_beat_accuracy_color(accuracy):
    """Get a color representing beat accuracy from red to green"""
    if accuracy >= 95:
        return (0, 255, 0)  # Excellent - Green
    elif accuracy >= 75:
        return (128, 255, 0)  # Great - Light Green
    elif accuracy >= 50:
        return (255, 255, 0)  # Good - Yellow
    elif accuracy >= 25:
        return (255, 128, 0)  # Poor - Orange
    else:
        return (255, 0, 0)  # Bad - Red

def draw_game_screen(screen, font, small_font, key_display, note_colors, current_time, 
                     visible_notes, score, max_score, correct_hits, missed_notes, wrong_notes,
                     last_key_pressed=None, active_note_info=None, beat_accuracy=0,
                     current_instrument=INSTRUMENTS["PIANO"], override_instruments=False):
    """Draw the main game screen with notes and UI"""
    screen.fill(BG_COLOR)
    
    # Draw vertical threshold line
    pygame.draw.line(screen, (200, 200, 200), (THRESHOLD_X, 0), (THRESHOLD_X, HEIGHT), 2)
    
    # Draw section divider
    draw_section_divider(screen, small_font)
    
    # Draw note labels and key mappings on left side for piano
    for note_name, y_pos in PIANO_NOTE_POSITIONS.items():
        key_name = pygame.key.name(key_display.get(note_name, pygame.K_SPACE)).upper()
        label = font.render(f"{key_name}: {note_name}", True, note_colors[note_name])
        screen.blit(label, (20, y_pos))
    
    # Draw note labels and key mappings on left side for guitar
    for note_name, y_pos in GUITAR_NOTE_POSITIONS.items():
        key_name = pygame.key.name(key_display.get(note_name, pygame.K_SPACE)).upper()
        label = font.render(f"{key_name}: {note_name}", True, note_colors[note_name])
        screen.blit(label, (20, y_pos))
    
    # Draw notes
    for note_data in visible_notes:
        # Calculate position
        elapsed_since_appear = current_time - note_data['appear_time']
        x_pos = WIDTH - int(elapsed_since_appear * NOTE_SPEED)
        
        note_name = note_data['Note']
        octave = note_data['Octave']
        
        # Determine instrument - either from override or from note data
        if override_instruments:
            instrument = current_instrument
        else:
            instrument = note_data.get('Instrument', INSTRUMENTS["PIANO"])
        
        # Get y position based on instrument and note name
        y_pos = get_note_y_position(note_name, instrument)
        note_duration = note_data['Duration']
        
        # Calculate width based on duration
        note_width = int(note_duration * NOTE_SPEED)
        
        # Only draw if at least partially visible
        if x_pos + note_width > 0 and x_pos < WIDTH:
            # Determine base color based on note type
            base_color = note_colors[note_name]
            
            # Determine color based on note status and instrument
            if note_data['played']:
                # If note was played, show beat accuracy with color intensity
                if 'beat_accuracy' in note_data and note_data['beat_accuracy'] > 0:
                    color = get_beat_accuracy_color(note_data['beat_accuracy'])
                else:
                    color = (0, 255, 0)  # Default green for hit notes without beat data
            elif note_data['missed']:
                color = (255, 0, 0)  # Red for missed notes
            elif note_data.get('wrong', False):
                color = (255, 0, 0)  # Also red for wrong notes
            else:
                # Get appropriate color based on instrument
                if instrument == INSTRUMENTS["ELECTRO_GUITAR"]:
                    color = pygame.Color(
                        min(255, base_color.r + 40),
                        base_color.g,
                        min(255, base_color.b + 40)
                    )
                else:
                    color = base_color
            
            # Draw the note as a rectangle
            pygame.draw.rect(screen, color, (x_pos, y_pos, note_width, 30))
            
            # Add indicator for electro guitar notes
            if instrument == INSTRUMENTS["ELECTRO_GUITAR"]:
                if note_width > 20:
                    pygame.draw.polygon(screen, (255, 255, 255), 
                                      [(x_pos + 2, y_pos + 2), 
                                       (x_pos + 7, y_pos + 10), 
                                       (x_pos + 2, y_pos + 18)])
            
            # Add note label
            text_surface = font.render(f"{note_name}{octave}", True, TEXT_COLOR)
            if note_width > 40:  # Only add text if there's enough space
                screen.blit(text_surface, (x_pos + 5, y_pos + 5))
            
            # For played notes with beat accuracy, show a progress bar inside
            if note_data['played'] and 'beat_accuracy' in note_data and note_width > 20:
                # Draw a progress outline for the duration
                pygame.draw.rect(screen, (255, 255, 255), (x_pos + 2, y_pos + 20, note_width - 4, 5), 1)
                
                # Draw the fill based on actual duration vs expected
                actual_width = int((note_data['actual_duration'] / note_data['expected_duration']) * (note_width - 4))
                actual_width = min(actual_width, note_width - 4)  # Cap at full width
                if actual_width > 0:
                    pygame.draw.rect(screen, (255, 255, 255), (x_pos + 2, y_pos + 20, actual_width, 5))
    
    # Display score and stats
    score_text = font.render(f"Score: {score}/{max_score}", True, TEXT_COLOR)
    screen.blit(score_text, (WIDTH - 200, 10))
    
    stats_text = small_font.render(f"Hits: {correct_hits} | Missed: {missed_notes} | Wrong: {wrong_notes}", True, TEXT_COLOR)
    screen.blit(stats_text, (WIDTH - 300, 40))
    
    # Calculate and display note accuracy
    total_attempted = correct_hits + wrong_notes + missed_notes
    note_accuracy = (correct_hits / total_attempted * 100) if total_attempted > 0 else 0
    note_accuracy_text = small_font.render(f"Note Accuracy: {note_accuracy:.1f}%", True, TEXT_COLOR)
    screen.blit(note_accuracy_text, (WIDTH - 200, 70))  # Display below the score and stats
    
    # Display beat accuracy
    beat_accuracy_text = small_font.render(f"Beat Accuracy: {beat_accuracy:.1f}%", True, get_beat_accuracy_color(beat_accuracy))
    screen.blit(beat_accuracy_text, (WIDTH - 200, 100))  # Display below note accuracy
    
    # Display current instrument
    instrument_text = font.render(f"Instrument: {INSTRUMENT_NAMES[current_instrument]}", True, (200, 200, 100))
    screen.blit(instrument_text, (WIDTH - 250, 130))
    
    instrument_hint = small_font.render("Press 'W' to toggle instrument", True, (200, 200, 100))
    screen.blit(instrument_hint, (WIDTH - 250, 160))
    
    # Display override status
    if override_instruments:
        override_text = small_font.render("(Overriding note instruments)", True, (200, 200, 100))
        screen.blit(override_text, (WIDTH - 250, 180))
    
    # Display current time
    time_text = small_font.render(f"Time: {current_time:.2f}s", True, TEXT_COLOR)
    screen.blit(time_text, (10, 10))
    
    # Display active section indicator
    if current_instrument == INSTRUMENTS["PIANO"]:
        section_text = small_font.render("Currently playing in Piano section", True, (200, 200, 200))
        screen.blit(section_text, (THRESHOLD_X + 20, PIANO_NOTE_POSITIONS["Do"] - 30))
    else:
        section_text = small_font.render("Currently playing in Guitar section", True, (200, 200, 100))
        screen.blit(section_text, (THRESHOLD_X + 20, GUITAR_NOTE_POSITIONS["Do"] - 30))
    
    # Display debug info
    if last_key_pressed:
        debug_text = small_font.render(f"Last key: {last_key_pressed} | Active note: {active_note_info}", True, (200, 200, 100))
        screen.blit(debug_text, (10, HEIGHT - 20))

def draw_note_summary(screen, song_data, width, height, area_rect, font, title="Note Accuracy"):
    """Draw a summary of all notes as colored circles in a line within specified area"""
    # Set up dimensions and positioning
    circle_radius = 10
    circle_spacing = 25
    
    # Split area into piano (top) and guitar (bottom) sections
    piano_line_y = area_rect.y + area_rect.height // 3
    guitar_line_y = area_rect.y + (area_rect.height * 2) // 3
    
    # Add title
    title_text = font.render(title, True, TEXT_COLOR)
    screen.blit(title_text, (area_rect.centerx - title_text.get_width()//2, area_rect.y + 20))
    
    # Add section labels
    piano_label = font.render("Piano", True, (200, 200, 200))
    guitar_label = font.render("Guitar", True, (200, 200, 100))
    screen.blit(piano_label, (area_rect.x + 20, piano_line_y - 30))
    screen.blit(guitar_label, (area_rect.x + 20, guitar_line_y - 30))
    
    # Separate notes by instrument
    piano_notes = [note for note in song_data if note.get('Instrument', INSTRUMENTS["PIANO"]) == INSTRUMENTS["PIANO"]]
    guitar_notes = [note for note in song_data if note.get('Instrument', INSTRUMENTS["PIANO"]) == INSTRUMENTS["ELECTRO_GUITAR"]]
    
    # Draw piano notes
    if piano_notes:
        total_width = min(area_rect.width - 60, len(piano_notes) * circle_spacing)
        start_x = area_rect.x + (area_rect.width - total_width) // 2
        
        # Draw a line to place the circles on
        pygame.draw.line(screen, (150, 150, 150), (start_x, piano_line_y), (start_x + total_width, piano_line_y), 2)
        
        # Draw a circle for each note
        for i, note in enumerate(piano_notes):
            x_pos = start_x + (i * total_width // max(1, len(piano_notes) - 1)) if len(piano_notes) > 1 else start_x + total_width // 2
            
            # Determine color based on note status
            if note['played']:
                color = (0, 255, 0)  # Green for correctly hit notes
            elif note['missed'] or note.get('wrong', False):
                color = (255, 0, 0)  # Red for missed or wrong notes
            else:
                color = (150, 150, 150)  # Gray for unplayed notes
            
            # Draw the circle
            pygame.draw.circle(screen, color, (x_pos, piano_line_y), circle_radius)
            
            # Add a small note label below each circle
            note_label = font.render(f"{note['Note']}", True, (200, 200, 200))
            note_label_rect = note_label.get_rect(center=(x_pos, piano_line_y + 20))
            screen.blit(note_label, note_label_rect)
    
    # Draw guitar notes
    if guitar_notes:
        total_width = min(area_rect.width - 60, len(guitar_notes) * circle_spacing)
        start_x = area_rect.x + (area_rect.width - total_width) // 2
        
        # Draw a line to place the circles on
        pygame.draw.line(screen, (150, 150, 150), (start_x, guitar_line_y), (start_x + total_width, guitar_line_y), 2)
        
        # Draw a circle for each note
        for i, note in enumerate(guitar_notes):
            x_pos = start_x + (i * total_width // max(1, len(guitar_notes) - 1)) if len(guitar_notes) > 1 else start_x + total_width // 2
            
            # Determine color based on note status
            if note['played']:
                color = (0, 255, 0)  # Green for correctly hit notes
            elif note['missed'] or note.get('wrong', False):
                color = (255, 0, 0)  # Red for missed or wrong notes
            else:
                color = (150, 150, 150)  # Gray for unplayed notes
            
            # Draw the circle
            pygame.draw.circle(screen, color, (x_pos, guitar_line_y), circle_radius)
            
            # Add guitar indicator
            pygame.draw.line(screen, (255, 255, 255), 
                           (x_pos - 5, guitar_line_y - 5), 
                           (x_pos + 5, guitar_line_y + 5), 2)
            pygame.draw.line(screen, (255, 255, 255), 
                           (x_pos - 5, guitar_line_y + 5), 
                           (x_pos + 5, guitar_line_y - 5), 2)
            
            # Add a small note label below each circle
            note_label = font.render(f"{note['Note']}", True, (200, 200, 200))
            note_label_rect = note_label.get_rect(center=(x_pos, guitar_line_y + 20))
            screen.blit(note_label, note_label_rect)
    
    # Add a legend
    legend_y = area_rect.y + area_rect.height - 50
    
    # Correct notes (green)
    pygame.draw.circle(screen, (0, 255, 0), (area_rect.x + 30, legend_y), circle_radius)
    correct_text = font.render("Correct", True, TEXT_COLOR)
    screen.blit(correct_text, (area_rect.x + 50, legend_y - 10))
    
    # Wrong/Missed notes (red)
    pygame.draw.circle(screen, (255, 0, 0), (area_rect.x + 150, legend_y), circle_radius)
    missed_text = font.render("Wrong/Missed", True, TEXT_COLOR)
    screen.blit(missed_text, (area_rect.x + 170, legend_y - 10))
    
    # Electro guitar indicator
    pygame.draw.circle(screen, (150, 150, 150), (area_rect.x + 330, legend_y), circle_radius)
    pygame.draw.line(screen, (255, 255, 255), 
                   (area_rect.x + 325, legend_y - 5), 
                   (area_rect.x + 335, legend_y + 5), 2)
    pygame.draw.line(screen, (255, 255, 255), 
                   (area_rect.x + 325, legend_y + 5), 
                   (area_rect.x + 335, legend_y - 5), 2)
    electro_text = font.render("Electro Guitar", True, TEXT_COLOR)
    screen.blit(electro_text, (area_rect.x + 350, legend_y - 10))

def draw_beat_accuracy_summary(screen, song_data, area_rect, font, title="Beat Accuracy"):
    """Draw a summary of beat accuracy as colored bars within specified area"""
    bar_height = 15
    bar_spacing = 25
    
    # Add title
    title_text = font.render(title, True, TEXT_COLOR)
    screen.blit(title_text, (area_rect.centerx - title_text.get_width()//2, area_rect.y + 20))
    
    # Split area into piano (top) and guitar (bottom) sections
    piano_section_y = area_rect.y + 60
    piano_section_height = (area_rect.height - 120) // 2
    
    guitar_section_y = piano_section_y + piano_section_height + 30
    guitar_section_height = (area_rect.height - 120) // 2
    
    # Add section labels
    piano_label = font.render("Piano", True, (200, 200, 200))
    guitar_label = font.render("Guitar", True, (200, 200, 100))
    screen.blit(piano_label, (area_rect.x + 20, piano_section_y))
    screen.blit(guitar_label, (area_rect.x + 20, guitar_section_y))
    
    # Only process notes that were actually played
    played_piano_notes = [note for note in song_data if note['played'] and 
                         note.get('Instrument', INSTRUMENTS["PIANO"]) == INSTRUMENTS["PIANO"]]
    
    played_guitar_notes = [note for note in song_data if note['played'] and 
                          note.get('Instrument', INSTRUMENTS["PIANO"]) == INSTRUMENTS["ELECTRO_GUITAR"]]
    
    # Draw piano section
    if not played_piano_notes:
        no_data_text = font.render("No piano beat accuracy data", True, TEXT_COLOR)
        screen.blit(no_data_text, (area_rect.centerx - no_data_text.get_width()//2, 
                                  piano_section_y + piano_section_height//2))
    else:
        # Calculate bar width based on available space
        bar_width = min(40, (area_rect.width - 80) // max(1, len(played_piano_notes)))
        total_bars_width = len(played_piano_notes) * (bar_width + 5)
        start_x = area_rect.x + (area_rect.width - total_bars_width) // 2
        
        # Draw bars for each played piano note
        for i, note in enumerate(played_piano_notes):
            x_pos = start_x + i * (bar_width + 5)
            
            # Calculate the bar height based on beat accuracy
            accuracy = note.get('beat_accuracy', 0)
            color = get_beat_accuracy_color(accuracy)
            
            # Full height represents 100%
            full_height = piano_section_height - 60  # Leave space for labels
            
            # Draw the bar outline
            bar_top = piano_section_y + 40  # Top position of the bar
            pygame.draw.rect(screen, (150, 150, 150), 
                           (x_pos, bar_top, bar_width, full_height), 1)
            
            # Draw the filled portion
            fill_height = int((accuracy / 100) * full_height)
            if fill_height > 0:
                pygame.draw.rect(screen, color, 
                               (x_pos, bar_top + full_height - fill_height, 
                                bar_width, fill_height))
            
            # Add note label
            note_label = font.render(f"{note['Note']}", True, (200, 200, 200))
            note_label_rect = note_label.get_rect(center=(x_pos + bar_width//2, 
                                                        bar_top + full_height + 15))
            screen.blit(note_label, note_label_rect)
            
            # Add accuracy percentage
            acc_label = font.render(f"{accuracy:.0f}%", True, color)
            acc_label_rect = acc_label.get_rect(center=(x_pos + bar_width//2, bar_top - 15))
            screen.blit(acc_label, acc_label_rect)
    
    # Draw guitar section
    if not played_guitar_notes:
        no_data_text = font.render("No guitar beat accuracy data", True, TEXT_COLOR)
        screen.blit(no_data_text, (area_rect.centerx - no_data_text.get_width()//2, 
                                  guitar_section_y + guitar_section_height//2))
    else:
        # Calculate bar width based on available space
        bar_width = min(40, (area_rect.width - 80) // max(1, len(played_guitar_notes)))
        total_bars_width = len(played_guitar_notes) * (bar_width + 5)
        start_x = area_rect.x + (area_rect.width - total_bars_width) // 2
        
        # Draw bars for each played guitar note
        for i, note in enumerate(played_guitar_notes):
            x_pos = start_x + i * (bar_width + 5)
            
            # Calculate the bar height based on beat accuracy
            accuracy = note.get('beat_accuracy', 0)
            color = get_beat_accuracy_color(accuracy)
            
            # Full height represents 100%
            full_height = guitar_section_height - 60  # Leave space for labels
            
            # Draw the bar outline
            bar_top = guitar_section_y + 40  # Top position of the bar
            pygame.draw.rect(screen, (150, 150, 150), 
                           (x_pos, bar_top, bar_width, full_height), 1)
            
            # Draw the filled portion
            fill_height = int((accuracy / 100) * full_height)
            if fill_height > 0:
                pygame.draw.rect(screen, color, 
                               (x_pos, bar_top + full_height - fill_height, 
                                bar_width, fill_height))
            
            # Add note label
            note_label = font.render(f"{note['Note']}", True, (200, 200, 200))
            note_label_rect = note_label.get_rect(center=(x_pos + bar_width//2, 
                                                        bar_top + full_height + 15))
            screen.blit(note_label, note_label_rect)
            
            # Add guitar indicator
            pygame.draw.line(screen, (255, 255, 255), 
                           (x_pos + bar_width//2 - 5, bar_top + full_height + 30), 
                           (x_pos + bar_width//2 + 5, bar_top + full_height + 40), 2)
            pygame.draw.line(screen, (255, 255, 255), 
                           (x_pos + bar_width//2 - 5, bar_top + full_height + 40), 
                           (x_pos + bar_width//2 + 5, bar_top + full_height + 30), 2)
            
            # Add accuracy percentage
            acc_label = font.render(f"{accuracy:.0f}%", True, color)
            acc_label_rect = acc_label.get_rect(center=(x_pos + bar_width//2, bar_top - 15))
            screen.blit(acc_label, acc_label_rect)
    
    # Add a legend
    legend_y = area_rect.y + area_rect.height - 20
    legend_colors = [
        ((0, 255, 0), "Excellent (95-100%)"),
        ((128, 255, 0), "Great (75-94%)"),
        ((255, 255, 0), "Good (50-74%)"),
        ((255, 128, 0), "Poor (25-49%)"),
        ((255, 0, 0), "Bad (0-24%)")
    ]
    
    # Calculate space for each legend item
    legend_width = area_rect.width // min(3, len(legend_colors))
    
    # Draw color swatches and labels (in two rows if needed)
    for i, (color, label) in enumerate(legend_colors):
        row = i // 3  # Split into 2 rows if more than 3 items
        col = i % 3
        
        x_offset = area_rect.x + 30 + col * legend_width
        y_offset = legend_y + row * 25
        
        pygame.draw.rect(screen, color, (x_offset, y_offset, 15, 15))
        text = font.render(label, True, TEXT_COLOR)
        screen.blit(text, (x_offset + 20, y_offset - 5))

def draw_game_over_screen(screen, font, small_font, score, max_score, correct_hits, missed_notes, wrong_notes, song_data, beat_accuracy=0):
    """Draw the game over screen with split-screen accuracy display"""
    screen.fill(BG_COLOR)
    
    # Draw header section
    title = font.render("Done!", True, TEXT_COLOR)
    screen.blit(title, (WIDTH//2 - 80, HEIGHT//10))
    
    final_score = font.render(f"Final Score: {score}/{max_score}", True, TEXT_COLOR)
    screen.blit(final_score, (WIDTH//2 - 100, HEIGHT//7))
    
    stats = font.render(f"Correct: {correct_hits} | Missed: {missed_notes} | Wrong: {wrong_notes}", True, TEXT_COLOR)
    screen.blit(stats, (WIDTH//2 - 200, HEIGHT//7 + 30))
    
    # Calculate and display note accuracy
    note_percentage = int((score / max_score * 100)) if max_score > 0 else 0
    note_grade = "A+" if note_percentage >= 95 else "A" if note_percentage >= 90 else "B" if note_percentage >= 80 else "C" if note_percentage >= 70 else "D" if note_percentage >= 60 else "F"
    note_result = font.render(f"Note Grade: {note_grade} ({note_percentage}%)", True, TEXT_COLOR)
    screen.blit(note_result, (WIDTH//4 - 80, HEIGHT//7 + 60))
    
    # Display beat accuracy grade
    beat_percentage = int(beat_accuracy)
    beat_grade = "A+" if beat_percentage >= 95 else "A" if beat_percentage >= 90 else "B" if beat_percentage >= 80 else "C" if beat_percentage >= 70 else "D" if beat_percentage >= 60 else "F"
    beat_result = font.render(f"Beat Grade: {beat_grade} ({beat_percentage}%)", True, get_beat_accuracy_color(beat_accuracy))
    screen.blit(beat_result, (WIDTH - WIDTH//4 - 80, HEIGHT//7 + 60))
    
    # Create split-screen layout
    # Draw a vertical divider line
    pygame.draw.line(screen, (100, 100, 100), (WIDTH//2, HEIGHT//5), (WIDTH//2, HEIGHT - 50), 1)
    
    # Define the left and right areas for accuracy displays
    left_area = pygame.Rect(0, HEIGHT//4, WIDTH//2, HEIGHT - HEIGHT//4 - 50)
    right_area = pygame.Rect(WIDTH//2, HEIGHT//4, WIDTH//2, HEIGHT - HEIGHT//4 - 50)
    
    # Draw note accuracy on left side
    draw_note_summary(screen, song_data, WIDTH, HEIGHT, left_area, small_font, "Note Accuracy")
    
    # Draw beat accuracy on right side
    draw_beat_accuracy_summary(screen, song_data, right_area, small_font, "Beat Accuracy")

def find_active_notes(song_data, current_time, threshold_distance=40):
    """Find notes near the threshold line"""
    active_notes = []
    for note in song_data:
        if note['played'] or note['missed'] or note.get('wrong', False):
            continue
        
        # Calculate note position
        elapsed_since_appear = current_time - note['appear_time']
        x_pos = WIDTH - int(elapsed_since_appear * NOTE_SPEED)
        
        # Check if near threshold
        if abs(x_pos - THRESHOLD_X) < threshold_distance:
            active_notes.append((note, abs(x_pos - THRESHOLD_X)))
    
    return active_notes
# visualizer.py - Visualization components for the music game

import pygame
import time
from constants import (
    WIDTH, HEIGHT, BG_COLOR, TEXT_COLOR, 
    NOTE_SPEED, THRESHOLD_X, NOTE_POSITIONS, FREQS
)

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
        # Track if the note has been played/missed
        note['played'] = False
        note['missed'] = False
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
        if not note['played'] and not note['missed'] and (x_pos + note_width < THRESHOLD_X - 40):
            note['missed'] = True
            missed_notes_count += 1
    
    return missed_notes_count

def draw_instruction_screen(screen, font, small_font, key_display, note_colors, instruction_box):
    """Draw the instruction screen"""
    pygame.draw.rect(screen, (50, 50, 50), instruction_box)
    pygame.draw.rect(screen, (200, 200, 200), instruction_box, 2)
    
    title = font.render("SlidePlay - Instructions", True, TEXT_COLOR)
    screen.blit(title, (WIDTH//4 + 10, HEIGHT//4 + 10))
    
    y_pos = HEIGHT//4 + 50
    for i, (note_name, y) in enumerate(NOTE_POSITIONS.items()):
        key_name = pygame.key.name(key_display.get(note_name, pygame.K_SPACE)).upper()
        instr = small_font.render(f"Press '{key_name}' for {note_name}", True, note_colors[note_name])
        screen.blit(instr, (WIDTH//4 + 20, y_pos + i*25))
    
    hint = small_font.render("Hit the notes as they cross the vertical line!", True, TEXT_COLOR)
    screen.blit(hint, (WIDTH//4 + 20, y_pos + 180))

def draw_game_screen(screen, font, small_font, key_display, note_colors, current_time, 
                    visible_notes, score, max_score, correct_hits, missed_notes, wrong_notes,
                    last_key_pressed=None, active_note_info=None):
    """Draw the main game screen with notes and UI"""
    screen.fill(BG_COLOR)
    
    # Draw vertical threshold line
    pygame.draw.line(screen, (200, 200, 200), (THRESHOLD_X, 0), (THRESHOLD_X, HEIGHT), 2)
    
    # Draw note labels and key mappings on left side
    for note_name, y_pos in NOTE_POSITIONS.items():
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
        y_pos = NOTE_POSITIONS.get(note_name, HEIGHT // 2)
        note_duration = note_data['Duration']
        
        # Calculate width based on duration
        note_width = int(note_duration * NOTE_SPEED)
        
        # Only draw if at least partially visible
        if x_pos + note_width > 0 and x_pos < WIDTH:
            # Determine color based on status
            if note_data['played']:
                color = (0, 255, 0)  # Green for hit notes
            elif note_data['missed']:
                color = (255, 0, 0)  # Red for missed notes
            else:
                color = note_colors[note_name]
            
            # Draw the note as a rectangle
            pygame.draw.rect(screen, color, (x_pos, y_pos, note_width, 30))
            
            # Add note label
            text_surface = font.render(f"{note_name}{octave}", True, TEXT_COLOR)
            if note_width > 40:  # Only add text if there's enough space
                screen.blit(text_surface, (x_pos + 5, y_pos + 5))
    
    # Display score and stats
    score_text = font.render(f"Score: {score}/{max_score}", True, TEXT_COLOR)
    screen.blit(score_text, (WIDTH - 200, 10))
    
    stats_text = small_font.render(f"Hits: {correct_hits} | Missed: {missed_notes} | Wrong: {wrong_notes}", True, TEXT_COLOR)
    screen.blit(stats_text, (WIDTH - 300, 40))
    
    # Display current time
    time_text = small_font.render(f"Time: {current_time:.2f}s", True, TEXT_COLOR)
    screen.blit(time_text, (10, 10))
    
    # Display debug info
    if last_key_pressed:
        debug_text = small_font.render(f"Last key: {last_key_pressed} | Active note: {active_note_info}", True, (200, 200, 100))
        screen.blit(debug_text, (10, HEIGHT - 20))

def draw_game_over_screen(screen, font, score, max_score, correct_hits, missed_notes, wrong_notes):
    """Draw the game over screen with final score"""
    screen.fill(BG_COLOR)
    
    title = font.render("Game Over!", True, TEXT_COLOR)
    screen.blit(title, (WIDTH//2 - 80, HEIGHT//4))
    
    final_score = font.render(f"Final Score: {score}/{max_score}", True, TEXT_COLOR)
    screen.blit(final_score, (WIDTH//2 - 100, HEIGHT//2 - 50))
    
    stats = font.render(f"Correct: {correct_hits} | Missed: {missed_notes} | Wrong: {wrong_notes}", True, TEXT_COLOR)
    screen.blit(stats, (WIDTH//2 - 200, HEIGHT//2))
    
    percentage = int((score / max_score) * 100) if max_score > 0 else 0
    grade = "A+" if percentage >= 95 else "A" if percentage >= 90 else "B" if percentage >= 80 else "C" if percentage >= 70 else "D" if percentage >= 60 else "F"
    result = font.render(f"Grade: {grade} ({percentage}%)", True, TEXT_COLOR)
    screen.blit(result, (WIDTH//2 - 80, HEIGHT//2 + 50))

def find_active_notes(song_data, current_time, threshold_distance=40):
    """Find notes near the threshold line"""
    active_notes = []
    for note in song_data:
        if note['played'] or note['missed']:
            continue
        
        # Calculate note position
        elapsed_since_appear = current_time - note['appear_time']
        x_pos = WIDTH - int(elapsed_since_appear * NOTE_SPEED)
        
        # Check if near threshold
        if abs(x_pos - THRESHOLD_X) < threshold_distance:
            active_notes.append((note, abs(x_pos - THRESHOLD_X)))
    
    return active_notes
# music_creation.py - A simple interface for creating music pieces
# Uses single-button navigation to select notes, length, and position

import pygame
import numpy as np
import time
import os
from constants import (
    WIDTH, HEIGHT, BG_COLOR, TEXT_COLOR, FREQS, 
    NOTE_POSITIONS, NOTE_SPEED, THRESHOLD_X, KEY_MAPPINGS,
    INSTRUMENTS, INSTRUMENT_NAMES
)
from sound_engine import play_note, play_error_sound
from visualizer import calculate_note_colors

# Creation mode states
NOTE_SELECTION = 0
LENGTH_SELECTION = 1
POSITION_SELECTION = 2

# Available note lengths
NOTE_LENGTHS = [0.5, 1, 2, 4]  # in seconds

# Define separate positions for piano and guitar notes in creation mode
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

class MusicCreator:
    def __init__(self):
        # Initialize pygame
        pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        
        # Set up display
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SlidePlay - Music Creation Mode")
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.clock = pygame.time.Clock()
        
        # Generate note colors
        self.note_colors = calculate_note_colors()
        
        # Composition data
        self.composition = []
        
        # Current state
        self.state = NOTE_SELECTION
        self.selected_note = None
        self.selected_octave = 4  # Default octave
        self.length_index = 0
        self.position = 0.0
        
        # Instrument selection (default to piano)
        self.selected_instrument = INSTRUMENTS["PIANO"]
        
        # Keep track of the maximum position for display purposes
        self.max_position = 10.0  # Initial timeline length
        
        # Key to note mapping
        self.key_to_note = KEY_MAPPINGS
        
        # Time conversions
        self.position_increment = 0.5  # Position increments by 0.5 seconds
    
    def save_composition(self, filename="track.txt"):
        """Save the composition to a file"""
        if not self.composition:
            return False
        
        # Sort notes by position
        sorted_notes = sorted(self.composition, key=lambda x: x['Start Time'])
        
        # Format each note as per the expected format
        formatted_notes = []
        for note in sorted_notes:
            # Include instrument in the saved format
            formatted_note = f"{note['Note']}{note['Octave']}-{note['Start Time']}-{note['Duration']}-{note['Volume']}-{note['Instrument']}"
            formatted_notes.append(formatted_note)
        
        # Join with spaces
        output = " ".join(formatted_notes)
        
        # Write to file
        try:
            with open(filename, 'w') as file:
                file.write(output)
            return True
        except Exception as e:
            print(f"Error saving composition: {e}")
            return False
    
    def add_note(self):
        """Add the current note to the composition"""
        if self.selected_note is None:
            return
        
        note_data = {
            'Note': self.selected_note,
            'Octave': self.selected_octave,
            'Start Time': self.position,
            'Duration': NOTE_LENGTHS[self.length_index],
            'Volume': 100,  # Fixed volume for now
            'Instrument': self.selected_instrument  # Add instrument information
        }
        
        # Check if the position extends beyond current max
        new_end_time = self.position + NOTE_LENGTHS[self.length_index]
        if new_end_time > self.max_position:
            self.max_position = new_end_time + 2  # Add some extra space
        
        # Add the note to the composition
        self.composition.append(note_data)
        
        # Play the note once with the selected instrument
        play_note(
            self.selected_note, 
            self.selected_octave, 
            NOTE_LENGTHS[self.length_index], 
            100,  # volume
            0.5,  # center pan
            self.selected_instrument  # instrument
        )
        
        # Reset state for next note
        self.state = NOTE_SELECTION
        self.selected_note = None
    
    def toggle_instrument(self):
        """Toggle between available instruments"""
        if self.selected_instrument == INSTRUMENTS["PIANO"]:
            self.selected_instrument = INSTRUMENTS["ELECTRO_GUITAR"]
        else:
            self.selected_instrument = INSTRUMENTS["PIANO"]
    
    def handle_events(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                # Escape key to exit
                if event.key == pygame.K_ESCAPE:
                    return False
                
                # Save functionality
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    saved = self.save_composition()
                    print(f"Composition {'saved to track.txt' if saved else 'not saved - no notes'}")
                
                # Delete key during note creation - cancel and go back to note selection
                if event.key == pygame.K_BACKSPACE or event.key == pygame.K_DELETE:
                    if self.state == LENGTH_SELECTION or self.state == POSITION_SELECTION:
                        # Cancel the current note and return to note selection
                        self.state = NOTE_SELECTION
                        self.selected_note = None
                    elif self.state == NOTE_SELECTION and self.composition:
                        # Delete the last note from the composition
                        self.composition.pop()
                        # Set position to 0 to follow the requirement
                        self.position = 0.0
                
                # State-specific handling
                if self.state == NOTE_SELECTION:
                    # Toggle instrument with A key before note selection
                    if event.key == pygame.K_a:
                        self.toggle_instrument()
                        # Play a sample note with the new instrument
                        play_note("Do", 4, 0.3, 100, 0.5, self.selected_instrument)
                        
                    # Check if a note key was pressed
                    elif event.key in self.key_to_note:
                        self.selected_note = self.key_to_note[event.key]
                        
                        # Play the note briefly with the selected instrument
                        play_note(self.selected_note, self.selected_octave, 0.3, 100, 0.5, self.selected_instrument)
                        
                        # Move to length selection
                        self.state = LENGTH_SELECTION
                    
                    # Octave selection
                    elif event.key == pygame.K_UP:
                        self.selected_octave = min(7, self.selected_octave + 1)
                    elif event.key == pygame.K_DOWN:
                        self.selected_octave = max(1, self.selected_octave - 1)
                
                # The 'a' key is used for navigation in length and position selection
                elif event.key == pygame.K_a:
                    if self.state == LENGTH_SELECTION:
                        # Cycle through available lengths
                        self.length_index = (self.length_index + 1) % len(NOTE_LENGTHS)
                        
                        # Preview the note with this length
                        if self.selected_note:
                            play_note(
                                self.selected_note, 
                                self.selected_octave, 
                                NOTE_LENGTHS[self.length_index], 
                                100, 
                                0.5,
                                self.selected_instrument
                            )
                            
                    elif self.state == POSITION_SELECTION:
                        # Increment position
                        self.position += self.position_increment
                        
                        # Check for collisions with existing notes
                        for note in self.composition:
                            if (abs(note['Start Time'] - self.position) < 0.1 and 
                                note['Note'] == self.selected_note):
                                # Skip this position
                                self.position += self.position_increment
                
                # Confirm current selection and move to next state
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if self.state == LENGTH_SELECTION:
                        # Reset position to 0 when entering position selection
                        self.position = 0.0
                        self.state = POSITION_SELECTION
                    elif self.state == POSITION_SELECTION:
                        self.add_note()
        
        return True
    
    def get_note_y_position(self, note_name, instrument):
        """Get the Y position for a note based on its name and instrument"""
        if instrument == INSTRUMENTS["PIANO"]:
            return PIANO_NOTE_POSITIONS.get(note_name, 190)  # Default position if note not found
        else:  # ELECTRO_GUITAR
            return GUITAR_NOTE_POSITIONS.get(note_name, 540)  # Default position if note not found
    
    def draw_section_divider(self):
        """Draw a divider between piano and guitar sections with labels"""
        # Draw horizontal divider line
        pygame.draw.line(self.screen, (100, 100, 100), (0, SECTION_DIVIDER_Y), (WIDTH, SECTION_DIVIDER_Y), 2)
        
        # Draw section labels
        piano_label = self.font.render("Piano", True, (200, 200, 200))
        guitar_label = self.font.render("Electro Guitar", True, (200, 200, 100))
        
        # Position labels on the left side
        self.screen.blit(piano_label, (20, SECTION_DIVIDER_Y - 40))
        self.screen.blit(guitar_label, (20, SECTION_DIVIDER_Y + 10))
        
        # Add highlight for current instrument section
        highlight_color = (70, 70, 100, 128)  # Semi-transparent highlight
        if self.selected_instrument == INSTRUMENTS["PIANO"]:
            # Highlight piano section
            pygame.draw.rect(self.screen, highlight_color, (0, 0, WIDTH, SECTION_DIVIDER_Y), 2)
            active_text = self.small_font.render("Current active section", True, (200, 200, 200))
            self.screen.blit(active_text, (WIDTH - 200, SECTION_DIVIDER_Y - 40))
        else:
            # Highlight guitar section
            pygame.draw.rect(self.screen, highlight_color, (0, SECTION_DIVIDER_Y, WIDTH, HEIGHT - SECTION_DIVIDER_Y), 2)
            active_text = self.small_font.render("Current active section", True, (200, 200, 100))
            self.screen.blit(active_text, (WIDTH - 200, SECTION_DIVIDER_Y + 10))
    
    def draw_note_ribbon(self):
        """Draw a ribbon showing all notes in the composition"""
        # Sort notes by position
        sorted_notes = sorted(self.composition, key=lambda x: x['Start Time'])
        
        # Draw timeline
        timeline_y = HEIGHT - 100
        timeline_start = 50
        timeline_end = WIDTH - 50
        timeline_length = timeline_end - timeline_start
        
        # Calculate scale: pixels per second
        pixels_per_second = timeline_length / self.max_position
        
        # Draw the timeline
        pygame.draw.line(self.screen, (150, 150, 150), 
                         (timeline_start, timeline_y), 
                         (timeline_end, timeline_y), 2)
        
        # Draw time markers
        for i in range(0, int(self.max_position) + 1, 1):
            marker_x = timeline_start + i * pixels_per_second
            pygame.draw.line(self.screen, (100, 100, 100),
                           (marker_x, timeline_y - 5),
                           (marker_x, timeline_y + 5), 1)
            
            # Add time labels for whole seconds
            if i % 2 == 0:  # Only show every other second to avoid crowding
                time_label = self.small_font.render(f"{i}s", True, (150, 150, 150))
                self.screen.blit(time_label, (marker_x - 10, timeline_y + 10))
        
        # Draw each note as a colored rectangle
        note_height = 20
        for note in sorted_notes:
            start_x = timeline_start + note['Start Time'] * pixels_per_second
            width = note['Duration'] * pixels_per_second
            
            # Get the note and instrument
            note_name = note['Note']
            instrument = note.get('Instrument', INSTRUMENTS["PIANO"])
            
            # Y position based on note and instrument
            y_pos = self.get_note_y_position(note_name, instrument)
            
            # Get base color
            base_color = self.note_colors[note_name]
            
            # Determine color based on instrument
            if instrument == INSTRUMENTS["ELECTRO_GUITAR"]:
                # Electro guitar gets a more intense color
                color = pygame.Color(
                    min(255, base_color.r + 40),
                    base_color.g,
                    min(255, base_color.b + 40)
                )
                
                # Add a small guitar icon or indicator
                pygame.draw.polygon(self.screen, (255, 255, 255), 
                                  [(start_x + 2, y_pos + 2), 
                                   (start_x + 7, y_pos + 10), 
                                   (start_x + 2, y_pos + 18)])
            else:
                color = base_color
            
            # Draw note rectangle
            pygame.draw.rect(self.screen, color, (start_x, y_pos, width, note_height))
            
            # Add note label
            label = self.small_font.render(f"{note['Note']}{note['Octave']}", True, TEXT_COLOR)
            if width > label.get_width() + 10:  # Only show label if enough space
                self.screen.blit(label, (start_x + 5, y_pos + 2))
        
        # Draw position marker for current position
        if self.state == POSITION_SELECTION:
            marker_x = timeline_start + self.position * pixels_per_second
            
            # Draw marker at appropriate height based on selected instrument
            if self.selected_instrument == INSTRUMENTS["PIANO"]:
                marker_y1 = PIANO_NOTE_POSITIONS[self.selected_note] - 30
                marker_y2 = PIANO_NOTE_POSITIONS[self.selected_note] + 50
            else:
                marker_y1 = GUITAR_NOTE_POSITIONS[self.selected_note] - 30
                marker_y2 = GUITAR_NOTE_POSITIONS[self.selected_note] + 50
                
            pygame.draw.line(self.screen, (255, 255, 0), 
                            (marker_x, marker_y1), 
                            (marker_x, marker_y2), 2)
    
    def draw_keyboard_guide(self):
        """Draw a guide showing which keys correspond to which notes"""
        # Draw piano section key guide
        for i, (note_name, y_pos) in enumerate(PIANO_NOTE_POSITIONS.items()):
            # Find the key that maps to this note
            key_name = None
            for key, note in self.key_to_note.items():
                if note == note_name:
                    key_name = pygame.key.name(key).upper()
                    break
            
            if key_name:
                # Draw key name for piano section
                color = self.note_colors[note_name]
                if self.selected_instrument == INSTRUMENTS["PIANO"] and self.selected_note == note_name:
                    # Highlight selected note in current instrument
                    color = pygame.Color(255, 255, 100)
                key_text = self.font.render(f"Press '{key_name}' for {note_name}", True, color)
                self.screen.blit(key_text, (50, y_pos))
        
        # Draw guitar section key guide
        for i, (note_name, y_pos) in enumerate(GUITAR_NOTE_POSITIONS.items()):
            # Find the key that maps to this note
            key_name = None
            for key, note in self.key_to_note.items():
                if note == note_name:
                    key_name = pygame.key.name(key).upper()
                    break
            
            if key_name:
                # Draw key name for guitar section
                color = self.note_colors[note_name]
                if self.selected_instrument == INSTRUMENTS["ELECTRO_GUITAR"] and self.selected_note == note_name:
                    # Highlight selected note in current instrument
                    color = pygame.Color(255, 255, 100)
                key_text = self.font.render(f"Press '{key_name}' for {note_name}", True, color)
                self.screen.blit(key_text, (50, y_pos))
    
    def draw_state_info(self):
        """Draw information about the current state and selection"""
        # Always show current instrument
        instrument_text = self.font.render(f"Instrument: {INSTRUMENT_NAMES[self.selected_instrument]}", True, (200, 200, 100))
        self.screen.blit(instrument_text, (WIDTH - 300, 20))
        
        if self.state == NOTE_SELECTION:
            state_text = self.font.render("Select a note (number keys)", True, TEXT_COLOR)
            self.screen.blit(state_text, (WIDTH//2 - 150, 20))
            
            instrument_hint = self.small_font.render("Press 'A' to toggle instrument", True, (200, 200, 100))
            self.screen.blit(instrument_hint, (WIDTH//2 - 150, 60))
            
            octave_text = self.font.render(f"Current Octave: {self.selected_octave} (↑/↓ to change)", True, TEXT_COLOR)
            self.screen.blit(octave_text, (WIDTH//2 - 150, 90))
            
        elif self.state == LENGTH_SELECTION:
            state_text = self.font.render(f"Select note length: {NOTE_LENGTHS[self.length_index]}s", True, TEXT_COLOR)
            self.screen.blit(state_text, (WIDTH//2 - 150, 20))
            
            hint_text = self.small_font.render("Press 'A' to cycle through lengths, SPACE to confirm", True, TEXT_COLOR)
            self.screen.blit(hint_text, (WIDTH//2 - 200, 60))
            
            cancel_text = self.small_font.render("Press BACKSPACE or DELETE to cancel", True, TEXT_COLOR)
            self.screen.blit(cancel_text, (WIDTH//2 - 150, 90))
            
            # Show the different length options
            options_y = 130
            for i, length in enumerate(NOTE_LENGTHS):
                color = (255, 255, 0) if i == self.length_index else (150, 150, 150)
                option_text = self.font.render(f"{length}s", True, color)
                self.screen.blit(option_text, (50 + i * 100, options_y))
            
        elif self.state == POSITION_SELECTION:
            state_text = self.font.render(f"Select position: {self.position:.1f}s", True, TEXT_COLOR)
            self.screen.blit(state_text, (WIDTH//2 - 150, 20))
            
            hint_text = self.small_font.render("Press 'A' to move position, SPACE to add note", True, TEXT_COLOR)
            self.screen.blit(hint_text, (WIDTH//2 - 200, 60))
            
            cancel_text = self.small_font.render("Press BACKSPACE or DELETE to cancel", True, TEXT_COLOR)
            self.screen.blit(cancel_text, (WIDTH//2 - 150, 90))
    
    def draw_controls_guide(self):
        """Draw a guide for the controls"""
        controls_y = HEIGHT - 40
        controls_text = self.small_font.render(
            "BACKSPACE: Delete last note | CTRL+S: Save | ESC: Exit", 
            True, (200, 200, 200)
        )
        self.screen.blit(controls_text, (WIDTH//2 - controls_text.get_width()//2, controls_y))
    
    def draw(self):
        """Draw the interface"""
        # Clear screen
        self.screen.fill(BG_COLOR)
        
        # Draw section divider
        self.draw_section_divider()
        
        # Draw keyboard guide
        self.draw_keyboard_guide()
        
        # Draw state-specific information
        self.draw_state_info()
        
        # Draw the note ribbon
        self.draw_note_ribbon()
        
        # Draw controls guide
        self.draw_controls_guide()
        
        # Update display
        pygame.display.flip()
    
    def run(self):
        """Main loop"""
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(60)
        
        # Clean up
        pygame.quit()

def main():
    creator = MusicCreator()
    creator.run()

if __name__ == "__main__":
    main()
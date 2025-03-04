# slide.py - Game logic for the SlidePlay music game

import pygame
import time
from constants import KEY_MAPPINGS, WIDTH, HEIGHT, BG_COLOR, FREQS
from sound_engine import play_note, play_error_sound
from visualizer import (
    init_pygame_window, calculate_note_colors, prepare_song_data,
    get_visible_notes, update_missed_notes, find_active_notes,
    draw_instruction_screen, draw_game_screen, draw_game_over_screen
)

class SlidePlayGame:
    def __init__(self, song_data, octave_range=None):
        self.song_data = prepare_song_data(song_data)
        self.max_score = len(song_data)
        self.score = 0
        self.correct_hits = 0
        self.missed_notes = 0
        self.wrong_notes = 0
        self.last_key_pressed = None
        self.active_note_info = None
        
        # Calculate last note time for ending the game
        self.last_note_time = max([n['Start Time'] + n['Duration'] for n in song_data]) if song_data else 0
        
        # Calculate octave range for panning
        if octave_range is None:
            all_octaves = [note['Octave'] for note in song_data]
            self.min_octave = min(all_octaves)
            self.max_octave = max(all_octaves)
            self.octave_range = max(1, self.max_octave - self.min_octave)
        else:
            self.min_octave, self.max_octave = octave_range
            self.octave_range = max(1, self.max_octave - self.min_octave)
        
        # Initialize pygame
        self.screen, self.font, self.small_font, self.clock = init_pygame_window()
        self.note_colors = calculate_note_colors()
        self.key_display = {note: key for key, note in KEY_MAPPINGS.items()}

    def process_key_event(self, event, current_time):
        """Process a key press event during gameplay"""
        if event.key in KEY_MAPPINGS:
            played_note = KEY_MAPPINGS[event.key]
            self.last_key_pressed = played_note
            
            # Find notes near the threshold
            active_notes = find_active_notes(self.song_data, current_time)
            
            if active_notes:
                # Get the closest note to the threshold
                closest_note, distance = min(active_notes, key=lambda x: x[1])
                self.active_note_info = f"{closest_note['Note']}, {distance}px from threshold"
                
                # Check if the correct note was played (ignoring octave)
                if closest_note['Note'] == played_note:
                    # Correct note!
                    octave = closest_note['Octave']
                    duration = closest_note['Duration']
                    volume = closest_note['Volume']
                    
                    # Calculate panning
                    if self.octave_range > 1:
                        pan = 0.1 + 0.8 * ((octave - self.min_octave) / self.octave_range)
                    else:
                        note_index = list(FREQS.keys()).index(played_note)
                        pan = 0.1 + 0.8 * (note_index / (len(FREQS) - 1))
                    
                    play_note(played_note, octave, duration, volume, pan)
                    closest_note['played'] = True
                    self.score += 1
                    self.correct_hits += 1
                else:
                    # Wrong note!
                    play_error_sound()
                    self.wrong_notes += 1
            else:
                # No active notes - wrong timing
                self.active_note_info = "No notes near threshold"
                play_error_sound()
                self.wrong_notes += 1
        
        # Allow ESC to exit
        if event.key == pygame.K_ESCAPE:
            return False
        
        return True

    def run(self):
        """Run the main game loop"""
        # Show instructions for 3 seconds before starting
        show_instructions = True
        instruction_end_time = time.time() + 3
        
        # Start game time
        start_time = time.time()
        running = True
        
        while running:
            current_time = time.time() - start_time
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                
                if event.type == pygame.KEYDOWN:
                    if show_instructions:
                        show_instructions = False
                        start_time = time.time()  # Reset time after instructions
                    else:
                        running = self.process_key_event(event, current_time)
            
            # Show instructions if needed
            if show_instructions:
                if time.time() < instruction_end_time:
                    self.screen.fill(BG_COLOR)
                    instruction_box = pygame.Rect(WIDTH//4, HEIGHT//4, WIDTH//2, HEIGHT//2)
                    draw_instruction_screen(
                        self.screen, self.font, self.small_font, 
                        self.key_display, self.note_colors, instruction_box
                    )
                    pygame.display.flip()
                    self.clock.tick(60)
                    continue
                else:
                    show_instructions = False
                    start_time = time.time()  # Reset time after instructions
            
            # Get visible notes and update missed notes
            visible_notes = get_visible_notes(self.song_data, current_time)
            self.missed_notes = update_missed_notes(visible_notes, current_time, self.missed_notes)
            
            # Draw game screen
            draw_game_screen(
                self.screen, self.font, self.small_font, self.key_display,
                self.note_colors, current_time, visible_notes, 
                self.score, self.max_score, self.correct_hits, 
                self.missed_notes, self.wrong_notes,
                self.last_key_pressed, self.active_note_info
            )
            
            pygame.display.flip()
            self.clock.tick(60)
            
            # End if all notes have been played/missed and sufficient time has elapsed
            all_notes_handled = all(note['played'] or note['missed'] for note in self.song_data)
            if all_notes_handled and current_time > self.last_note_time + 2:
                # Show final score
                self.show_game_over_screen()
                running = False
        
        pygame.quit()

    def show_game_over_screen(self):
        """Show the game over screen with final score"""
        final_screen = True
        final_start = time.time()
        
        while final_screen and time.time() - final_start < 5:
            draw_game_over_screen(
                self.screen, self.font, 
                self.score, self.max_score, 
                self.correct_hits, self.missed_notes, self.wrong_notes
            )
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    final_screen = False
            
            pygame.display.flip()
            self.clock.tick(60)
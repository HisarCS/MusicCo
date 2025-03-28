# slide.py - Enhanced game logic for the SlidePlay music game with pre-play feature

import pygame
import time
from constants import KEY_MAPPINGS, WIDTH, HEIGHT, BG_COLOR, FREQS, TEXT_COLOR, INSTRUMENTS, INSTRUMENT_NAMES
from sound_engine import play_note, play_error_sound
from visualizer import (
    init_pygame_window, calculate_note_colors, prepare_song_data,
    get_visible_notes, update_missed_notes, find_active_notes,
    draw_instruction_screen, draw_game_screen, draw_game_over_screen, draw_pre_play_screen,
    get_note_y_position, PIANO_NOTE_POSITIONS, GUITAR_NOTE_POSITIONS, SECTION_DIVIDER_Y
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
        
        # Default instrument - now can be overridden per note or globally
        self.current_instrument = INSTRUMENTS["PIANO"]
        
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
        
        # Track accuracy stats
        self.note_accuracy = {}  # Dictionary to store accuracy for each note type
        
        # Beat accuracy tracking
        self.beat_accuracy_total = 0  # Total percentage accuracy of all notes
        self.beat_accuracy_count = 0  # Number of notes with beat accuracy measured
        self.currently_playing = {}  # Track currently pressed keys and their start times
        self.key_to_note_map = {}  # Map keys to active notes they're playing
        
        # Track if we're using instrument override
        self.override_instruments = False

    def toggle_instrument(self):
        """Toggle between available instruments"""
        if self.current_instrument == INSTRUMENTS["PIANO"]:
            self.current_instrument = INSTRUMENTS["ELECTRO_GUITAR"]
        else:
            self.current_instrument = INSTRUMENTS["PIANO"]
            
        # Set the override flag
        self.override_instruments = True
        
        # Play a sample note with the new instrument
        play_note("Do", 4, 0.3, 100, 0.5, self.current_instrument)

    def calculate_pan(self, note_name, octave):
        """Calculate pan value based on note pitch"""
        if self.octave_range > 1:
            return 0.1 + 0.8 * ((octave - self.min_octave) / self.octave_range)
        else:
            note_index = list(FREQS.keys()).index(note_name)
            return 0.1 + 0.8 * (note_index / (len(FREQS) - 1))

    def process_key_event(self, event, current_time):
        """Process a key press event during gameplay"""
        # Handle W key for instrument toggle
        if event.type == pygame.KEYDOWN and event.key == pygame.K_w:
            self.toggle_instrument()
            return
            
        if event.type == pygame.KEYDOWN and event.key in KEY_MAPPINGS:
            played_note = KEY_MAPPINGS[event.key]
            self.last_key_pressed = played_note
            
            # Mark the time this key was pressed
            self.currently_playing[event.key] = {
                'start_time': current_time,
                'note': played_note
            }
            
            # Find notes near the threshold
            active_notes = find_active_notes(self.song_data, current_time)
            
            if active_notes:
                # Filter active notes by instrument type if we're overriding
                if self.override_instruments:
                    filtered_notes = []
                    for note, distance in active_notes:
                        # If we're using instrument override, filter by current instrument
                        # Otherwise, keep all notes
                        if self.override_instruments:
                            # Allow matching with any instrument type if all notes have passed
                            # and we only have notes with wrong instrument type left
                            if all((n[0].get('Instrument', INSTRUMENTS["PIANO"]) != self.current_instrument) 
                                  for n in active_notes):
                                filtered_notes.append((note, distance))
                            elif note.get('Instrument', INSTRUMENTS["PIANO"]) == self.current_instrument:
                                filtered_notes.append((note, distance))
                        else:
                            filtered_notes.append((note, distance))
                    
                    # Only use filtered notes if we actually found any
                    if filtered_notes:
                        active_notes = filtered_notes
                
                # Get the closest note to the threshold
                closest_note, distance = min(active_notes, key=lambda x: x[1])
                self.active_note_info = f"{closest_note['Note']}, {distance}px from threshold"
                
                # Check if the correct note was played (ignore octave for now)
                if closest_note['Note'] == played_note:
                    # Correct note!
                    octave = closest_note['Octave']
                    duration = closest_note['Duration']
                    volume = closest_note['Volume']
                    
                    # Calculate panning
                    pan = self.calculate_pan(played_note, octave)
                    
                    # Determine which instrument to use
                    if self.override_instruments:
                        # Use the globally selected instrument
                        instrument = self.current_instrument
                    else:
                        # Use the instrument specified in the note, or default to piano
                        instrument = closest_note.get('Instrument', INSTRUMENTS["PIANO"])
                    
                    play_note(played_note, octave, duration, volume, pan, instrument)
                    closest_note['played'] = True
                    self.score += 1
                    self.correct_hits += 1
                    
                    # Map this key to the note for beat accuracy tracking
                    self.key_to_note_map[event.key] = closest_note
                    # Initialize beat accuracy for this note
                    closest_note['expected_duration'] = duration
                    closest_note['actual_duration'] = 0  # Will be updated on key release
                    closest_note['beat_accuracy'] = 0    # Will be calculated on key release
                    
                    # Update accuracy stats for this note
                    if played_note not in self.note_accuracy:
                        self.note_accuracy[played_note] = {'correct': 0, 'wrong': 0}
                    self.note_accuracy[played_note]['correct'] += 1
                else:
                    # Wrong note!
                    closest_note['wrong'] = True  # Mark the note as wrong
                    play_error_sound()
                    self.wrong_notes += 1
                    
                    # Update accuracy stats for the played note
                    if played_note not in self.note_accuracy:
                        self.note_accuracy[played_note] = {'correct': 0, 'wrong': 0}
                    self.note_accuracy[played_note]['wrong'] += 1
            else:
                # No active notes - wrong timing
                self.active_note_info = "No notes near threshold"
                play_error_sound()
                self.wrong_notes += 1
                
                # Update accuracy stats for the played note
                if played_note not in self.note_accuracy:
                    self.note_accuracy[played_note] = {'correct': 0, 'wrong': 0}
                self.note_accuracy[played_note]['wrong'] += 1
        
        elif event.type == pygame.KEYUP and event.key in KEY_MAPPINGS:
            # Key release - calculate beat accuracy if this key was playing a note
            if event.key in self.currently_playing:
                press_data = self.currently_playing[event.key]
                press_duration = current_time - press_data['start_time']
                
                # If this key was mapped to a note, calculate beat accuracy
                if event.key in self.key_to_note_map:
                    note = self.key_to_note_map[event.key]
                    expected_duration = note['expected_duration']
                    
                    # Calculate accuracy as a percentage (how close to the expected duration)
                    # If held longer than expected, still count as 100%
                    if press_duration >= expected_duration:
                        accuracy = 100.0
                    else:
                        accuracy = (press_duration / expected_duration) * 100.0
                    
                    # Update the note data with beat accuracy info
                    note['actual_duration'] = press_duration
                    note['beat_accuracy'] = accuracy
                    
                    # Update overall beat accuracy stats
                    self.beat_accuracy_total += accuracy
                    self.beat_accuracy_count += 1
                    
                    # Clean up tracking dictionaries
                    del self.key_to_note_map[event.key]
                
                # Remove from currently playing
                del self.currently_playing[event.key]
    
    def get_beat_accuracy(self):
        """Get the average beat accuracy percentage"""
        if self.beat_accuracy_count > 0:
            return self.beat_accuracy_total / self.beat_accuracy_count
        return 0.0
        
    def show_instructions(self, wait_time=5):  # Increased time to read the now more complex instructions
        """Show instructions for a specified time"""
        instruction_end_time = time.time() + wait_time
        instruction_box = pygame.Rect(WIDTH//4, HEIGHT//4, WIDTH//2, HEIGHT//2)
        
        while time.time() < instruction_end_time:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    return True
            
            self.screen.fill(BG_COLOR)
            draw_instruction_screen(
                self.screen, self.font, self.small_font,
                self.key_display, self.note_colors, instruction_box
            )
            
            # Add "Press SPACE to skip" text
            skip_text = self.small_font.render("Press SPACE to skip", True, (200, 200, 200))
            self.screen.blit(skip_text, (WIDTH//2 - skip_text.get_width()//2, HEIGHT//4 + HEIGHT//2 - 30))
            
            pygame.display.flip()
            self.clock.tick(60)
        
        return True
    
    def run_pre_play(self):
        """Run the pre-play demonstration of the song"""
        # Sort song data by start time to play notes in order
        sorted_notes = sorted(self.song_data, key=lambda x: x['Start Time'])
        
        # Reset all notes just in case
        for note in sorted_notes:
            note['played'] = False
            note['missed'] = False
            note['wrong'] = False
            
        # Display pre-play message
        self.screen.fill(BG_COLOR)
        pre_play_text = self.font.render("Pre-Play Demonstration", True, TEXT_COLOR)
        self.screen.blit(pre_play_text, (WIDTH//2 - pre_play_text.get_width()//2, HEIGHT//4))
        
        listen_text = self.small_font.render("Listen to how the song should sound", True, TEXT_COLOR)
        self.screen.blit(listen_text, (WIDTH//2 - listen_text.get_width()//2, HEIGHT//4 + 40))
        
        layout_text = self.small_font.render("Piano notes shown on top, Electro Guitar notes on bottom", True, (200, 200, 100))
        self.screen.blit(layout_text, (WIDTH//2 - layout_text.get_width()//2, HEIGHT//4 + 70))
        
        skip_text = self.small_font.render("Press SPACE to skip", True, (200, 200, 200))
        self.screen.blit(skip_text, (WIDTH//2 - skip_text.get_width()//2, HEIGHT - 50))
        
        pygame.display.flip()
        time.sleep(1)  # Brief pause before starting
        
        # Start the pre-play
        start_time = time.time()
        running = True
        last_played_index = -1
        
        while running:
            current_time = time.time() - start_time
            
            # Handle events (allow skipping)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    return True
            
            # Find notes that should be played at this time
            for i, note in enumerate(sorted_notes):
                if i > last_played_index and current_time >= note['Start Time']:
                    # Play this note
                    play_note(
                        note['Note'], 
                        note['Octave'], 
                        note['Duration'], 
                        note['Volume'], 
                        self.calculate_pan(note['Note'], note['Octave']),
                        note.get('Instrument', INSTRUMENTS["PIANO"])  # Use note's instrument or default to piano
                    )
                    note['demo_played'] = True
                    last_played_index = i
            
            # Update display
            visible_notes = get_visible_notes(sorted_notes, current_time)
            draw_pre_play_screen(
                self.screen, self.font, self.small_font, 
                self.note_colors, current_time, visible_notes,
                last_played_index  # Pass the index of the last played note
            )
            
            # Display current instrument
            if self.override_instruments:
                instr_text = self.font.render(
                    f"Current Instrument: {INSTRUMENT_NAMES[self.current_instrument]}", 
                    True, (200, 200, 100)
                )
                self.screen.blit(instr_text, (WIDTH - 400, 10))
            
            pygame.display.flip()
            self.clock.tick(60)
            
            # Check if we've finished playing all notes
            if current_time > self.last_note_time + 1:
                break
        
        # Show a "Ready to play?" message
        self.screen.fill(BG_COLOR)
        ready_text = self.font.render("Ready to play?", True, TEXT_COLOR)
        self.screen.blit(ready_text, (WIDTH//2 - ready_text.get_width()//2, HEIGHT//2 - 60))
        
        # Add instrument toggle reminder
        instr_text = self.font.render(
            f"Current Instrument: {INSTRUMENT_NAMES[self.current_instrument]}", 
            True, (200, 200, 100)
        )
        self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, HEIGHT//2 - 20))
        
        instr_hint = self.small_font.render(
            "Press 'W' during gameplay to toggle instrument", 
            True, (200, 200, 100)
        )
        self.screen.blit(instr_hint, (WIDTH//2 - instr_hint.get_width()//2, HEIGHT//2 + 10))
        
        layout_text = self.small_font.render(
            "Piano notes on top, Electro Guitar notes on bottom", 
            True, (200, 200, 100)
        )
        self.screen.blit(layout_text, (WIDTH//2 - layout_text.get_width()//2, HEIGHT//2 + 40))
        
        start_text = self.small_font.render("Press SPACE to start", True, (200, 200, 200))
        self.screen.blit(start_text, (WIDTH//2 - start_text.get_width()//2, HEIGHT//2 + 80))
        
        pygame.display.flip()
        
        # Wait for user to start
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        waiting = False
                    # Allow instrument toggle even in the ready screen
                    elif event.key == pygame.K_w:
                        self.toggle_instrument()
                        
                        # Update the instrument display
                        self.screen.fill(BG_COLOR)
                        ready_text = self.font.render("Ready to play?", True, TEXT_COLOR)
                        self.screen.blit(ready_text, (WIDTH//2 - ready_text.get_width()//2, HEIGHT//2 - 60))
                        
                        instr_text = self.font.render(
                            f"Current Instrument: {INSTRUMENT_NAMES[self.current_instrument]}", 
                            True, (200, 200, 100)
                        )
                        self.screen.blit(instr_text, (WIDTH//2 - instr_text.get_width()//2, HEIGHT//2 - 20))
                        
                        instr_hint = self.small_font.render(
                            "Press 'W' during gameplay to toggle instrument", 
                            True, (200, 200, 100)
                        )
                        self.screen.blit(instr_hint, (WIDTH//2 - instr_hint.get_width()//2, HEIGHT//2 + 10))
                        
                        layout_text = self.small_font.render(
                            "Piano notes on top, Electro Guitar notes on bottom", 
                            True, (200, 200, 100)
                        )
                        self.screen.blit(layout_text, (WIDTH//2 - layout_text.get_width()//2, HEIGHT//2 + 40))
                        
                        start_text = self.small_font.render("Press SPACE to start", True, (200, 200, 200))
                        self.screen.blit(start_text, (WIDTH//2 - start_text.get_width()//2, HEIGHT//2 + 80))
                        
                        pygame.display.flip()
            
            self.clock.tick(60)
        
        # Reset all the note statuses for the actual gameplay
        for note in self.song_data:
            note['played'] = False
            note['missed'] = False
            note['wrong'] = False
            if 'demo_played' in note:
                del note['demo_played']
        
        return True
    
    def show_game_over(self, wait_time=8):  # Increased wait time to give more time to view the summary
        """Show game over screen for a specified time"""
        end_time = time.time() + wait_time
        
        while time.time() < end_time:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            
            draw_game_over_screen(
                self.screen, self.font, self.small_font,
                self.score, self.max_score,
                self.correct_hits, self.missed_notes, self.wrong_notes,
                self.song_data,  # Pass the song data for the note summary
                self.get_beat_accuracy()  # Pass the beat accuracy
            )
            
            # Add "Press ESC to exit" text
            exit_text = self.small_font.render("Press ESC to exit", True, (200, 200, 200))
            self.screen.blit(exit_text, (WIDTH//2 - exit_text.get_width()//2, HEIGHT - 30))
            
            pygame.display.flip()
            self.clock.tick(60)
    
    def run(self):
        """Main game loop"""
        # Show instructions
        if not self.show_instructions():
            return
        
        # Run pre-play demonstration
        if not self.run_pre_play():
            return
        
        # Start the game
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
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        break
                
                # Process both keydown and keyup events for beat accuracy
                self.process_key_event(event, current_time)
            
            # Get visible notes and update missed notes
            visible_notes = get_visible_notes(self.song_data, current_time)
            self.missed_notes = update_missed_notes(visible_notes, current_time, self.missed_notes)
            
            # Draw game screen
            draw_game_screen(
                self.screen, self.font, self.small_font,
                self.key_display, self.note_colors, current_time,
                visible_notes, self.score, self.max_score,
                self.correct_hits, self.missed_notes, self.wrong_notes,
                self.last_key_pressed, self.active_note_info,
                self.get_beat_accuracy(),  # Pass beat accuracy to display
                self.current_instrument,   # Pass current instrument
                self.override_instruments  # Pass instrument override flag
            )
            
            pygame.display.flip()
            self.clock.tick(60)
            
            # Check for game end
            all_notes_handled = all(note['played'] or note['missed'] or note.get('wrong', False) for note in self.song_data)
            if all_notes_handled and current_time > self.last_note_time + 2:
                running = False
        
        # Show the final score with note summary
        self.show_game_over()
        
        pygame.quit()
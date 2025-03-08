import pygame
import argparse
from music_parser import parse_music_data
from slide import SlidePlayGame
from constants import INSTRUMENTS, INSTRUMENT_NAMES

def load_song_from_file(file_path):
    """Load song data from a file"""
    try:
        with open(file_path, 'r') as file:
            input_data = file.read()
        return parse_music_data(input_data)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error loading song data: {e}")
        return None

def main():
    """Main function to run the SlidePlay game"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='SlidePlay - A Music Note Game')
    parser.add_argument('song_file', nargs='?', default='track.txt', 
                        help='Path to the song file (default: track.txt)')
    parser.add_argument('--instrument', '-i', type=str, choices=['piano', 'guitar'], default=None,
                        help='Override instrument (piano or guitar)')
    args = parser.parse_args()
    
    # Initialize pygame
    pygame.init()
    
    # Load song data
    song_data = load_song_from_file(args.song_file)
    
    if song_data:
        # Create and run the game
        game = SlidePlayGame(song_data)
        
        # Set initial instrument if specified
        if args.instrument:
            if args.instrument.lower() == 'guitar':
                game.current_instrument = INSTRUMENTS["ELECTRO_GUITAR"]
                game.override_instruments = True
                print("Starting with Electro Guitar")
            elif args.instrument.lower() == 'piano':
                game.current_instrument = INSTRUMENTS["PIANO"]
                game.override_instruments = True
                print("Starting with Piano")
        
        # Run the game
        game.run()
    else:
        print("Failed to load song data. Exiting.")
        return

if __name__ == "__main__":
    main()
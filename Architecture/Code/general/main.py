# main.py - Main entry point for the SlidePlay music game

import pygame
import argparse
from music_parser import parse_music_data
from slide import SlidePlayGame

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
    args = parser.parse_args()
    
    # Initialize pygame
    pygame.init()
    
    # Load song data
    song_data = load_song_from_file(args.song_file)
    
    if song_data:
        # Create and run the game
        game = SlidePlayGame(song_data)
        game.run()
    else:
        print("Failed to load song data. Exiting.")
        return

if __name__ == "__main__":
    main()
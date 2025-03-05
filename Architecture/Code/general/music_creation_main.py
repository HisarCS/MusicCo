# music_creation_main.py - Entry point for music creation tool

from music_creation import MusicCreator

def main():
    """Main entry point for the music creation tool"""
    creator = MusicCreator()
    creator.run()

if __name__ == "__main__":
    main()
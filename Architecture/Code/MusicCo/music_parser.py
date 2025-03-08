from constants import INSTRUMENTS

def parse_music_data(input_data):
    """
    Parses a string of musical note data into a structured list of dictionaries.
   
    Args:
        input_data (str): The input string containing note data in the format
                          <Note><Octave>-<Start Time>-<Duration>-<Volume>[-<Instrument>].
                         
    Returns:
        list: A list of dictionaries with parsed note data.
    """

    entries = input_data.split()
    parsed_data = []
   
    for entry in entries:
        # Split by hyphens
        parts = entry.split('-')
        
        # Handle both old format (without instrument) and new format (with instrument)
        if len(parts) == 4:
            # Old format: note_octave-start_time-duration-volume
            note_octave, start_time, duration, volume = parts
            instrument = INSTRUMENTS["PIANO"]  # Default to piano for backward compatibility
        elif len(parts) == 5:
            # New format: note_octave-start_time-duration-volume-instrument
            note_octave, start_time, duration, volume, instrument = parts
            instrument = int(instrument)
        else:
            print(f"Warning: Skipping malformed entry: {entry}")
            continue
            
        # Separate note and octave
        note = ''.join([c for c in note_octave if not c.isdigit()])
        octave = ''.join([c for c in note_octave if c.isdigit()])

        parsed_data.append({
            'Note': note,
            'Octave': int(octave),
            'Start Time': float(start_time),
            'Duration': float(duration),
            'Volume': int(volume),
            'Instrument': instrument
        })
   
    return parsed_data
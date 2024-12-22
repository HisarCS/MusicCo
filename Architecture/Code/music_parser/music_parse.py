import pandas as pd


with open('music.txt', 'r') as file:
    input_data = file.read().strip()


entries = input_data.split()
parsed_data = []
for entry in entries:
    note_octave, start_time, duration, volume = entry.split('-')

    note = ''.join([c for c in note_octave if not c.isdigit()])
    octave = ''.join([c for c in note_octave if c.isdigit()])
    parsed_data.append({
        'Note': note,
        'Octave': int(octave),
        'Start Time': float(start_time),
        'Duration': float(duration),
        'Volume': int(volume)
    })


df = pd.DataFrame(parsed_data)


import ace_tools as tools; tools.display_dataframe_to_user(name="Parsed Musical Notes from music.txt", dataframe=df)

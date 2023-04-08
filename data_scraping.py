import os
import re
from chords import Chord
import string

### quick and dirty plaintext parsing

data_dir = 'data/chordpro/'
subdirs = os.listdir(data_dir)

# take only data folders, ignore hte others:
subdirs = [subdir for subdir in subdirs if subdir in list(string.ascii_lowercase) + ['1-9']]

##### scanning:

all_song_paths = []
song_paths_by_artist = {}
for s, subdir in enumerate(sorted(subdirs)):
    print(f'{s+1}/{len(subdirs)} Scanning artists beginning with {subdir}')
    subdir_path = os.path.join(data_dir, subdir)
    artists = os.listdir(subdir_path)
    for a, artist in enumerate(sorted(artists)):
        print(f'  {a+1}/{len(artists)} Scanning songs by artist: {artist}')
        artist_path = os.path.join(subdir_path, artist)
        song_names = os.listdir(artist_path)
        song_paths = [os.path.join(artist_path, song_name) for song_name in song_names]

        all_song_paths.extend(song_paths)
        song_paths_by_artist[artist] = song_paths
print(f'Scanned {len(all_song_paths)} songs')


##### parsing:

# for demonstration purposes we only take so many chords per song, and so many songs:
chords_per_song = 8
start_at = 0
max_num_songs = 300

# parse out progressions and cast to Chord types:
i = 0
progressions_by_artist = {}
for artist, song_paths in song_paths_by_artist.items():
    progressions_by_artist[artist] = {}
    for song_path in song_paths:
        if i >= start_at:
            with open(song_path, 'r') as file:
                song_name = (song_path.split('/')[-1]).split('chopro')[0]
                try:
                    contents = file.read()
                    # scan for chord names enclosed within square brackets:
                    matches = re.findall(r'\[([^\]]*)\]', contents)

                    # initialise as Chord objects:
                    song_chords = [Chord(m) for m in matches[:chords_per_song]]
                    progressions_by_artist[artist][song_name] = song_chords
                    print(f'    {i+1}/{len(all_song_paths)}: Parsed progressions for {artist} - {song_name}:')
                    for j, song_chord in enumerate(song_chords):
                        print(f'        {j}. {song_chord}')

                except Exception as e:
                    print(f'    {i+1}/{len(all_song_paths)}:  ERROR reading {song_name} by {artist}: {e}')
        i += 1
    if i >= (start_at + max_num_songs):
        break

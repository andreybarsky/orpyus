import os
import re
from src.chords import Chord
from src.progressions import Progression, ChordProgression, ChordList
import string
import ipdb

### quick and dirty plaintext parsing

data_dir = 'song_data/'
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

class Song:
    def __init__(self, name, artist, chords=None):
        self.name = name
        self.artist = artist

        if chords is not None:
            self.chords = ChordList(chords)

    def __str__(self):
        return (f'{self.artist} - {self.name}   |   {self.chords}')
    def __repr__(self):
        return str(self)

##### chord name parsing:

# parse out progressions as lists of valid chord_name strings:
i = 0
song_progressions_by_artist = {}
all_progressions = []
all_songs = []

for artist, song_paths in song_paths_by_artist.items():
    song_progressions_by_artist[artist] = {}
    for song_path in song_paths:
        with open(song_path, 'r') as file:
            song_name = (song_path.split('/')[-1]).split('chopro')[0]
            try:
                contents = file.read()
            except Exception as e:
                print(f'Error reading file {song_path}: {e}')
                continue
            # check for chord names enclosed within square brackets:
            song_chords = re.findall(r'\[([^\]]*)\]', contents)

            song_progression = ChordProgression(song_chords)
            song_progressions_by_artist[artist][song_name] = song_progression
            all_progressions.append(song_progression)
            song = Song(song_name, artist, song_chords)
            all_songs.append(song)
            print(f'    {i+1}/{len(all_song_paths)}: Parsed progressions for {artist} - {song_name}:')

            # except Exception as e:
            #     print(f'    {i+1}/{len(all_song_paths)}:  ERROR reading {song_name} by {artist}: {e}')
            i += 1



##### chord object instantiation:

#
# # for demonstration purposes we only take so many chords per song, and so many songs:
# chords_per_song = 12
# max_num_songs = 300
#
# i = 0
#
# # cache chords so we avoid re-initialising the same object many times:
# cached_chords = {}
#
# song_chords_by_artist = {}
# song_progs_by_artist = {}
# for artist, song_names in song_progressions_by_artist.items():
#
#     song_chords_by_artist[artist] = {}
#     song_progs_by_artist[artist] = {}
#     for song_name, progression in song_names.items():
#         print(f'\n{i}/{len(all_progressions)}: {artist} - {song_name}:')
#
#         # initialise as Chord objects, or use cached Chord if it's already been initialised:
#         song_chords = []
#         for song_chord_name in progression[:chords_per_song]:
#             # query cache:
#             if song_chord_name not in cached_chords:
#                 try:
#                     song_chord = Chord(song_chord_name)
#                     cached_chords[song_name] = song_chord
#                 except Exception as e:
#                     print(f'  Failed to initialise chord {song_chord_name}: {e}')
#                     song_chord = song_chord_name
#             else:
#                 song_chord = cached_chords[song_chord_name]
#             song_chords.append(song_chord)
#
#         song_chords_by_artist[artist][song_name] = song_chords
#
#         song_prog = ChordProgression(song_chords)
#         song_progs_by_artist[artist][song_name] = song_prog
#
#         print(song_prog)
#
#         i += 1
#         # exit loop if we've reached our limit for demonstration:
#         if i > max_num_songs:
#             break

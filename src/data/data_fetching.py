import os
import ssl
import urllib
import tarfile
import string

# JSC chordpro guitar archive with 3000 songs, last updated in 2013:
song_repo_url = 'http://getsome.org/guitar/olga/chordpro/chordpro.tgz'
song_local_dir = 'song_data/'

def fetch_song_data(force=False):
    if os.path.exists(song_local_dir):
        # path already exists, no need to create
        pass
        # print(f'Song data local dir ({song_local_dir}) already exists')
    else:
        print(f'Creating directory: {song_local_dir}')
        os.mkdir(song_local_dir)

    archive_filename = song_repo_url.split('/')[-1]
    archive_path = os.path.join(song_local_dir, archive_filename)

    if (not os.path.exists(archive_path)) or (force): # if not already downloaded, or we've asked to force it
        print(f'Downloading archive from: {song_repo_url}')
        # unsigned ssl certificate:
        ssl._create_default_https_context = ssl._create_unverified_context
        # download:
        urllib.request.urlretrieve(song_repo_url, archive_path)
        print(f'Downloaded to: {archive_path}')
    else:
        print(f'Song data archive ({archive_path}) already exists, no need to download')

    existing_files = os.listdir(song_local_dir)
    if (len(existing_files) == 1) or (force):
        # if it seems like the files have already been unpacked,
        # or we've been asked to force it
        print(f'Unpacking files...')
        archive = tarfile.open(archive_path)
        archive.extractall(song_local_dir)
        archive.close()
        print(f'Finished unpacking.')
    else:
        print(f'Files already seem to be unpacked. (if not, try rerunning with force=True)')

def read_files(count=False):
    """if count=False, loads subdirectories containing chord data into a dict tree.
    if count=True, just counts the number of files instead and returns the number that exist.
        (as a budget checksum to see if they've all been downloaded)"""
    subdirs = os.listdir(song_local_dir)

    # take only data folders, ignore the others:
    subdirs = [subdir for subdir in subdirs if subdir in list(string.ascii_lowercase) + ['1-9']]
    subdirs = sorted(subdirs) # alphabetical order

    num_files = 0
    total_successful_reads = 0
    if not count:
        file_tree = {}

    for letter_dir in subdirs:
        print(f'Artist names beginning with {letter_dir}:')
        letter_path = os.path.join(song_local_dir, letter_dir)
        artist_dirs = os.listdir(letter_path)
        for artist_dir in artist_dirs:
            artist_path = os.path.join(letter_path, artist_dir)
            artist_files = os.listdir(artist_path)
            song_filenames = [f for f in artist_files if f[-7:] == '.chopro']
            num_files += len(song_filenames)
            # print(f'  Artist {artist_dir}: {len(song_filenames)} .chopro files   (running total: {num_files})')


            if not count:
                artist_songs = {} # dict of song names to their contents
                successful_reads = 0
                failed_reads = 0
                for song_name in song_filenames:
                    song_path = os.path.join(artist_path, song_name)
                    try:
                        with open(song_path, 'r', encoding='iso8859_3') as song_file:
                            song_contents = song_file.read()
                            artist_songs[song_name] = song_contents
                        successful_reads += 1
                        total_successful_reads += 1
                    except Exception as e:
                        # print(f' -  Could not read {song_name}: {e}')
                        failed_reads += 1
                        # import ipdb; ipdb.set_trace()
                # print(f'    Read {successful_reads}/{len(song_filenames)} files successfully.')
                # add to dict tree:
                file_tree[artist_dir] = artist_songs

    if not count:
        if (total_successful_reads == num_files):
            print(f'All files read successfully.')
        else:
            print(f'{total_successful_reads}/{num_files} files read successfully.')

    if count:
        # raw integer of how many song files were found:
        return num_files
    else:
        # dict of dicts, with artist names to song names to song contents:
        return file_tree

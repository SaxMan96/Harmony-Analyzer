from bs4 import BeautifulSoup
import urllib
import re
import json
from pyRealParser import Tune
import pandas as pd
import pychord


def get_song_urls(web_links):
    songs_urls = []
    for link in web_links:
        fp = urllib.request.urlopen(link)
        mystr = fp.read().decode("latin-1")
        soup = BeautifulSoup(mystr, features="lxml")
        for link in soup.findAll("a", attrs={"href": re.compile("^irealb://")}):
            songs_urls.append(link.get("href"))
    return songs_urls


def string_to_chords(string):
    chords = [
        {
            "Root": chord.split(",")[0][2:-1],
            "Ext": chord.split(",")[1][2:-1],
            # "Bass": chord.split(",")[2][2:-2],
        }
        for chord in string.split(";")
    ]
    return chords


def chords_to_string(chords):
    string = ";".join(json.dumps(list(d.values())) for d in chords)
    return string


def multihot(chords, size='full'):
    if size == 'full':
        size = 33
    else:
        chords = [[note % size for note in chord] for chord in chords]
    encoded_chords = []
    for chord in chords:
        encoded_chord = [0] * size
        for i in chord:
            # in case of bass note I'll transpose it by octave up B = -1 --> B = 11
            if i < 0:
                i += 12
            encoded_chord[i] = 1
        encoded_chords.append(encoded_chord)
    return encoded_chords


def get_components(chords, ignore_bass=True):
    notes_numbers = []
    for c in chords:
        chord = pychord.Chord(c)
        if ignore_bass:
            chord._on = None
        comp = chord.components(visible=False)
        notes_numbers.append(comp)
    return notes_numbers


def discard_enharmonics(note):
    note = note.replace("C#", "Db")
    note = note.replace("D#", "Eb")
    note = note.replace("E#", "F")
    note = note.replace("F#", "Gb")
    note = note.replace("G#", "Ab")
    note = note.replace("A#", "Bb")
    note = note.replace("B#", "C")
    return note


def extract_chords_from_tune(my_tune):
    chords = []
    for measure in my_tune.measures_as_strings:
        elements = re.findall(
            r"([A-G][#b]?)(11|7b13sus|13sus|9sus|7susadd3|7b9sus|13#9|13b9|13#11|13|7alt|7b9b13|7b9#9|7b9#5|7b9b5|7b9#11|7#9#11|7#9b5|7#9#5|7b13|9#5|9b5|9#11|7#5|7b5|7#11|7#9|7b9|9|-#5|-b6|h9|-7b5|-11|-9|-\^9|-\^7|-69|-6|\^7#5|\^9#11|\^7#11|69|6|\^13|\^9|o7|h7|7sus|7|-7|\^7|-|\^|sus|h|o|\+|add9|2|5?)?(/[A-G][#b]?)?",
            measure,
        )
        for (root, extension, _) in elements:
            root = discard_enharmonics(root)
            chords.append(root + extension)
    return chords


def extract_meta_data(songs_urls):
    songs_meta = []
    for song_url in songs_urls:
        if len(Tune.parse_ireal_url(song_url)) > 0:
            my_tune = Tune.parse_ireal_url(song_url)[0]
            chords = extract_chords_from_tune(my_tune)
            # We are assuming that each note is interval from C
            song_meta = {
                "title": my_tune.title,
                "composer": my_tune.composer,
                "style": my_tune.style,
                "key": my_tune.key,
                "transpose": my_tune.transpose,
                "comp_style": my_tune.comp_style,
                "bpm": my_tune.bpm,
                "repeats": my_tune.repeats,
                "time_signature": my_tune.time_signature,
                'chords': chords
            }
            songs_meta.append(song_meta)
    df = pd.DataFrame(sorted(songs_meta, key=lambda l: l['title']))
    df.drop_duplicates(subset="title", inplace=True)
    return df
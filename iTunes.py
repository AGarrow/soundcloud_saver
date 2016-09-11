#!/usr/bin/env python

import os
import sys
import codecs
import xml.etree.ElementTree as ET

from appscript import *

iTunes = app('iTunes')

def get_library():
    return iTunes.library_playlists['Library']


def get_folders():
    return iTunes.folder_playlists()


def count_folder(folder):
    return folder.count(each=k.playlist)


def get_playlists():
    skip = [
        u'Party Shuffle',
        u'90\u2019s Music',
        u'Movies',
        u'Music',
        u'Music Videos',
        u'My Top Rated',
        u'Recently Added',
        u'Recently Played',
        u'Top 25 Most Played',
        u'TV Shows',
        u'Podcasts',
    ]
    return [x for x in iTunes.user_playlists() if x.name() not in skip]


def get_tracks(playlist):
    return playlist.file_tracks()


def get_parent(playlist):
    try:
        return playlist.parent()
    except:
        return None


def list_names(list, out):
    for elem in list:
        out.write('%s\n' % elem.name())


def check_track(track):
    try:
        path = track.location().path
        if not os.path.isfile(path):
            throw(AttributeError)
        return True
    except AttributeError:
        return False


def delete_missing(log):
    library = get_library()
    for track in get_tracks(library):
        if not check_track(track):
            log.write('- %s - %s\n' % (track.artist(), track.name())) 
            library.delete(track)


def freeze_tracks(tracks):
    return frozenset([x.database_ID() for x in tracks])


def catalog_playlists(playlists):
    return dict([(freeze_tracks(get_tracks(x)), x) for x in playlists])


def catalog_folders(folders):
    return dict([(x.name(), x) for x in folders])


def track_tuple(keys):
    return tuple(map(lambda x: x if x else 'Unknown', keys))


def catalog_tracks(playlist, log):
    tracks = get_tracks(playlist)
    catalog = dict()
    for track in tracks:
        artist = track.album_artist()
        if not artist:
            artist = track.artist()
        album = track.album()
        name = track.name()
        key = track_tuple([artist, album, name])
        if key in catalog:
            log.write('? duplicate track: %s - %s - %s\n' % key)
        else:
            catalog[key] = track
    return catalog


class setdict(dict):
    def add(self, key, val):
        if not key in self:
            self[key] = set()
        self[key].add(val)


class setdict2(setdict):
    def add(self, key1, key2, val):
        if key1 not in self:
            self[key1] = setdict()
        self[key1].add(key2, val)


def file_artist(track):
    try:
        path = track.location().path
        artist = os.path.split(path)[0].split('/')[-2]
        return artist if not artist == 'Compilations' else 'Various'
    except AttributeError:
        return None


def album_artist(tracks, log, album):
    artists = set([x.artist() for x in tracks])
    album_artists = set([x.album_artist() for x in tracks])
    compilations = set([x.compilation() for x in tracks])
    file_artists = set([file_artist(x) for x in tracks])
    compilation = compilations == set([True])
    if len(album_artists) == 1 and album_artists != set(['']):
        artist = album_artists.pop()
        if compilation:
            log.write('Album %s (%s) is compilation\n' % (album, artist))
    elif len(artists) == 1 and artists != set(['']):
        artist = artists.pop()
        if compilation:
            log.write('Album %s (%s) is compilation\n' % (album, artist))
    elif compilations == set([True]):
        artist = 'Various'
    elif len(file_artists) == 1:
        artist = file_artists.pop()
        log.write('Using file_artist for album %s (%s)\n' % (album, artist))
    else:
        artist = 'Unknown'
        log.write('Cannot determine artist for album %s\n' % album)
    return artist


def collect_albums(playlist):
    artists = setdict2()
    for track in get_tracks(playlist):
        artist = file_artist(track)
        if artist:
            album  = track.album()
            artists.add(artist, album, track)
    return artists


def year_string(tracks):
    years = [x.year() for x in tracks if x.year()]
    years = list(set(years))
    years.sort()
    n = len(years)
    if   n == 0:
        years = '-'
    elif n == 1:
        years = '(%d)' % years[0]
    elif n == 2:
        years = '(%d,%d)' % (years[0], years[1])
    else:
        years = '(%d-%d)' % (years[0], years[-1])
    return years


def title_key(pair):
    title = pair[0].lower()
    if title.startswith('a '):
        title = title[2:]
    elif title.startswith('the '):
        title = title[4:]
    return title


def track_key(track):
    return (track.disc_number(), track.track_number())


def list_albums(out, log):
    artists = collect_albums(get_library()).items()
    artists.sort(key=title_key)
    for artist, albums in artists:
        out.write('%s\n' % artist)
        albums = albums.items()
        albums.sort(key=title_key)
        for album, tracks in albums:
            years = year_string(tracks)
            out.write('\t%s %s\n' % (album, years))
        out.write('\n')


def list_playlists(out):
    list_names(get_playlists(), out)


def list_folders(out):
    list_names(get_folders(), out)


def list_album_playlists(out):
    artists = collect_albums(get_library())
    catalog = catalog_playlists(get_playlists())
    for artist in artists:
        albums = artists[artist]
        for album in albums:
            key = freeze_tracks(albums[album])
            if key in catalog:
                out.write('%s\n' % catalog[key].name())


def make(kind, name, loc=iTunes):
    return iTunes.make(new=kind, at=loc, with_properties={k.name: name})


def check_tracks(tracks, artist, album, log):
    try:
        error = "disc count"
        disc_count = set([x.disc_count() for x in tracks])
        assert len(disc_count) == 1
        disc_count = disc_count.pop()
        assert disc_count != 0
        track_counts = [set() for x in range(0,disc_count)]
        track_numbers = [list() for x in range(0,disc_count)]
        for track in tracks:
            n = track.disc_number()
            track_counts[n-1].add(track.track_count())
            track_numbers[n-1].append(track.track_number())
        for track_count, track_number in zip(track_counts, track_numbers):
            error = "missing disc"
            assert len(track_count) > 0
            error = "track count"
            assert len(track_count) == 1
            track_count = track_count.pop()
            assert track_count != 0
            error = "track numbers"
            track_number.sort()
            assert track_number == range(1,track_count+1)
    except AssertionError:
        log.write('! %s - %s (%s)\n' % (artist, album, error))


def add_tracks(tracks, playlist, log):
    tracks = list(tracks)
    tracks.sort(key=track_key)
    for track in tracks:
        iTunes.duplicate(track, to=playlist)


def delete_playlist(folder, log, index=None):
    name = folder.name()
    folder.delete()
    if index:
        del index[name]
    log.write('- %s\n' % name)


def make_album_playlists(log):
    artists = collect_albums(get_library())
    playlists = catalog_playlists(get_playlists())
    folders = catalog_folders(get_folders())
    for artist, albums in artists.iteritems():
        if artist not in folders:
            folder = make(k.folder_playlist, artist)
            log.write('+ %s\n' % artist)
            folders[artist] = folder
        else:
            folder = folders[artist]
        for album, tracks in albums.iteritems():
            check_tracks(tracks, artist, album, log)
            artist2 = album_artist(tracks, log, album)
            years = year_string(tracks)
            name = "%s %s %s" % (artist2, years, album)
            key = freeze_tracks(albums[album])
            if key in playlists:
                playlist = playlists[key]
                name2 = playlist.name()
                folder2 = get_parent(playlist)
                if folder2 and folder == folder2 and name == name2:
                    continue
                delete_playlist(playlist, log)
                if folder2 != folder and not count_folder(folder2):
                    delete_playlist(folder2, log, index=folders)
            playlist = make(k.user_playlist, name, loc=folder)
            add_tracks(tracks, playlist, log)
            log.write('+ %s\n' % name)


def dict_from_plist(plist):
    xml = dict()
    pairs = zip(plist[::2], plist[1::2])
    for key, val in pairs:
        assert key.tag == 'key'
        if val.tag == 'dict':
            xml[key.text] = dict_from_plist(val)
        elif val.tag == 'array':
            xml[key.text] = map(dict_from_plist, val)
        else:
            xml[key.text] = val.text
    return xml


def dict_from_xml_playlist(xmlfile):
    tree = ET.parse(xmlfile)
    assert tree.getroot().tag == 'plist'
    plist = tree.find('dict')
    xml = dict_from_plist(plist)
    return xml


def catalog_xml_playlists(xmlfile):
    xml = dict_from_xml_playlist(xmlfile)
    catalog = list()
    library = xml['Tracks']
    playlists = xml['Playlists']
    for playlist in playlists:
        if not 'Playlist Items' in playlist:
            continue
        tracks = list()
        track_IDs = [x['Track ID'] for x in playlist['Playlist Items']]
        for ID in track_IDs:
            track = library[ID]
            if 'Album Artist' in track:
                artist = track['Album Artist']
            else: 
                artist = track['Artist'] if 'Artist' in track else None
            album = track['Album'] if 'Album' in track else None
            name = track['Name'] if 'Name' in track else None
            key = track_tuple([artist, album, name])
            tracks.append(key)
        catalog.append((playlist['Name'], tracks))
    return catalog


def write_playlist(playlist, tracks, out):
    out.write('\n%s\n\n' % playlist)
    for track in tracks:
        out.write('%s - %s - %s\n' % track)
    

def list_xml_playlists(xmlfile, out):
    catalog = catalog_xml_playlists(xmlfile)
    for playlist, tracks in catalog:
        write_playlist(playlist, tracks, out)


def diff_playlists(xmlfile1, xmlfile2, out1, out2):
    catalog1 = dict(catalog_xml_playlists(xmlfile1))
    catalog2 = dict(catalog_xml_playlists(xmlfile2))
    for playlist, tracks1 in catalog1.iteritems():
        set1 = set(tracks1)
        set2 = set(catalog2[playlist]) if playlist in catalog2 else set()
        diff1 = list(set1 - set2)
        diff2 = list(set2 - set1)
        diff1.sort()
        diff2.sort()
        write_playlist(playlist, diff1, out1)
        write_playlist(playlist, diff2, out2)


def get_args(count, usage):
    argv = sys.argv
    if len(argv) == count + 1:
        return argv[1:]
    else:
        print 'usage: %s %s' % (argv[0], usage)
        exit(0)


def open_args(count, usage, start=1):
    argv = sys.argv
    if len(argv) == count + 1:
        return [codecs.open(x, 'w', 'utf-8') for x in argv[start:]]
    else:
        print 'usage: %s %s' % (argv[0], usage)
        exit(0)


def open_arg(usage):
    return open_args(1, usage)[0]

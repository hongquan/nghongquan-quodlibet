from __future__ import print_function
from quodlibet.formats._audio import AudioFile as Fakesong
from quodlibet.formats._audio import INTERN_NUM_DEFAULT, PEOPLE
from quodlibet.formats._album import Album,Playlist
import tempfile

from tests import TestCase, add
from random import randint
from timeit import timeit,default_timer


PLAYLISTS = tempfile.gettempdir()

NUMERIC_SONGS = [
    Fakesong({"~filename":"fake1.mp3",
              "~#length": 4, "~#added": 5, "~#lastplayed": 1,
              "~#bitrate": 200, "date": "100", "~#rating": 0.1,
              "originaldate": "2004-01-01", "~#filesize":101}),
    Fakesong({"~filename":"fake2.mp3",
              "~#length": 7, "~#added": 7, "~#lastplayed": 88,
              "~#bitrate": 220, "date": "99", "~#rating": 0.3,
              "originaldate": "2002-01-01", "~#filesize":202}),
    Fakesong({"~filename":"fake3.mp3",
              "~#length": 1, "~#added": 3, "~#lastplayed": 43,
              "~#bitrate": 60, "date": "33", "~#rating": 0.5})
]

class TAlbum(TestCase):
    def test_people_sort(s):
        songs = [
            Fakesong({"albumartist": "aa", "artist": "b\na"}),
            Fakesong({"albumartist": "aa", "artist": "a\na"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        s.failUnlessEqual(album.comma("~people"), "aa, a, b")

    def test_peoplesort_sort(s):
        songs = [
            Fakesong({"albumartistsort": "aa", "artist": "b\na"}),
            Fakesong({"albumartist": "aa", "artistsort": "a\na"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        s.failUnlessEqual(album.comma("~peoplesort"), "aa, a, b")

    def test_tied_tags(s):
        songs = [
            Fakesong({"artist": "a", "title": "c"}),
            Fakesong({"artist": "a", "dummy": "d\ne"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        s.failUnlessEqual(album.comma("~artist~dummy"), "a - e, d")

    def test_tied_num_tags(s):
        songs = [
            Fakesong({"~#length": 5, "title": "c", "~#rating": 0.4}),
            Fakesong({"~#length": 7, "dummy": "d\ne", "~#rating": 0.6}),
            Fakesong({"~#length": 0, "dummy2": 5, "~#rating": 0.5})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        s.failUnlessEqual(album.comma("~foo~~s~~~"), "")
        s.failUnlessEqual(album.comma("~#length~dummy"), "12 - e, d")
        s.failUnlessEqual(album.comma("~#rating~dummy"), "0.50 - e, d")
        s.failUnlessEqual(album.comma("~#length:sum~dummy"), "12 - e, d")
        s.failUnlessEqual(album.comma("~#dummy2"), 5)
        s.failUnlessEqual(album.comma("~#dummy3"), "")

    def test_internal_tags(s):
        songs = [
            Fakesong({"~#length": 5, "discnumber": "1", "date": "2038"}),
            Fakesong({"~#length": 7, "dummy": "d\ne", "discnumber": "2"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        s.failIfEqual(album.comma("~long-length"), "")
        s.failIfEqual(album.comma("~tracks"), "")
        s.failIfEqual(album.comma("~discs"), "")
        s.failUnlessEqual(album.comma("~foo"), "")

        s.failUnlessEqual(album.comma(""), "")
        s.failUnlessEqual(album.comma("~"), "")
        s.failUnlessEqual(album.get("~#"), "")

    def test_numeric_ops(s):
        songs = [
            Fakesong({"~#length": 4, "~#added": 5, "~#lastplayed": 1,
            "~#bitrate": 200, "date": "100", "~#rating": 0.1,
            "originaldate": "2004-01-01"}),
            Fakesong({"~#length": 7, "~#added": 7, "~#lastplayed": 88,
            "~#bitrate": 220, "date": "99", "~#rating": 0.3,
            "originaldate": "2002-01-01"}),
            Fakesong({"~#length": 1, "~#added": 3, "~#lastplayed": 43,
            "~#bitrate": 60, "date": "33", "~#rating": 0.5})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        s.failUnlessEqual(album.get("~#length"), 12)
        s.failUnlessEqual(album.get("~#length:sum"), 12)
        s.failUnlessEqual(album.get("~#length:max"), 7)
        s.failUnlessEqual(album.get("~#length:min"), 1)
        s.failUnlessEqual(album.get("~#length:avg"), 4)
        s.failUnlessEqual(album.get("~#length:foo"), 0)

        s.failUnlessEqual(album.get("~#added"), 7)
        s.failUnlessEqual(album.get("~#lastplayed"), 88)
        s.failUnlessEqual(album.get("~#bitrate"), 200)
        s.failUnlessEqual(album.get("~#year"), 33)
        s.failUnlessEqual(album.get("~#rating"), 0.3)
        s.failUnlessEqual(album.get("~#originalyear"), 2002)

    def test_defaults(s):
        failUnlessEq = s.failUnlessEqual
        song = Fakesong({})
        album = Album(song)

        failUnlessEq(album("foo", "x"), "x")

        album.songs.add(song)

        failUnlessEq(album("~#length", "x"), song("~#length", "x"))
        failUnlessEq(album("~#bitrate", "x"), song("~#bitrate", "x"))
        failUnlessEq(album("~#rating", "x"), song("~#rating", "x"))
        failUnlessEq(album("~#playcount", "x"), song("~#playcount", "x"))
        failUnlessEq(album("~#mtime", "x"), song("~#mtime", "x"))
        failUnlessEq(album("~#year", "x"), song("~#year", "x"))

        failUnlessEq(album("~#foo", "x"), song("~#foo", "x"))
        failUnlessEq(album("foo", "x"), song("foo", "x"))
        failUnlessEq(album("~foo", "x"), song("~foo", "x"))

        failUnlessEq(album("~people", "x"), song("~people", "x"))
        failUnlessEq(album("~peoplesort", "x"), song("~peoplesort", "x"))
        failUnlessEq(album("~performer", "x"), song("~performer", "x"))
        failUnlessEq(album("~performersort", "x"), song("~performersort", "x"))

        failUnlessEq(album("~cover", "x"), song("~cover", "x"))
        failUnlessEq(album("~rating", "x"), song("~rating", "x"))

        for p in PEOPLE:
            failUnlessEq(album(p, "x"), song(p, "x"))

        for p in INTERN_NUM_DEFAULT:
            failUnlessEq(album(p, "x"), song(p, "x"))

    def test_methods(s):
        songs = [
            Fakesong({"b": "bb4\nbb1\nbb1", "c": "cc1\ncc3\ncc3"}),
            Fakesong({"b": "bb1\nbb1\nbb4", "c": "cc3\ncc1\ncc3"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        s.failUnlessEqual(album.list("c"), ["cc3", "cc1"])
        s.failUnlessEqual(album.list("~c~b"), ["cc3", "cc1", "bb1", "bb4"])

        s.failUnlessEqual(album.comma("c"), "cc3, cc1")
        s.failUnlessEqual(album.comma("~c~b"), "cc3, cc1 - bb1, bb4")

add(TAlbum)

class TPlaylist(TestCase):

    def test_equality(s):
        pl = Playlist(PLAYLISTS, "playlist")
        pl2 = Playlist(PLAYLISTS, "playlist")
        pl3 = Playlist("./", "playlist")
        s.failUnlessEqual(pl, pl2)
        # Debatable
        s.failUnlessEqual(pl, pl3)
        pl4 = Playlist(PLAYLISTS, "foobar")
        s.failIfEqual(pl, pl4)


    def test_internal_tags(s):
        songs = [
            Fakesong({"~#length": 5, "discnumber": "1", "date": "2038"}),
            Fakesong({"~#length": 7, "dummy": "d\ne", "discnumber": "2"})
        ]
        pl = Playlist(PLAYLISTS, "playlist")
        pl.extend(songs)

        s.failIfEqual(pl.comma("~long-length"), "")
        s.failIfEqual(pl.comma("~tracks"), "")
        s.failIfEqual(pl.comma("~discs"), "")
        s.failUnlessEqual(pl.comma("~foo"), "")

        s.failUnlessEqual(pl.comma(""), "")
        s.failUnlessEqual(pl.comma("~"), "")
        s.failUnlessEqual(pl.get("~#"), "")

    def test_numeric_ops(s):
        songs = NUMERIC_SONGS
        pl = Playlist(PLAYLISTS, "playlist")
        pl.extend(songs)

        s.failUnlessEqual(pl.get("~#length"), 12)
        s.failUnlessEqual(pl.get("~#length:sum"), 12)
        s.failUnlessEqual(pl.get("~#length:max"), 7)
        s.failUnlessEqual(pl.get("~#length:min"), 1)
        s.failUnlessEqual(pl.get("~#length:avg"), 4)
        s.failUnlessEqual(pl.get("~#length:foo"), 0)

        s.failUnlessEqual(pl.get("~#filesize"), 303)

        s.failUnlessEqual(pl.get("~#added"), 7)
        s.failUnlessEqual(pl.get("~#lastplayed"), 88)
        s.failUnlessEqual(pl.get("~#bitrate"), 200)
        s.failUnlessEqual(pl.get("~#year"), 33)
        s.failUnlessEqual(pl.get("~#rating"), 0.3)
        s.failUnlessEqual(pl.get("~#originalyear"), 2002)

    def test_listlike(s):
        pl = Playlist(PLAYLISTS, "playlist")
        pl.extend(NUMERIC_SONGS)
        s.failUnlessEqual(NUMERIC_SONGS[0], pl[0])
        s.failUnlessEqual(NUMERIC_SONGS[1:2], pl[1:2])
        s.failUnless(NUMERIC_SONGS[1] in pl)

    def test_playlists_featuring(s):
        Playlist._remove_all()
        Playlist._clear_global_cache()
        pl = Playlist(PLAYLISTS, "playlist")
        pl.extend(NUMERIC_SONGS)
        playlists = Playlist.playlists_featuring(NUMERIC_SONGS[0])
        s.failUnlessEqual(playlists, set([pl]))
        # Now add a second one, check that instance tracking works
        pl2 = Playlist(PLAYLISTS, "playlist2")
        pl2.append(NUMERIC_SONGS[0])
        playlists = Playlist.playlists_featuring(NUMERIC_SONGS[0])
        s.failUnlessEqual(playlists, set([pl, pl2]))

    def test_playlists_tag(self):
        # Arguably belongs in _audio
        songs = NUMERIC_SONGS
        Playlist._remove_all()
        Playlist._clear_global_cache()
        pl_name="playlist 123!"
        pl = Playlist(PLAYLISTS, pl_name)
        pl.extend(songs)
        for song in songs:
            self.assertEquals(pl_name, song("~playlists"))
add(TPlaylist)

class TPlaylistPerformance(TestCase):
    def test_playlists_featuring_performance(s):
        """Basic performance tests for `playlists_featuring()`

        Initial tests indicate that:
        For 100,000 songs with 20 Playlists (each of 1000 songs):
        -> The cache is ~= 6MB in size, delivers a 250x speed increase once warm

        For 10,000 songs with 20 Playlists (each of 100 songs):
        -> The cache is ~= 770 KB in size, 6.4x speed increase once warm

        For 10,000 songs with 2 Playlists (each of 5000 songs)
        -> The cache is ~= 770 KB in size, 180x speed increase once warm

        TODO: Convert prints to print_d and allow through if required in tests
        """

        # Basic sizes
        NUM_PLAYLISTS = 10
        NUM_SONGS = 10000

        # Every nth song is playlisted
        SONGS_TO_PLAYLIST_SIZE_RATIO = 10

        PLAYLISTS_PER_PLAYLISTED_SONG = 3

        ARTISTS = ["Mr Foo", "Bar", "Miss T Fie", "Dr Death"]
        pls = []
        library = []

        def setup():
            Playlist._remove_all()
            for i in xrange(NUM_PLAYLISTS):
                pls.append(Playlist(PLAYLISTS, "List %d" % (i+1)))
            for i in xrange(NUM_SONGS):
                a = ARTISTS[randint(0,2)]
                t = "Song %d" % i
                data = {"title": t, "artist":a, "~#tracknumber": i % 20,
                        "~#filesize":randint(1000000,100000000)}
                song = Fakesong(data)
                library.append(song)
                if not (i % SONGS_TO_PLAYLIST_SIZE_RATIO):
                    song["~included"] = "yes"
                    for j in range(PLAYLISTS_PER_PLAYLISTED_SONG):
                        pls[(i+j) % NUM_PLAYLISTS].append(song)

        print("\nSetting up %d songs and %d playlists... " % (
            NUM_SONGS, NUM_PLAYLISTS), end='')
        print("took %.1f ms" % (timeit(setup, "pass", default_timer, 1)*1000.0))

        def get_playlists():
            for song in library:
                #song = library[randint(0,len(library)-1)]
                playlists = func(song)
                s.failUnlessEqual(len(playlists),
                                  PLAYLISTS_PER_PLAYLISTED_SONG if
                                        song("~included") else 0)
                # Spot sanity check
                # s.failUnless(song in list(playlists)[0])

        REPEATS = 2
        func = Playlist._uncached_playlists_featuring
        print("Using %d songs and %d playlists, with 1 in %d songs "
              "in %d playlist(s) => each playlist has %d songs. "
               %  (NUM_SONGS, NUM_PLAYLISTS,
                   SONGS_TO_PLAYLIST_SIZE_RATIO,
                   PLAYLISTS_PER_PLAYLISTED_SONG,
                   PLAYLISTS_PER_PLAYLISTED_SONG * NUM_SONGS
                       / (SONGS_TO_PLAYLIST_SIZE_RATIO * NUM_PLAYLISTS)))
        print("Timing basic get_playlists_featuring()... ", end='')
        duration = timeit(get_playlists, "pass", default_timer, REPEATS)
        print("averages %.1f ms" % (duration * 1000.0 / REPEATS))

        # Now try caching version
        func = Playlist._cached_playlists_featuring
        print("Timing cached get_playlists_featuring()...", end='')
        cold = timeit(get_playlists, "pass", default_timer, 1)
        # And now it's warmed up...
        print("\n\tcold: averages %.1f ms" % (cold* 1000.0))
        warm = timeit(get_playlists, "pass", default_timer, REPEATS -1)
        print("\twarm: averages %.1f ms (speedup = %.1f X)"
              % (warm * 1000.0 / (REPEATS-1), cold/warm))
        print("Cache hits = %d, misses = %d (%d%% hits). Size of cache=%.2f KB"
              % (Playlist._hits, Playlist._misses,
                 Playlist._hits * 100 / (Playlist._misses + Playlist._hits),
                 Playlist._get_cache_size()))

# TODO: Add to a new perf-test suite, when available
# add(TPlaylistPerformance)
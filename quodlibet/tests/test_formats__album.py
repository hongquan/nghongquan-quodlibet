from quodlibet.formats._audio import AudioFile as Fakesong
from quodlibet.formats._audio import INTERN_NUM_DEFAULT, PEOPLE
from quodlibet.formats._album import Album

from tests import TestCase, add

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

import os
from tests import add
from unittest import TestCase
import mutagen.apev2

from mutagen.apev2 import APEv2File

DIR = os.path.dirname(__file__)
SAMPLE = os.path.join(DIR, "data", "click.mpc")
OLD = os.path.join(DIR, "data", "oldtag.apev2")
BROKEN = os.path.join(DIR, "data", "brokentag.apev2")
LYRICS2 = os.path.join(DIR, "data", "apev2-lyricsv2.mp3")

class APEWriter(TestCase):
    offset = 0

    def setUp(self):
        import shutil
        shutil.copy(SAMPLE, SAMPLE + ".new")
        shutil.copy(BROKEN, BROKEN + ".new")
        tag = mutagen.apev2.APEv2()
        self.values = {"artist": "Joe Wreschnig\0unittest",
                       "album": "Mutagen tests",
                       "title": "Not really a song"}
        for k, v in self.values.items():
            tag[k] = v
        tag.save(SAMPLE + ".new")
        tag.save(SAMPLE + ".justtag")
        tag.save(SAMPLE + ".tag_at_start")
        fileobj = file(SAMPLE + ".tag_at_start", "ab")
        fileobj.write("tag garbage" * 1000)
        fileobj.close()
        self.tag = mutagen.apev2.APEv2(SAMPLE + ".new")

    def test_changed(self):
        size = os.path.getsize(SAMPLE + ".new") 
        self.tag.save()
        self.failUnlessEqual(
            os.path.getsize(SAMPLE + ".new"), size - self.offset)

    def test_fix_broken(self):
        # Clean up garbage from a bug in pre-Mutagen APEv2.
        # This also tests removing ID3v1 tags on writes.
        self.failIfEqual(os.path.getsize(OLD), os.path.getsize(BROKEN))
        tag = mutagen.apev2.APEv2(BROKEN)
        tag.save(BROKEN + ".new")
        self.failUnlessEqual(
            os.path.getsize(OLD), os.path.getsize(BROKEN+".new"))

    def test_readback(self):
        for k, v in self.tag.items():
            self.failUnlessEqual(str(v), self.values[k])

    def test_size(self):
        self.failUnlessEqual(
            os.path.getsize(SAMPLE + ".new"),
            os.path.getsize(SAMPLE) + os.path.getsize(SAMPLE + ".justtag"))

    def test_delete(self):
        mutagen.apev2.delete(SAMPLE + ".justtag")
        mutagen.apev2.delete(SAMPLE + ".new")
        self.failUnlessEqual(os.path.getsize(SAMPLE + ".justtag"), self.offset)
        self.failUnlessEqual(os.path.getsize(SAMPLE) + self.offset,
                             os.path.getsize(SAMPLE + ".new"))

    def test_empty(self):
        self.failUnlessRaises(
            IOError, mutagen.apev2.APEv2,
            os.path.join("tests", "data", "emptyfile.mp3"))

    def test_tag_at_start(self):
        filename = SAMPLE + ".tag_at_start"
        tag = mutagen.apev2.APEv2(filename)
        self.failUnlessEqual(tag["album"], "Mutagen tests")

    def test_tag_at_start_write(self):
        filename = SAMPLE + ".tag_at_start"
        tag = mutagen.apev2.APEv2(filename)
        tag.save()
        tag = mutagen.apev2.APEv2(filename)
        self.failUnlessEqual(tag["album"], "Mutagen tests")
        self.failUnlessEqual(
            os.path.getsize(SAMPLE + ".justtag"),
            os.path.getsize(filename) - (len("tag garbage") * 1000))

    def test_tag_at_start_delete(self):
        filename = SAMPLE + ".tag_at_start"
        tag = mutagen.apev2.APEv2(filename)
        tag.delete()
        self.failUnlessRaises(IOError, mutagen.apev2.APEv2, filename)
        self.failUnlessEqual(
            os.path.getsize(filename), len("tag garbage") * 1000)

    def tearDown(self):
        os.unlink(SAMPLE + ".new")
        os.unlink(BROKEN + ".new")
        os.unlink(SAMPLE + ".justtag")
        os.unlink(SAMPLE + ".tag_at_start")

class APEReader(TestCase):
    def setUp(self):
        self.tag = mutagen.apev2.APEv2(OLD)

    def test_invalid(self):
        self.failUnlessRaises(IOError, mutagen.apev2.APEv2, "dne")

    def test_cases(self):
        self.failUnlessEqual(self.tag["artist"], self.tag["ARTIST"])
        self.failUnless("artist" in self.tag)
        self.failUnless("artisT" in self.tag)

    def test_keys(self):
        self.failUnless("track" in self.tag.keys())
        self.failUnless("Track" in self.tag.keys())
        self.failUnless("AnArtist" in self.tag.values())

        self.failUnlessEqual(
            self.tag.items(), zip(self.tag.keys(), self.tag.values()))

    def test_dictlike(self):
        self.failUnless(self.tag.get("track"))
        self.failUnless(self.tag.get("Track"))

    def test_del(self):
        s = self.tag["artist"]
        del(self.tag["artist"])
        self.failIf("artist" in self.tag)
        self.failUnlessRaises(KeyError, self.tag.__getitem__, "artist")
        self.tag["Artist"] = s
        self.failUnlessEqual(self.tag["artist"], "AnArtist")

    def test_values(self):
        self.failUnlessEqual(self.tag["artist"], self.tag["artist"])
        self.failUnless(self.tag["artist"] < self.tag["title"])
        self.failUnlessEqual(self.tag["artist"], "AnArtist")
        self.failUnlessEqual(self.tag["title"], "Some Music")
        self.failUnlessEqual(self.tag["album"], "A test case")
        self.failUnlessEqual("07", self.tag["track"])

        self.failIfEqual(self.tag["album"], "A test Case")

    def test_pprint(self):
        self.failUnless(self.tag.pprint())

class APEv2ThenID3v1Reader(APEReader):
    def setUp(self):
        import shutil
        shutil.copy(OLD, OLD + ".new")
        f = file(OLD + ".new", "ab+")
        f.write("TAG" + "\x00" * 125)
        f.close()
        self.tag = mutagen.apev2.APEv2(OLD + ".new")

    def tearDown(self):
        os.unlink(OLD + ".new")
add(APEv2ThenID3v1Reader)

class APEv2ThenID3v1Writer(APEWriter):
    offset = 128

    def setUp(self):
        super(APEv2ThenID3v1Writer, self).setUp()
        f = file(SAMPLE + ".new", "ab+")
        f.write("TAG" + "\x00" * 125)
        f.close()
        f = file(BROKEN + ".new", "ab+")
        f.write("TAG" + "\x00" * 125)
        f.close()
        f = file(SAMPLE + ".justtag", "ab+")
        f.write("TAG" + "\x00" * 125)
        f.close()

    def test_tag_at_start_write(self):
        pass

add(APEv2ThenID3v1Writer)

class APEv2WithLyrics2(TestCase):
    def setUp(self):
        self.tag = mutagen.apev2.APEv2(LYRICS2)
		
    def test_values(self):
        self.failUnlessEqual(self.tag["MP3GAIN_MINMAX"], "000,179")
        self.failUnlessEqual(self.tag["REPLAYGAIN_TRACK_GAIN"], "-4.080000 dB")
        self.failUnlessEqual(self.tag["REPLAYGAIN_TRACK_PEAK"], "1.008101")

add(APEv2WithLyrics2)

class APEKeyTest(TestCase):
    from mutagen.apev2 import APEKey

    def test_eq(self):
        self.failUnlessEqual(self.APEKey("foo"), "foo")
        self.failUnlessEqual("foo", self.APEKey("foo"))
        self.failUnlessEqual(self.APEKey("foo"), u"foo")
        self.failUnlessEqual(u"foo", self.APEKey("foo"))

        self.failUnlessEqual(self.APEKey("Bar"), "baR")
        self.failUnlessEqual(u"baR", self.APEKey("Bar"))

    def test_hash(self):
        self.failUnlessEqual(hash("foo"), hash(self.APEKey("foo")))
        self.failUnlessEqual(hash("foo"), hash(self.APEKey("FoO")))

    def test_repr(self):
        self.failUnless(repr(self.APEKey("foo")))

class APEBinaryTest(TestCase):
    from mutagen.apev2 import APEBinaryValue as BV

    def setUp(self):
        self.sample = "\x12\x45\xde"
        self.value = mutagen.apev2.APEValue(self.sample,mutagen.apev2.BINARY)

    def test_type(self):
        self.failUnless(isinstance(self.value, self.BV))

    def test_const(self):
        self.failUnlessEqual(self.sample, str(self.value))

    def test_repr(self):
        repr(self.value)

class APETextTest(TestCase):
    from mutagen.apev2 import APETextValue as TV
    def setUp(self):
        self.sample = ["foo", "bar", "baz"]
        self.value = mutagen.apev2.APEValue(
            "\0".join(self.sample), mutagen.apev2.TEXT)

    def test_type(self):
        self.failUnless(isinstance(self.value, self.TV))

    def test_list(self):
        self.failUnlessEqual(self.sample, list(self.value))

    def test_setitem_list(self):
        self.value[2] = self.sample[2] = 'quux'
        self.test_list()
        self.test_getitem()
        self.value[2] = self.sample[2] = 'baz'

    def test_getitem(self):
        for i in range(len(self.value)):
            self.failUnlessEqual(self.sample[i], self.value[i])

    def test_repr(self):
        repr(self.value)

class APEExtTest(TestCase):
    from mutagen.apev2 import APEExtValue as EV

    def setUp(self):
        self.sample = "http://foo"
        self.value = mutagen.apev2.APEValue(
            self.sample, mutagen.apev2.EXTERNAL)

    def test_type(self):
        self.failUnless(isinstance(self.value, self.EV))

    def test_const(self):
        self.failUnlessEqual(self.sample, str(self.value))

    def test_repr(self):
        repr(self.value)

class TAPEv2File(TestCase):
    def setUp(self):
        self.audio = APEv2File("tests/data/click.mpc")

    def test_add_tags(self):
        self.failUnless(self.audio.tags is None)
        self.audio.add_tags()
        self.failUnless(self.audio.tags is not None)
        self.failUnlessRaises(ValueError, self.audio.add_tags)
add(TAPEv2File)

add(APEReader)
add(APEWriter)
add(APEKeyTest)
add(APEBinaryTest)
add(APETextTest)
add(APEExtTest)

import os
from tests import TestCase, add
from mutagen import File, Metadata, FileType
from mutagen.oggvorbis import OggVorbis
from mutagen.oggflac import OggFLAC
from mutagen.oggspeex import OggSpeex
from mutagen.oggtheora import OggTheora
from mutagen.mp3 import MP3
from mutagen.apev2 import APEv2File
from mutagen.flac import FLAC
from mutagen.wavpack import WavPack
from mutagen.trueaudio import TrueAudio
from mutagen.m4a import M4A
from mutagen.musepack import Musepack
from mutagen.monkeysaudio import MonkeysAudio
try: from os.path import devnull
except ImportError: devnull = "/dev/null"

class TMetadata(TestCase):
    uses_mmap = False

    class FakeMeta(Metadata):
        def __init__(self): pass

    def test_virtual_constructor(self):
        self.failUnlessRaises(NotImplementedError, Metadata, "filename")

    def test_virtual_save(self):
        self.failUnlessRaises(NotImplementedError, self.FakeMeta().save)
        self.failUnlessRaises(
            NotImplementedError, self.FakeMeta().save, "filename")

    def test_virtual_delete(self):
        self.failUnlessRaises(NotImplementedError, self.FakeMeta().delete)
        self.failUnlessRaises(
            NotImplementedError, self.FakeMeta().delete, "filename")
add(TMetadata)

class TFileType(TestCase):
    uses_mmap = False

    def setUp(self):
        self.vorbis = File(os.path.join("tests", "data", "empty.ogg"))

    def test_delitem_not_there(self):
        self.failUnlessRaises(KeyError, self.vorbis.__delitem__, "foobar")

    def test_delitem(self):
        self.vorbis["foobar"] = "quux"
        del(self.vorbis["foobar"])
        self.failIf("quux" in self.vorbis)
add(TFileType)

class TFile(TestCase):
    uses_mmap = False

    def test_bad(self):
        try: self.failUnless(File(devnull) is None)
        except (OSError, IOError):
            print "WARNING: Unable to open %s." % devnull
        self.failUnless(File(__file__) is None)

    def test_empty(self):
        filename = os.path.join("tests", "data", "empty")
        file(filename, "wb").close()
        try: self.failUnless(File(filename) is None)
        finally: os.unlink(filename)

    def test_not_file(self):
        self.failUnlessRaises(EnvironmentError, File, "/dev/doesnotexist")

    def test_no_options(self):
        for filename in ["empty.ogg", "empty.oggflac", "silence-44-s.mp3"]:
            filename = os.path.join("tests", "data", "empty.ogg")
            self.failIf(File(filename, options=[]))

    def test_oggvorbis(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "empty.ogg")), OggVorbis))

    def test_oggflac(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "empty.oggflac")), OggFLAC))

    def test_oggspeex(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "empty.spx")), OggSpeex))

    def test_oggtheora(self):
        self.failUnless(isinstance(File(
            os.path.join("tests", "data", "sample.oggtheora")), OggTheora))

    def test_mp3(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "bad-xing.mp3")), MP3))
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "xing.mp3")), MP3))
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "silence-44-s.mp3")), MP3))

    def test_flac(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "silence-44-s.flac")), FLAC))

    def test_musepack(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "click.mpc")), Musepack))
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "sv4_header.mpc")), Musepack))
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "sv5_header.mpc")), Musepack))

    def test_monkeysaudio(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "mac-399.ape")), MonkeysAudio))
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "mac-396.ape")), MonkeysAudio))

    def test_apev2(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "oldtag.apev2")), APEv2File))

    def test_tta(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "empty.tta")), TrueAudio))

    def test_wavpack(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "silence-44-s.wv")), WavPack))

    def test_m4a(self):
        self.failUnless(isinstance(
            File(os.path.join("tests", "data", "has-tags.m4a")), M4A))

add(TFile)

class TMutagen(TestCase):
    uses_mmap = False

    def test_not_prerelease(self):
        from mutagen import version
        from os.path import dirname, basename, abspath
        trunk = basename(dirname(dirname(dirname(abspath(__file__)))))
        if trunk != "trunk":
            self.failIf(version[-1] < 0, "mutagen.version is a prerelease.")
        else:
            self.failIf(
                version[-1] >= 0, "mutagen.version is not a prerelease.")
add(TMutagen)

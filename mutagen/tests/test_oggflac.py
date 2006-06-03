import os
import shutil
import sys

from tempfile import mkstemp
from cStringIO import StringIO

from mutagen.oggflac import OggFLAC, OggFLACStreamInfo, delete
from mutagen.ogg import OggPage
from tests import add
from tests.test_ogg import TOggFileType

class TOggFLAC(TOggFileType):
    Kind = OggFLAC

    def setUp(self):
        original = os.path.join("tests", "data", "empty.oggflac")
        fd, self.filename = mkstemp(suffix='.ogg')
        os.close(fd)
        shutil.copy(original, self.filename)
        self.audio = OggFLAC(self.filename)

    def test_vendor(self):
        self.failUnless(
            self.audio.tags.vendor.startswith("reference libFLAC"))
        self.failUnlessRaises(KeyError, self.audio.tags.__getitem__, "vendor")

    def test_streaminfo_bad_marker(self):
        page = OggPage(file(self.filename, "rb")).write()
        page = page.replace("fLaC", "!fLa", 1)
        self.failUnlessRaises(IOError, OggFLACStreamInfo, StringIO(page))

    def test_streaminfo_bad_version(self):
        page = OggPage(file(self.filename, "rb")).write()
        page = page.replace("\x01\x00", "\x02\x00", 1)
        self.failUnlessRaises(IOError, OggFLACStreamInfo, StringIO(page))

    def test_flac_reference_simple_save(self):
        self.audio.save()
        self.scan_file()
        value = os.system("flac --ogg -t %s 2> /dev/null" % self.filename)
        self.failIf(value and value != NOTFOUND)

    def test_flac_reference_really_big(self):
        self.test_really_big()
        self.audio.save()
        self.scan_file()
        value = os.system("flac --ogg -t %s 2> /dev/null" % self.filename)
        self.failIf(value and value != NOTFOUND)

    def test_module_delete(self):
        delete(self.filename)
        self.scan_file()
        self.failIf(OggFLAC(self.filename).tags)

    def test_flac_reference_delete(self):
        self.audio.delete()
        self.scan_file()
        value = os.system("flac --ogg -t %s 2> /dev/null" % self.filename)
        self.failIf(value and value != NOTFOUND)
 
    def test_flac_reference_medium_sized(self):
        self.audio["foobar"] = "foobar" * 1000
        self.audio.save()
        self.scan_file()
        value = os.system("flac --ogg -t %s 2> /dev/null" % self.filename)
        self.failIf(value and value != NOTFOUND)

    def test_flac_reference_delete_readd(self):
        self.audio.delete()
        self.audio.tags.clear()
        self.audio["foobar"] = "foobar" * 1000
        self.audio.save()
        self.scan_file()
        value = os.system("flac --ogg -t %s 2> /dev/null" % self.filename)
        self.failIf(value and value != NOTFOUND)
 
    def test_not_my_ogg(self):
        fn = os.path.join('tests', 'data', 'empty.ogg')
        self.failUnlessRaises(IOError, type(self.audio), fn)
        self.failUnlessRaises(IOError, self.audio.save, fn)
        self.failUnlessRaises(IOError, self.audio.delete, fn)

add(TOggFLAC)

NOTFOUND = os.system("tools/notarealprogram 2> /dev/null")

if os.system("flac 2> /dev/null > /dev/null") == NOTFOUND:
    print "WARNING: Skipping Ogg FLAC reference tests."

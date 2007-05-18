from tests import TestCase, add

import gtk

from quodlibet.formats._audio import AudioFile
from quodlibet.player import PlaylistPlayer
from quodlibet.qltk.tracker import SongTracker
from quodlibet.library import SongLibrary

class TSongTracker(TestCase):
    def setUp(self):
        self.p = PlaylistPlayer('fakesink')
        self.w = SongLibrary()
        self.s1 = AudioFile(
            {"~#playcount": 0, "~#skipcount": 0, "~#lastplayed": 10,
             "~filename": "foo"})
        self.s2 = AudioFile(
            {"~#playcount": 0, "~#skipcount": 0, "~#lastplayed": 10,
             "~filename": "foo"})
        self.cm = SongTracker(self.w, self.p, self)
        self.current = None

    def do(self):
        while gtk.events_pending(): gtk.main_iteration()

    def test_play(self):
        self.p.emit('song-ended', self.s1, False)
        self.do()
        import time; t = time.time()
        self.assertEquals(self.s1["~#playcount"], 1)
        self.assertEquals(self.s1["~#skipcount"], 0)
        self.failUnless(t - self.s1["~#lastplayed"] <= 1)

    def test_skip(self):
        self.p.emit('song-ended', self.s1, True)
        self.do()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 1)
        self.failUnless(self.s1["~#lastplayed"], 10)

    def test_restart(self):
        self.current = self.s1
        self.p.emit('song-ended', self.s1, True)
        self.do()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 0)

    def tearDown(self):
        self.w.destroy()

add(TSongTracker)


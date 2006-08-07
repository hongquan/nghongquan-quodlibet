from tests import TestCase, add

import gtk
from util import copool

class Tcopool(TestCase):
    def setUp(self):
        self.buffer = None

    def __set_buffer(self):
        while True:
            self.buffer = True
            yield None

    def test_add_remove(self):
        copool.add(self.__set_buffer)
        gtk.main_iteration()
        gtk.main_iteration()
        self.assertEquals(self.buffer, True)
        copool.remove(self.__set_buffer)
        self.buffer = None
        gtk.main_iteration()
        gtk.main_iteration()
        self.assertEquals(self.buffer, None)

    def test_add_remove_with_funcid(self):
        copool.add(self.__set_buffer, funcid="test")
        gtk.main_iteration()
        gtk.main_iteration()
        self.assertEquals(self.buffer, True)
        copool.remove("test")
        self.buffer = None
        gtk.main_iteration()
        gtk.main_iteration()
        self.assertEquals(self.buffer, None)

    def test_pause_resume(self):
        copool.add(self.__set_buffer)
        gtk.main_iteration()
        gtk.main_iteration()
        copool.pause(self.__set_buffer)
        self.buffer = None
        gtk.main_iteration()
        gtk.main_iteration()
        self.assertEquals(self.buffer, None)
        copool.resume(self.__set_buffer)
        gtk.main_iteration()
        gtk.main_iteration()
        self.assertEquals(self.buffer, True)
        copool.remove(self.__set_buffer)
        self.buffer = None
        gtk.main_iteration()
        gtk.main_iteration()

    def test_pause_resume_with_funcid(self):
        copool.add(self.__set_buffer, funcid="test")
        gtk.main_iteration()
        gtk.main_iteration()
        copool.pause("test")
        self.buffer = None
        gtk.main_iteration()
        gtk.main_iteration()
        self.assertEquals(self.buffer, None)
        copool.resume("test")
        gtk.main_iteration()
        gtk.main_iteration()
        self.assertEquals(self.buffer, True)
        copool.remove("test")
        self.buffer = None
        gtk.main_iteration()
        gtk.main_iteration()

add(Tcopool)







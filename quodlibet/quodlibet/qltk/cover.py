# -*- coding: utf-8 -*-
# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Iñigo Serna,
# Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


import gobject
import gtk

from quodlibet import qltk
from quodlibet import config
from quodlibet import print_d, print_w
from quodlibet.util import thumbnails


# TODO: neater way of managing dependency on this particular plugin
ALBUM_ART_PLUGIN_ID = "Download Album art"


class BigCenteredImage(qltk.Window):
    """Load an image and display it, scaling down to 1/2 the screen's
    dimensions if necessary.

    This might leak memory, but it could just be Python's GC being dumb."""

    def __init__(self, title, filename, parent=None):
        super(BigCenteredImage, self).__init__()
        self.set_transient_for(qltk.get_top_parent(parent))
        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2

        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        pixbuf = thumbnails.scale(pixbuf, (width, height), scale_up=False)

        self.set_title(title)
        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_modal(False)
        self.add(gtk.Frame())
        self.child.set_shadow_type(gtk.SHADOW_OUT)
        self.child.add(gtk.EventBox())
        self.child.child.add(gtk.Image())
        self.child.child.child.set_from_pixbuf(pixbuf)

        self.child.child.connect('button-press-event', self.__destroy)
        self.child.child.connect('key-press-event', self.__destroy)
        self.show_all()

    def __destroy(self, *args):
        self.destroy()

class ResizeImage(gtk.Image):
    """Automatically resizes to the maximum height given by its
    parent container. If resize is True, size and max will be ignored"""
    def __init__(self, resize, size=0, max=128):
        super(ResizeImage, self).__init__()
        self.__path = None
        self.__ignore = False
        self.__resize = resize
        self.__size = size
        self.__max_size = max
        self.__no_cover = None
        if self.__resize:
            self.set_size_request(-1, 0)
            self.connect("size-allocate", self.__allocate)

    def set_path(self, path):
        if path != self.__path:
            self.__path = path
            if self.__resize:
                self.queue_resize()
            else:
                self.__update_image()

    def __allocate(self, img, alloc):
        self.__size = alloc.height - 2
        if not self.__ignore:
            self.__update_image()

    def __get_no_cover(self, width, height):
        size = min(width, height)
        if self.__no_cover is None or min(self.__no_cover.get_width(),
            self.__no_cover.get_height()) != size:
            theme = gtk.icon_theme_get_default()
            try:
                self.__no_cover = theme.load_icon(
                    "quodlibet-missing-cover", size, 0)
            except gobject.GError: pass
            else:
                self.__no_cover = thumbnails.scale(
                    self.__no_cover, (size, size))
        return self.__no_cover

    def __update_image(self):
        height = self.__size
        if not height: return

        if self.__resize:
            height = min(self.__max_size, height)
            width = self.__max_size
        else:
            width = height

        if self.__path is None:
            pixbuf = self.__get_no_cover(width, height)
        else:
            try:
                round_thumbs = config.getboolean("albumart", "round")
                pixbuf = thumbnails.get_thumbnail(self.__path, (width, height))
                pixbuf = thumbnails.add_border(pixbuf, 80, round_thumbs)
            except gobject.GError:
                pixbuf = self.__get_no_cover(width, height)

        self.set_from_pixbuf(pixbuf)
        if self.__resize:
            self.__ignore = True
            self.__sig = self.connect_after("size-allocate",
                self.__stop_ignore)

    def __stop_ignore(self, *args):
        self.__ignore = False
        self.disconnect(self.__sig)

class CoverImage(gtk.EventBox):
    __file = None
    __current_bci = None

    def __init__(self, resize=False, size=70, song=None):
        super(CoverImage, self).__init__()
        self.add(ResizeImage(resize, size))
        self.connect('button-press-event', self.__show_cover)
        self.set_song(self, song)
        self.show_all()

    def set_song(self, activator, song):
        if not self.child: return
        if song:
            self.__file = song.find_cover()
            self.child.set_path(self.__file and self.__file.name)
        else:
            self.child.set_path(None)
        self.__song = song

    def refresh(self):
        if not (self.child and self.__song): return
        print_d("Refreshing icon for %s." % self.__song("~filename"), self)
        self.__file = self.__song.find_cover()
        self.child.set_path(self.__file and self.__file.name)

    def __nonzero__(self):
        return bool(self.__file)

    def __reset_bci(self, bci):
        self.__current_bci = None

    def __show_cover(self, box, event):
        """Show the cover as a detached BigCenteredImage.
        If one is already showing, destroy it instead
        If there is no image, run the AlbumArt plugin
        """
        if (not self.__song or event.button != 1 or
                event.type != gtk.gdk.BUTTON_PRESS):
            return

        if self.__file:
            if self.__current_bci is not None:
                # We're displaying it; destroy it.
                self.__current_bci.destroy()
                return
            # We're not displaying it yet; display it.
            while self.__file:
                try:
                    self.__current_bci = BigCenteredImage(
                        self.__song.comma("album"), self.__file.name, self)
                except gobject.GError: # reload in case the image file is gone
                    self.set_song(self, self.__song)
                else:
                    self.__current_bci.connect('destroy', self.__reset_bci)
                    break
        else:
            from quodlibet.qltk.songsmenu import SongsMenu
            for pk in SongsMenu.handler.plugins:
                if pk.PLUGIN_ID == ALBUM_ART_PLUGIN_ID:
                    plugin = pk([self.__song])
                    print_d("Running \"%s\" plugin... (%r)" %
                            (ALBUM_ART_PLUGIN_ID, plugin))
                    plugin.plugin_album([self.__song])
                    return
            print_d("Couldn't find \"%s\" plugin. Is it installed and enabled?"
                    % ALBUM_ART_PLUGIN_ID)

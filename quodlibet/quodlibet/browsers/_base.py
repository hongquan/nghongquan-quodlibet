# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gobject
import gtk

import quodlibet.library

from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.util.library import background_filter

# Browers are how the audio library is presented to the user; they
# create the list of songs that MainSongList is filled with, and pass
# them back via a callback function.
class Browser(object):
    # Unfortunately, GObjects do not play with Python multiple inheritance.
    # So, we need to reasssign this in every subclass.
    __gsignals__ = {
        'songs-selected':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, object))
        }

    # The browser's name, without an accelerator.
    name = _("Library Browser")
    # The name, with an accelerator.
    accelerated_name = _("Library Browser")
    # Priority in the menu list (0 is first, higher numbers come later)
    priority = 100
    # Whether the browser should appear in the Music->Browse menu.
    in_menu = True

    # Packing options. False if the browser should be packed into the
    # window's VBox with expand=False. A subclass of Paned to automatically
    # pack the browser into the first and the MainSongList into the second
    # pane. If you override the pack() method this will not be called.
    expand = None

    # For custom packing, define a function that returns a Widget with the
    # browser and MainSongList both packed into it. If you need
    # a custom pack() method, you probably also need a custom unpack()
    # method.
    def pack(self, songpane):
        if self.expand is not None:
            container = self.expand()
            container.pack1(self, resize=True)
            container.pack2(songpane, resize=True)
        else:
            container = gtk.VBox(spacing=6)
            container.pack_start(self, expand=False)
            container.pack_start(songpane)
        return container

    # Unpack the browser and songlist when switching browsers in the main
    # window. The container will be automatically destroyed afterwards.
    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

    # If true, the global filter will be applied by MainSongList to
    # the songs returned.
    background = True

    # A list of column headers to display; None means all are okay.
    headers = None

    # Per-browser remote commands.
    commands = {}

    # Called after library and MainWindow initialization, before the
    # GTK main loop starts.
    def init(klass, library): pass
    init = classmethod(init)

    # Deprecated: use active_filter instead
    def dynamic(self, song):
        if callable(self.active_filter):
            ret = self.active_filter(song)
            if ret is not None:
                return ret
        return True

    # A callable that returns True if the passed song should be in the
    # song list, False if not and None if no filter is active.
    # Used for adding new songs to the song list or
    # dynamic playlist removal when a song ends.
    # def active_filter(self, song): ...
    active_filter = None

    # Save/restore selected songlist. Browsers should save whatever
    # they need to recreate the criteria for the current song list (not
    # the list itself). restore is called at startup if the browser
    # is the first loaded.
    def save(self): raise NotImplementedError
    def restore(self): raise NotImplementedError

    # Called after restore/activate or after the browser is loaded.
    # restored is True if restore was called.
    def finalize(self, restored): pass

    # Decides whether "filter on foo" menu entries are available.
    def can_filter(self, key): return False

    # Actually do the filtering (with a union of values).
    def filter(self, key, values): raise NotImplementedError

    # Scroll to something related to the given song.
    def scroll(self, song): pass

    # Do whatever is needed to emit songs-selected again.
    def activate(self): raise NotImplementedError

    # Called when the song list is reordered. If it's not callable
    # but true, no call is made but the song list is still reorderable.
    # def reordered(self, songlist): ...
    reordered = None

    # Called with the SongList and a list of songs when songs are dropped
    # but the song list does not support reordering. Adding the songs to
    # the list is the browser's responsibility. This function should
    # return True if the drop was successful.
    # def dropped(self, songlist, songs): ... return True
    dropped = None

    # An AccelGroup that is added to / removed from the window where
    # the browser is.
    accelerators = None

    # This method returns a gtk.Menu, probably a SongsMenu. After this
    # menu is returned the SongList may modify it further.
    def Menu(self, songs, songlist, library):
        menu = SongsMenu(
            library, songs, delete=True, accels=songlist.accelerators,
            parent=self)
        return menu

    def statusbar(self, i):
        return ngettext(
            "%(count)d song (%(time)s)", "%(count)d songs (%(time)s)", i)

    # Return a list of unique values for the given tag. This needs to be
    # here since not all browsers pull from the default library.
    def list(self, tag):
        library = quodlibet.library.library
        bg = background_filter()
        if bg:
            songs = filter(bg, library.itervalues())
            tags = set()
            for song in songs:
                tags.update(song.list(tag))
            return list(tags)
        return library.tag_values(tag)

    # Reset all filters and display the whole library.
    def unfilter(self):
        pass

    # Replay Gain profiles for this browser.
    replaygain_profiles = None

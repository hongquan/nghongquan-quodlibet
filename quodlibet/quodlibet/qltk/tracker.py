# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time

import gtk.gdk
import gobject

from quodlibet import const
from quodlibet import config
from quodlibet import util
from quodlibet.qltk.msg import ErrorMessage

MAX_ERRORS = 50

class SongTracker(object):
    def __init__(self, librarian, player, pl):
        player.connect_object('song-ended', self.__end, librarian, pl)
        player.connect_object('song-started', self.__start, librarian)
        player.connect('error', self.__error, librarian)
        gobject.timeout_add(1000, self.__timer, librarian, player)
        self.__errors_in_a_row = 0
        self.elapsed = 0
        gtk.quit_add(1, self.__quit, librarian, player)

    def __error(self, player, song, error, lock, librarian):
        newstr = u"%s: %s\n\n" % (
            util.decode(time.asctime(), const.ENCODING), error)
        self.__errors_in_a_row += 1
        if self.__errors_in_a_row > MAX_ERRORS:
            self.__errors_in_a_row = 0
            if lock:
                gtk.gdk.threads_enter()
            ErrorMessage(None, _("Too Many Errors"),
                         _("Stopping playback because there were %d errors "
                           "in a row.") % MAX_ERRORS).run()
            player.go_to(None)
            player.paused = True
            if lock:
                gtk.gdk.threads_leave()
        song["~errors"] = newstr + song.get("~errors", "")

    def __start(self, librarian, song):
        self.elapsed = 0
        if song is not None:
            if song.multisong:
                song["~#lastplayed"] = int(time.time())
                song["~#playcount"] = song.get("~#playcount", 0) + 1
            else:
                config.set("memory", "song", song["~filename"])
            song["~#laststarted"] = int(time.time())
            librarian.changed([song])

    def __end(self, librarian, song, ended, pl):
        if song is None or song.multisong:
            return
        elif self.elapsed > 0.5 * song.get("~#length", 1):
            song["~#lastplayed"] = int(time.time())
            song["~#playcount"] = song.get("~#playcount", 0) + 1
            librarian.changed([song])
        elif pl.current is not song:
            if "~errors" not in song:
                song["~#skipcount"] = song.get("~#skipcount", 0) + 1
            librarian.changed([song])

        if not ended and song and "~errors" in song:
            del(song["~errors"])
            self.__errors_in_a_row = 0

    def __quit(self, librarian, player):
        config.set("memory", "seek", player.get_position())
        player.emit('song-ended', player.song, True)
        return 0

    def __timer(self, librarian, player):
        # This is easier, if lamer, QLScrobbler's time() shenanigans
        if not player.paused:
            self.elapsed += 1
        return True

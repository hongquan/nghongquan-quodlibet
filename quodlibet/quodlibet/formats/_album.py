# -*- coding: utf-8 -*-
# Copyright 2004-2010 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gtk
import gobject

from quodlibet import util
from quodlibet import config
from quodlibet import stock
from quodlibet.formats._audio import PEOPLE, TAG_TO_SORT
from quodlibet.util import thumbnails

ELPOEP = list(reversed(PEOPLE))
PEOPLE_SCORE = [100**i for i in xrange(len(PEOPLE))]

NUM_DEFAULT_FUNCS = {
    "length": "sum",
    "playcount": "sum",
    "added": "max",
    "lastplayed": "max",
    "laststarted": "max",
    "mtime": "max",
    "bitrate": "avg",
    "rating": "avg",
    "skipcount": "avg",
    "year": "min",
}

NUM_FUNCS = {
    "max": max, "min": min, "sum": sum,
    "avg": lambda s: float(sum(s)) / len(s)
}

class Album(object):
    """Simliar to an AudioFile, except it doesn't look like a dict because
    there is no easy way to access tags."""

    try:
        cover = gtk.gdk.pixbuf_new_from_file_at_size(stock.NO_ALBUM, 48, 48)
    except RuntimeError:
        cover = None

    scanned = False

    peoplesort = property(lambda self: self.__get_sort("~peoplesort"))
    date = property(lambda self: self.get("date"))
    title = property(lambda self: self.get("album"))

    def __init__(self, song):
        self.songs = set()
        #albumsort is part of the album_key, so every song has the same
        self.sort = util.human_sort_key(song("albumsort"))
        self.key = song.album_key
        self.__cache = {}
        self.__sortcache = {}

    def finalize(self):
        """Call this after songs got added or removed"""
        self.__cache.clear()
        self.__sortcache.clear()

    def get(self, key, default=u"", connector=u" - ",
        to_cache=frozenset(("~peoplesort", "album", "~people", "date"))):

        if key in to_cache:
            cache_key = (key, default, connector)
            val = self.__cache.get(cache_key)
            if val is None:
                val = self.__get(key, default, connector)
                self.__cache[cache_key] = val
            return val
        else:
            return self.__get(key, default, connector)

    __call__ = get

    def comma(self, key):
        value = self.get(key)
        if isinstance(value, (int, float)): return value
        return value.replace("\n", ", ")

    def list(self, key):
        if "~" in key[1:]:
            v = self.get(key, connector=u"\n")
        else: v = self.get(key)
        if v == "": return []
        else: return v.split("\n")
        return []

    def scan_cover(self):
        if self.scanned or not self.songs: return
        self.scanned = True

        song = next(iter(self.songs))
        cover = song.find_cover()

        if cover is not None:
            try:
                round = config.getboolean("settings", "round")
                self.cover = thumbnails.get_thumbnail(cover.name, (48, 48))
                self.cover = thumbnails.add_border(self.cover, 30, round)
            except gobject.GError:
                return

    def __get_sort(self, key):
        """Cache the sort keys extra, because of human sorting"""
        val = self.__sortcache.get(key)
        if val is None:
            val = self.get(key).split("\n")
            val = map(util.human_sort_key, val)
            self.__sortcache[key] = val
        return val

    def __get(self, key, default, connector):
        """This is similar to __call__ in the AudioFile class.
        All internal tags are changed to represent an album instead of a song.
        """

        if key[:1] == "~":
            key = key[1:]
            if "~" in key:
                return connector.join(map(unicode, filter(None,
                            map(self.get, util.tagsplit("~" + key))
                    )))
            elif key[:1] == "#": pass
            elif key in ("people", "peoplesort"):
                people = {}
                peoplesort = {}
                for song in self.songs:
                    # Rank people by "relevance" -- artists before composers
                    # before performers, then by number of appearances.
                    for w, k in enumerate(ELPOEP):
                        persons = song.list(k)
                        for person in persons:
                            people[person] = (people.get(person, 0) -
                                              PEOPLE_SCORE[w])
                        if k in TAG_TO_SORT:
                            persons = song.list(TAG_TO_SORT[k]) or persons
                        for person in persons:
                            peoplesort[person] = (peoplesort.get(person, 0) -
                                                  PEOPLE_SCORE[w])
                #It's cheaper to get people and peoplesort in one go
                cache_key = lambda k: (k, default, connector)
                self.__cache[cache_key("~people")] = "\n".join(
                    sorted(people.keys(), key=people.__getitem__)[:100])
                self.__cache[cache_key("~peoplesort")] = "\n".join(sorted(
                    peoplesort.keys(), key=peoplesort.__getitem__)[:100])
                return self.__cache[cache_key("~" + key)]
            elif key == "length":
                return util.format_time(self.get("~#length"))
            elif key == "long-length":
                return util.format_time_long(self.get("~#length"))
            elif key == "tracks":
                tracks = self.get("~#tracks")
                return ngettext("%d track", "%d tracks", tracks) % tracks
            elif key == "discs":
                discs = self.get("~#discs")
                if discs > 1:
                    return ngettext("%d disc", "%d discs", discs) % discs
                else: return default
            elif key == "rating":
                return util.format_rating(self.get("~#rating", 0))
            elif key == "cover":
                return ((self.cover != type(self).cover) and "y") or default
            key = "~" + key

        # Using key:<func> runs the resulting list of values
        # through the function before returning it.
        # Numeric keys without a func will default to a reasonable function
        if key.startswith("~#"):
            key = key[2:]

            if key[-4:-3] == ":":
                func = key[-3:]
                key = key[:-4]
            elif key == "tracks":
                return len(self.songs)
            elif key == "discs":
                return len(set([song("~#disc", 1) for song in self.songs]))
            elif key in NUM_DEFAULT_FUNCS:
                func = NUM_DEFAULT_FUNCS[key]
            else:
                #Unknown key. AudioFile will try to cast the values to int,
                #default to avg
                func = "avg"

            key = "~#" + key

            func = NUM_FUNCS.get(func)
            if func:
                #if none of the songs can return a numeric key
                #the album returns default
                values = (song(key) for song in self.songs)
                values = [v for v in values if v != ""]
                if values: return func(values)
                else: return default
            return default

        #Nothing special was found, so just take all values of the songs
        #and sort them by their number of appearance
        result = {}
        for song in self.songs:
            for value in song.list(key):
                result[value] = result.get(value, 0) - 1

        return "\n".join(map(lambda x: x[0],
            sorted(result.items(), key=lambda x: x[1])
        )) or default

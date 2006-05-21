# -*- coding: utf-8 -*-
# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

"""
Plugins are objects (generally classes or modules) that have the following
characteristics:

    Attributes:
        obj.PLUGIN_NAME (required)
        obj.PLUGIN_DESC (required)
        obj.PLUGIN_ICON (optional)

    Callables: (one or more required)
        obj.plugin_on_song_started(song)
        obj.plugin_on_song_ended(song, stopped)
        obj.plugin_on_changed(song)
        obj.plugin_on_removed(song)
        obj.plugin_on_paused()
        obj.plugin_on_unpaused()
        obj.plugin_on_seek(song, msec)

    All matching provided callables on a single object are called in the above
    order if they match until one returns a true value.  A plugin should
    generally only provide one of the manually invoked callables, but it's quite
    reasonable to provide many event-based callbacks.

    If a module defines __all__, only plugins whose names are listed in __all__
    will be detected. This makes using __all__ in a module-as-plugin impossible.
"""

import gobject
import gtk

import config
import qltk
import util

from traceback import print_exc

from player import PlaylistPlayer
from plugins._manager import Manager
from qltk.watcher import SongWatcher
from qltk.wlw import WritingWindow

def hascallable(obj, attr):
    return callable(getattr(obj, attr, None))

class SongWrapper(object):
    __slots__ = ['_song', '_updated', '_needs_write']

    def __init__(self, song):
        self._song = song
        self._updated = False
        self._needs_write = False

    def _was_updated(self):
        return self._updated

    def __setitem__(self, key, value):
        if key in self and self[key] == value: return
        self._updated = True
        self._needs_write = (self._needs_write or not key.startswith("~"))
        return self._song.__setitem__(key, value)

    def __delitem__(self, *args):
        retval = self._song.__delitem__(*args)
        self._updated = True
        self._needs_write = True
        return retval

    def __getattr__(self, attr):
        return getattr(self._song, attr)

    def __setattr__(self, attr, value):
        # Don't set our attributes on the song. However, we only want to
        # set attributes the song already has. So, if the attribute
        # isn't one of ours, and isn't one of the song's, hand it off
        # to our parent's attribute handler for error handling.
        if attr in self.__slots__:
            return super(SongWrapper, self).__setattr__(attr, value)
        elif hasattr(self._song, attr):
            return setattr(self._song, attr, value)
        else:
            return super(SongWrapper, self).__setattr__(attr, value)

    def __cmp__(self, other):
        try: return cmp(self._song, other._song)
        except: return cmp(self._song, other)

    def __getitem__(self, *args): return self._song.__getitem__(*args)
    def __contains__(self, key): return key in self._song
    def __call__(self, *args): return self._song(*args)

    def update(self, other):
        self._updated = True
        self._needs_write = True
        return self._song.update(other)

    def rename(self, newname):
        self._updated = True
        return self._song.rename(newname)

def ListWrapper(songs):
    def wrap(song):
        if song is None: return None
        else: return SongWrapper(song)
    return map(wrap, songs)

class PluginManager(Manager):
    """Manage event plugins."""

    library_events = [(s.replace('-', '_'), 'plugin_on_' + s.replace('-', '_'))
                      for s in gobject.signal_list_names(SongWatcher)]
    player_events = [(s.replace('-', '_'), 'plugin_on_' + s.replace('-', '_'))
                     for s in gobject.signal_list_names(PlaylistPlayer)]
    player_events.remove(('error', 'plugin_on_error'))
    all_events = library_events + player_events

    def __init__(self, watcher=None, player=None, folders=[], name=None):
        super(PluginManager, self).__init__(folders, name)
        self.byfile = {}
        self.plugins = {}
        self.watcher = watcher

        self.events = {}
        invoke = self.invoke_event
        for event, handle in self.all_events:
            self.events[event] = {}
        if watcher:
            for event, handle in self.library_events:
                def handler(watcher, *args): invoke(args[-1], *args[:-1])
                watcher.connect(event, handler, event)
        if player:
            for event, handle in self.player_events:
                def handler(player, *args): invoke(args[-1], *args[:-1])
                player.connect(event, handler, event)

    def _load(self, name, mod):        
        for pluginname in self.byfile.get(name, []):
            try: del self.plugins[pluginname]
            except KeyError: pass

        for events in self.events.values():
            try: del events[name]
            except KeyError: pass

        self.byfile[name] = []
        objects = [mod] + [getattr(mod, attr) for attr in
                            getattr(mod, '__all__', vars(mod))]
        for obj in objects:
            try: obj = obj()
            except TypeError:
                if obj is not mod: continue # let the module through
            except (KeyboardInterrupt, MemoryError):
                raise
            except:
                print_exc()
                continue

            # if an object doesn't have all required metadata, skip it
            try:
                for attr in ['PLUGIN_NAME', 'PLUGIN_DESC']:
                    getattr(obj, attr)
            except AttributeError:
                continue

            self.load_events(obj, name)

    def restore(self):
        possible = config.get("plugins", "active").split("\n")
        for plugin in self.list():
            self.enable(plugin, plugin.PLUGIN_NAME in possible)

    def save(self):
        active = [plugin.PLUGIN_NAME for plugin in self.list()
                  if self.enabled(plugin)]
        config.set("plugins", "active", "\n".join(active))

    def load_events(self, obj, name):
        for bin, attr in self.all_events:
            if hascallable(obj, attr):
                self.events[bin].setdefault(name, []).append(obj)

    def list(self):
        plugins = [plugin for handlers in self.events.values()
                   for ps in handlers.values() for plugin in ps]
        plugins = [(p.PLUGIN_NAME, p) for p in
                   dict.fromkeys(plugins).keys()]
        plugins.sort()
        return [p for (pn, p) in plugins]
                    
    def check_change_and_refresh(self, args):
        songs = filter(None, args)
        needs_write = filter(lambda s: s._needs_write, songs)

        if needs_write:
            win = WritingWindow(None, len(needs_write))
            for song in needs_write:
                try: song._song.write()
                except Exception:
                    qltk.ErrorMessage(
                        None, _("Unable to edit song"),
                        _("Saving <b>%s</b> failed. The file "
                          "may be read-only, corrupted, or you "
                          "do not have permission to edit it.")%(
                        util.escape(song('~basename')))).run()
                win.step()
            win.destroy()
            while gtk.events_pending(): gtk.main_iteration()

        changed = []
        for song in songs:
            needs_reload = []
            if song._was_updated(): changed.append(song._song)
            elif not song.valid() and song.exists():
                self.watcher.reload(song._song)
        self.watcher.changed(changed)

    def invoke_event(self, event, *args):
        try:
            args = list(args)
            if args and args[0]:
                if isinstance(args[0], dict): args[0] = SongWrapper(args[0])
                elif isinstance(args[0], list): args[0] = ListWrapper(args[0])
            for plugins in self.events[event].values():
                for plugin in plugins:
                    if not self.enabled(plugin): continue
                    handler = getattr(plugin, 'plugin_on_' + event, None)
                    if handler is not None:
                        try: handler(*args)
                        except Exception: print_exc()
        finally:
            if event not in ["removed", "changed"] and args:
                if isinstance(args[0], list):
                    self.check_change_and_refresh(args[0])
                else:
                    self.check_change_and_refresh([args[0]])

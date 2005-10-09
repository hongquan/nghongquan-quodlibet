# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import sys
import gobject, gtk, pango
import config
import parser
import player
import qltk
import util
from widgets import widgets

if sys.version_info < (2, 4): from sets import Set as set
from library import library
from browsers.base import Browser
from util import tag

class PanedBrowser(gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RVPaned

    class Pane(qltk.HintedTreeView):
        __render = gtk.CellRendererText()
        __render.set_property('ellipsize', pango.ELLIPSIZE_END)

        def __init__(self, mytag, next):
            qltk.HintedTreeView.__init__(self)
            if "~" in mytag[1:]: self.tags = filter(None, mytag.split("~"))
            else: self.tags = [mytag]
            self.__next = next
            model = gtk.ListStore(str, object)

            column = gtk.TreeViewColumn(tag(mytag), self.__render, markup=0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_fixed_width(50)
            self.append_column(column)
            self.set_model(model)

            selection = self.get_selection()
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            self.__sig = selection.connect('changed', self.__changed)

            s = widgets.watcher.connect('removed', self.__removed)
            self.connect_object('destroy', widgets.watcher.disconnect, s)

            self.connect_object('destroy', self.__destroy, model)

        def __destroy(self, model):
            self.set_model(None)
            model.clear()

        def __changed(self, selection, jump=False):
            model, rows = selection.get_selected_rows()
            if jump and rows:
                self.scroll_to_cell(rows[0][0], use_align=True, row_align=0.5)
            self.__next.fill(self.get_songs())

        def __removed(self, watcher, songs):
            model = self.get_model()
            to_remove = []
            def update(model, path, iter):
                data = model[iter][1]
                for song in songs:
                    if song in data: data.remove(song)
                if not model[iter][1]: to_remove.append(iter)
            model.foreach(update)
            map(model.remove, to_remove)

        def inhibit(self): self.get_selection().handler_block(self.__sig)
        def uninhibit(self): self.get_selection().handler_unblock(self.__sig)

        def fill(self, songs, inhibit=False):
            selected = self.get_selected()
            self.inhibit()
            values = {}
            unknown = set()
            for song in songs:
                songvals = song.listall(self.tags)
                if songvals:
                    for val in songvals:
                        values.setdefault(val, set()).add(song)
                else: unknown.add(song)
            keys = values.keys()
            keys.sort()

            model = self.get_model()
            model.clear()
            if len(keys) + bool(unknown) > 1:
                model.append(row=["<b>%s</b>" % _("All"), songs])
            for k in keys: model.append(row=[util.escape(k), values[k]])
            if unknown:
                model.append(row=["<b>%s</b>" % _("Unknown"), unknown])

            self.uninhibit()
            if selected: self.set_selected(selected, jump=True)
            else: self.set_selected(None, jump=True)

        def scroll(self, song):
            values = map(util.escape, song.listall(self.tags))
            for i, row in enumerate(iter(self.get_model())):
                if row[0] in values:
                    self.scroll_to_cell(i, use_align=True, row_align=0.5)
                    break

        def get_selected(self):
            model, rows = self.get_selection().get_selected_rows()
            return [model[row][0] for row in rows]

        def set_selected(self, values, jump=False):
            model = self.get_model()
            selection = self.get_selection()
            if values == self.get_selected(): return
            elif values is None and selection.path_is_selected((0,)): return

            self.inhibit()
            selection.unselect_all()
            first = 0
            if values is None: selection.select_path((0,))
            else:
                for i, row in enumerate(iter(model)):
                    if row[0] in values:
                        selection.select_path((i,))
                        first = first or i
            if first == 0: selection.select_path((0,))
            if jump and len(model): self.scroll_to_cell(first)
            self.uninhibit()
            self.get_selection().emit('changed')

        def get_songs(self):
            model, rows = self.get_selection().get_selected_rows()
            # No reason to look further if "All" is selected.
            if rows and rows[0][0] == 0: return model[(0,)][1]
            else:
                songs = [model[row][1] for row in rows]
                return list(reduce(set.union, songs, set()))

    def __init__(self, main=True):
        gtk.VBox.__init__(self, spacing=0)
        self.__save = main

        hb = gtk.HBox(spacing=3)
        hb2 = gtk.HBox(spacing=0)
        label = gtk.Label(_("_Search:"))
        label.set_padding(3, 0)
        search = qltk.ValidatingEntry(parser.is_valid_color)
        label.set_mnemonic_widget(search)
        label.set_use_underline(True)
        clr = gtk.Button()
        clr.add(gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_MENU))
        clr.connect_object('clicked', search.set_text, "")
        hb2.pack_start(search)
        hb2.pack_start(clr, expand=False)
        hb.pack_start(label, expand=False)
        hb.pack_start(hb2)
        self.pack_start(hb, expand=False)
        self.__refill_id = None
        self.__filter = None
        search.connect('changed', self.__filter_changed)

        self.refresh_panes(restore=False)
        self.show_all()

    def __filter_changed(self, entry):
        if self.__refill_id is not None:
            gobject.source_remove(self.__refill_id)
            self.__refill_id = None
        text = entry.get_text().decode('utf-8')
        if parser.is_parsable(text):
            if text: self.__filter = parser.parse(text).search
            else: self.__filter = None
            self.__refill_id = gobject.timeout_add(500, self.activate)

    def activate(self):
        self.__panes[0].fill(filter(self.__filter, library.values()))

    def scroll(self):
        for pane in self.__panes:
            pane.scroll(player.playlist.song)

    def refresh_panes(self, restore=True):
        try: hbox = self.get_children()[1]
        except IndexError: pass # first call
        else: hbox.destroy()

        hbox = gtk.HBox(spacing=3)
        hbox.set_homogeneous(True)
        hbox.set_size_request(100, 100)
        # fill in the pane list. the last pane reports back to us.
        self.__panes = [self]
        panes = config.get("browsers", "panes").split(); panes.reverse()
        for pane in panes:
            self.__panes.insert(0, self.Pane(pane, self.__panes[0]))
        self.__panes.pop() # remove self

        for pane in self.__panes:
            if self.__save: pane.connect('row-activated', self.__start)
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.add(pane)
            hbox.pack_start(sw)

        self.pack_start(hbox)
        if restore: self.restore()
        else:
            self.__panes[-1].inhibit()
            self.activate()
            self.__panes[-1].uninhibit()
        self.show_all()

    def __start(self, view, indices, col):
        player.playlist.reset()
        player.playlist.next()

    def can_filter(self, key):
        for pane in self.__panes:
            if key in pane.tags: return True
        else: return False

    def filter(self, key, values):
        self.__panes[-1].inhibit()
        for pane in self.__panes:
            if key in pane.tags:
                pane.set_selected(map(util.escape, values), True)
            else: pane.set_selected(None, True)
        self.__panes[-1].uninhibit()
        self.__panes[-1].get_selection().emit('changed')

    def save(self):
        selected = []
        for pane in self.__panes:
            selected.append("\t".join(pane.get_selected()))
        config.set("browsers", "pane_selection", "\n".join(selected))

    def restore(self):
        selected = config.get("browsers", "pane_selection").split("\n")
        if len(selected) == len(self.__panes):
            self.__panes[-1].inhibit()
            for values, pane in zip(selected, self.__panes[:-1]):
                pane.set_selected(values.split("\t"), True)
            self.__panes[-1].uninhibit()
            self.__panes[-1].set_selected(selected[-1].split("\t"), True)

    def __refresh(self, watcher):
        self.activate()

    def fill(self, songs):
        if self.__save: self.save()
        self.emit('songs-selected', list(songs), None)

gobject.type_register(PanedBrowser)

browsers = [(3, _("_Paned Browser"), PanedBrowser, True)]

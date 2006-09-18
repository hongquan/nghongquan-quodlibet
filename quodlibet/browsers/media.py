# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import sys

import gtk
import gtk.gdk as gdk
import pango

import config
import qltk
import util
import devices

from browsers._base import Browser
from formats._audio import AudioFile
from qltk.views import AllTreeView
from qltk.songsmenu import SongsMenu
from qltk.wlw import WaitLoadWindow, WaitLoadBar
from qltk.browser import LibraryBrowser
from qltk.delete import DeleteDialog

class DeviceProperties(gtk.Dialog):
    def __init__(self, parent, device):
        self.__device = device

        super(DeviceProperties, self).__init__(
            _("Device Properties"), qltk.get_top_parent(parent),
            buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.set_default_size(400, -1)
        self.connect('response', self.__close)

        table = gtk.Table()
        table.set_border_width(8)
        table.set_row_spacings(8)
        table.set_col_spacings(8)
        self.vbox.pack_start(table, expand=False)

        props = []

        props.append((_("Device:"), device.dev, None))
        props.append((_("Mountpoint:"),
            device.mountpoint or _("<i>Not mounted</i>"), None))
        props.append((None, None, None))

        entry = gtk.Entry()
        entry.set_text(device['name'])
        props.append((_("_Name:"), entry, 'name'))

        y = 0
        for title, value, key in props + device.Properties():
            if title == None:
                table.attach(gtk.HSeparator(), 0, 2, y, y + 1)
            else:
                if key and isinstance(value, gtk.CheckButton):
                    value.set_label(title)
                    value.set_use_underline(True)
                    value.connect('toggled', self.__changed, key)
                    table.attach(value, 0, 2, y, y + 1, xoptions=gtk.FILL)
                else:
                    label = gtk.Label()
                    label.set_markup("<b>%s</b>" % util.escape(title))
                    label.set_alignment(0.0, 0.5)
                    table.attach(label, 0, 1, y, y + 1, xoptions=gtk.FILL)
                    if key and isinstance(value, gtk.Widget):
                        widget = value
                        label.set_mnemonic_widget(widget)
                        label.set_use_underline(True)
                        widget.connect('changed', self.__changed, key)
                    else:
                        widget = gtk.Label(value)
                        widget.set_use_markup(True)
                        widget.set_selectable(True)
                        widget.set_alignment(0.0, 0.5)
                    table.attach(widget, 1, 2, y, y + 1)
            y += 1
        self.show_all()

    def __changed(self, widget, key):
        if isinstance(widget, gtk.Entry):
            value = widget.get_text()
        elif isinstance(widget, gtk.SpinButton):
            value = widget.get_value()
        elif isinstance(widget, gtk.CheckButton):
            value = widget.get_active()
        else:
            raise NotImplementedError
        self.__device[key] = value

    def __close(self, dialog, response):
        dialog.destroy()
        devices.write()

# This will be included in SongsMenu
class Menu(gtk.Menu):
    def __init__(self, songs, library):
        super(Menu, self).__init__()
        for device, pixbuf in MediaDevices.devices():
            x, y = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)
            pixbuf = pixbuf.scale_simple(x, y, gdk.INTERP_BILINEAR)
            i = gtk.ImageMenuItem(device['name'])
            i.set_sensitive(device.is_connected())
            i.get_image().set_from_pixbuf(pixbuf)
            i.connect_object(
                'activate', self.__copy_to_device, device, songs, library)
            self.append(i)

    @staticmethod
    def __copy_to_device(device, songs, library):
        if len(MediaDevices.instances()) > 0:
            browser = MediaDevices.instances()[0]
        else:
            win = LibraryBrowser(MediaDevices, library)
            browser = win.browser
        browser.select(device)
        browser.dropped(browser.get_toplevel().songlist, songs)

class MediaDevices(gtk.VBox, Browser, util.InstanceTracker):
    __gsignals__ = Browser.__gsignals__

    name = _("Media Devices")
    accelerated_name = _("_Media Devices")
    priority = 25
    replaygain_profiles = ['track']

    __devices = gtk.ListStore(object, gdk.Pixbuf)
    __busy = False

    @staticmethod
    def cell_data(col, render, model, iter):
        device = model[iter][0]
        if device.is_connected():
            render.markup = "<b>%s</b>" % util.escape(device['name'])
        else:
            render.markup = util.escape(device['name'])
        render.set_property('markup', render.markup)

    @classmethod
    def init(klass, library):
        devices._hal.connect_to_signal(
            'DeviceAdded', klass.__hal_device_added)
        devices._hal.connect_to_signal(
            'DeviceRemoved', klass.__hal_device_removed)
        for udi in devices.discover():
            klass.__hal_device_added(udi)

    @classmethod
    def devices(klass):
        return [(row[0], row[1]) for row in klass.__devices]

    @classmethod
    def __hal_device_added(klass, udi):
        device = devices.get_by_udi(udi)
        if device != None:
            klass.__add_device(device)

    @classmethod
    def __hal_device_removed(klass, udi):
        for row in klass.__devices:
            if row[0].udi == udi:
                klass.__devices.remove(row.iter)
                break

    @classmethod
    def __add_device(klass, device):
        pixbuf = gdk.pixbuf_new_from_file_at_size(
            device.icon, 24, 24)
        klass.__devices.append(row=[device, pixbuf])

    def __init__(self, library, player):
        super(MediaDevices, self).__init__(spacing=6)
        self._register_instance()

        self.__cache = {}
        self.__last = None

        # Device list on the left pane
        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.pack_start(swin)

        self.__view = view = AllTreeView()
        view.set_reorderable(True)
        view.set_model(self.__devices)
        view.set_rules_hint(True)
        view.set_headers_visible(False)
        view.get_selection().set_mode(gtk.SELECTION_BROWSE)
        view.get_selection().connect_object('changed', self.__refresh, False)
        view.connect('popup-menu', self.__popup_menu, library)
        if player: view.connect('row-activated', lambda *a: player.reset())
        swin.add(view)

        col = gtk.TreeViewColumn("Devices")
        view.append_column(col)

        render = gtk.CellRendererPixbuf()
        col.pack_start(render, expand=False)
        col.add_attribute(render, 'pixbuf', 1)

        self.__render = render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        render.connect('edited', self.__edited)
        col.pack_start(render)
        col.set_cell_data_func(render, MediaDevices.cell_data)

        self.__refresh_button = refresh = qltk.Button(
            _("_Refresh"), gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU)
        refresh.connect_object('clicked', self.__refresh, True)
        refresh.set_sensitive(False)
        self.pack_start(refresh, expand=False)

        self.__eject_button = eject = qltk.Button(
            _("_Eject"), gtk.STOCK_DISCONNECT, gtk.ICON_SIZE_MENU)
        eject.connect('clicked', self.__eject)
        eject.set_sensitive(False)
        self.pack_start(eject, expand=False)

        # Device info on the right pane
        self.__header = table = gtk.Table()
        table.set_col_spacings(8)

        self.__device_icon = icon = gtk.Image()
        icon.set_size_request(48, 48)
        table.attach(icon, 0, 1, 0, 2, 0)

        self.__device_name = label = gtk.Label()
        label.set_alignment(0, 0)
        table.attach(label, 1, 3, 0, 1)

        self.__device_space = label = gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 1, 2)

        self.__progress = progress = gtk.ProgressBar()
        progress.set_size_request(150, -1)
        table.attach(progress, 2, 3, 1, 2, xoptions=0, yoptions=0)

        self.accelerators = gtk.AccelGroup()
        key, mod = gtk.accelerator_parse('F2')
        self.accelerators.connect_group(key, mod, 0, self.__rename)

        self.__statusbar = WaitLoadBar()

        self.show_all()

    def pack(self, songpane):
        self.__vbox = vbox = gtk.VBox(spacing=6)
        vbox.pack_start(self.__header, expand=False)
        vbox.pack_start(songpane)
        vbox.pack_start(self.__statusbar, expand=False)

        vbox.show()
        self.__header.show_all()
        self.__header.hide()
        self.__statusbar.show_all()
        self.__statusbar.hide()

        self.__paned = paned = qltk.RHPaned()
        paned.pack1(self)
        paned.pack2(vbox)
        return paned

    def unpack(self, container, songpane):
        self.__vbox.remove(songpane)
        self.__paned.remove(self)

    def Menu(self, songs, songlist, library):
        menu = super(MediaDevices, self).Menu(songs, songlist, library)
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            device = model[iter][0]
            if device.delete:
                delete = gtk.ImageMenuItem(gtk.STOCK_DELETE)
                delete.connect_object('activate',
                    self.__delete_songs, songlist, songs)
                menu.append(delete)
        return menu

    def activate(self):
        self.__refresh()

    def save(self):
        selection = self.__view.get_selection()
        model, iter = selection.get_selected()
        config.set('browsers', 'media', model[iter][0]['name'])

    def restore(self):
        try: name = config.get('browsers', 'media')
        except: pass
        else:
            for row in self.__devices:
                if row[0]['name'] == name: break
            else: return
            selection = self.__view.get_selection()
            selection.unselect_all()
            selection.select_iter(row.iter)

    def select(self, device):
        for row in self.__devices:
            if row[0] == device: break
        else: return

        # Force a full refresh
        try: del self.__cache[device.udi]
        except KeyError: pass

        selection = self.__view.get_selection()
        selection.unselect_all()
        selection.select_iter(row.iter)

    def dropped(self, songlist, songs):
        return self.__copy_songs(songlist, songs)

    def __popup_menu(self, view, library):
        model, iter = view.get_selection().get_selected()
        device = model[iter][0]

        if device.is_connected() and not self.__busy:
            songs = self.__list_songs(device)
        else:
            songs = []
        menu = SongsMenu(library, songs, playlists=False,
                         devices=False, remove=False)

        menu.preseparate()

        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        props.connect_object( 'activate', self.__properties, model[iter][0])
        props.set_sensitive(not self.__busy)
        menu.prepend(props)

        ren = qltk.MenuItem(_("_Rename"), gtk.STOCK_EDIT)
        keyval, mod = gtk.accelerator_parse("F2")
        ren.add_accelerator(
            'activate', self.accelerators, keyval, mod, gtk.ACCEL_VISIBLE)
        def rename(path):
            self.__render.set_property('editable', True)
            view.set_cursor(path, view.get_columns()[0], start_editing=True)
        ren.connect_object('activate', rename, model.get_path(iter))
        menu.prepend(ren)

        menu.preseparate()

        eject = qltk.MenuItem(_("_Eject"), gtk.STOCK_DISCONNECT)
        eject.set_sensitive(
            not self.__busy and device.eject and device.is_connected())
        eject.connect_object('activate', self.__eject, None)
        menu.prepend(eject)

        refresh = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        refresh.set_sensitive(device.is_connected())
        refresh.connect_object('activate', self.__refresh, True)
        menu.prepend(refresh)

        menu.show_all()
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True

    def __properties(self, device):
        DeviceProperties(self, device).run()
        self.__set_name(device)

    def __rename(self, group, acceleratable, keyval, modifier):
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            self.__render.set_property('editable', True)
            self.__view.set_cursor(model.get_path(iter),
                                   self.__view.get_columns()[0],
                                   start_editing=True)

    def __edited(self, render, path, newname):
        self.__devices[path][0]['name'] = newname
        self.__set_name(self.__devices[path][0])
        render.set_property('editable', False)
        devices.write()

    def __set_name(self, device):
        self.__device_name.set_markup(
            '<span size="x-large"><b>%s</b></span>' %
                util.escape(device['name']))

    def __refresh(self, rescan=False):
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            path = model[iter].path
            if not rescan and self.__last == path: return
            self.__last = path

            device = model[iter][0]
            self.__device_icon.set_from_file(device.icon)
            self.__set_name(device)

            songs = []
            if device.is_connected():
                self.__header.show_all()
                self.__eject_button.set_sensitive(bool(device.eject))
                self.__refresh_button.set_sensitive(True)
                self.__refresh_space(device)

                try: songs = self.__list_songs(device, rescan)
                except NotImplementedError: pass
            else:
                self.__eject_button.set_sensitive(False)
                self.__refresh_button.set_sensitive(False)
                self.__header.hide()
            self.emit('songs-selected', songs, True)
        else:
            self.__last = None

    def __refresh_space(self, device):
        try: space, free = device.get_space()
        except NotImplementedError:
            self.__device_space.set_text("")
            self.__progress.hide()
        else:
            used = space - free
            fraction = float(used) / space

            self.__device_space.set_markup(
                _("<b>%s</b> used, <b>%s</b> available") %
                    (util.format_size(used), util.format_size(free)))
            self.__progress.set_fraction(fraction)
            self.__progress.set_text("%.f%%" % round(fraction * 100))
            self.__progress.show()

    def __list_songs(self, device, rescan=False):
        if rescan or not device.udi in self.__cache:
            self.__busy = True
            self.__cache[device.udi] = device.list(self.__statusbar)
            self.__busy = False
        return self.__cache[device.udi]

    def __check_device(self, device, message):
        if not device.is_connected():
            qltk.WarningMessage(
                self, message,
                _("The device <b>%s</b> is not connected.")
                    % util.escape(device['name'])
            ).run()
            return False
        return True

    def __copy_songs(self, songlist, songs):
        model, iter = self.__view.get_selection().get_selected()
        if not iter: return False

        device = model[iter][0]
        if not self.__check_device(device, _("Unable to copy songs")):
            return False

        self.__busy = True

        wlb = self.__statusbar
        wlb.setup(len(songs), _("Copying <b>%s</b>"), "")
        wlb.show()

        model = songlist.get_model()
        for song in songs:
            label = util.escape(song('~artist~title'))
            if wlb.step(label):
                wlb.hide()
                break

            songlist.scroll_to_cell(model[-1].path)
            while gtk.events_pending(): gtk.main_iteration()

            space, free = device.get_space()
            if free < os.path.getsize(song['~filename']):
                wlb.hide()
                qltk.WarningMessage(
                    self, _("Unable to copy song"),
                    _("The device has not enough free space for this song.")
                ).run()
                break

            status = device.copy(songlist, song)
            if isinstance(status, AudioFile):
                model.append([status])
                try: self.__cache[device.udi].append(song)
                except KeyError: pass
                self.__refresh_space(device)
            else:
                msg = _("The song <b>%s</b> could not be copied.")
                if type(status) == str:
                    msg += "\n\n"
                    msg += _("<b>Error:</b> %s") % util.escape(status)
                qltk.WarningMessage(
                    self, _("Unable to copy song"),
                    msg % label).run()

        if device.cleanup and not device.cleanup(wlb, 'copy'):
            pass
        else:
            wlb.hide()

        self.__busy = False
        return True

    def __delete_songs(self, songlist, songs):
        model, iter = self.__view.get_selection().get_selected()
        if not iter: return False

        device = model[iter][0]
        if not self.__check_device(device, _("Unable to delete songs")):
            return False

        song_titles = [s('~artist~title') for s in songs]
        if DeleteDialog(self, song_titles, False, True).run() != 2:
            return False

        self.__busy = True

        wlb = self.__statusbar
        wlb.setup(len(songs), _("Deleting <b>%s</b>"), "")
        wlb.show()

        model = songlist.get_model()
        for song in songs:
            label = util.escape(song('~artist~title'))
            if wlb.step(label):
                wlb.hide()
                break

            status = True
            status = device.delete(songlist, song)
            if status:
                model.remove(model.find(song))
                try: self.__cache[device.udi].remove(song)
                except (KeyError, ValueError): pass
                self.__refresh_space(device)
            else:
                msg = _("The song <b>%s</b> could not be deleted.")
                if type(status) == str:
                    msg += "\n\n"
                    msg += _("<b>Error:</b> %s") % status
                qltk.WarningMessage(
                    self, _("Unable to delete song"),
                    msg % label).run()

        if device.cleanup and not device.cleanup(wlb, 'delete'):
            pass
        else:
            wlb.hide()

        self.__busy = False

    def __eject(self, button):
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            device = model[iter][0]
            status = device.eject()
            if status == True:
                self.__refresh(True)
            else:
                qltk.ErrorMessage(
                    self, _("Unable to eject device"),
                    _("Ejecting <b>%s</b> failed with the following error:\n\n"
                      + status) % device['name']).run()

browsers = [MediaDevices]

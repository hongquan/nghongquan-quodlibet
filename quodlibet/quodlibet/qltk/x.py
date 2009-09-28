# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Things that are more or less direct wrappers around GTK widgets to
# ease constructors.

import gobject
import gtk

from quodlibet import util

class Window(gtk.Window):
    """A Window that binds the ^W accelerator to close. This should not
    be used for dialogs; Escape closes (cancels) those."""
    
    __gsignals__ = {"close-accel": (
        gobject.SIGNAL_RUN_LAST|gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ())}
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)
        self.__accels = gtk.AccelGroup()
        self.add_accel_group(self.__accels)
        self.add_accelerator(
            'close-accel', self.__accels, ord('w'), gtk.gdk.CONTROL_MASK, 0)
        esc, mod = gtk.accelerator_parse("Escape")
        self.add_accelerator('close-accel', self.__accels, esc, mod, 0)

    def set_transient_for(self, parent):
        super(Window, self).set_transient_for(parent)
        if parent is not None:
            self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)

    def do_close_accel(self):
        if not self.emit('delete-event', gtk.gdk.Event(gtk.gdk.DELETE)):
            self.destroy()

class Notebook(gtk.Notebook):
    """A regular gtk.Notebook, except when appending a page, if no
    label is given, the page's 'title' attribute (either a string or
    a widget) is used."""
    
    def append_page(self, page, label=None):
        if label is None:
            try: label = page.title
            except AttributeError:
                raise TypeError("no page.title and no label given")

        if not isinstance(label, gtk.Widget):
            label = gtk.Label(label)
        super(Notebook, self).append_page(page, label)

def Frame(label, child=None):
    """A gtk.Frame with no shadow, 12px left padding, and 3px top padding."""
    frame = gtk.Frame()
    label_w = gtk.Label()
    label_w.set_markup("<b>%s</b>" % util.escape(label))
    align = gtk.Alignment(xalign=0.0, yalign=0.0, xscale=1.0, yscale=1.0)
    align.set_padding(3, 0, 12, 0)
    frame.add(align)
    frame.set_shadow_type(gtk.SHADOW_NONE)
    frame.set_label_widget(label_w)
    if child:
        align.add(child)
        label_w.set_mnemonic_widget(child)
        label_w.set_use_underline(True)
    return frame

def MenuItem(label, stock_id):
    """An ImageMenuItem with a custom label and stock image."""
    item = gtk.ImageMenuItem(label)
    item.get_image().set_from_stock(stock_id, gtk.ICON_SIZE_MENU)
    return item

def Button(label, stock_id, size=gtk.ICON_SIZE_BUTTON):
    """A Button with a custom label and stock image. It should pack
    exactly like a stock button."""
    align = gtk.Alignment(xscale=0.0, yscale=1.0, xalign=0.5, yalign=0.5)
    hbox = gtk.HBox(spacing=2)
    hbox.pack_start(gtk.image_new_from_stock(stock_id, size))
    label = gtk.Label(label)
    label.set_use_underline(True)
    hbox.pack_start(label)
    align.add(hbox)
    button = gtk.Button()
    button.add(align)
    return button

class RPaned(object):
    """A Paned that supports relative (percentage) width/height setting."""

    def get_relative(self):
        """Return the relative position of the separator, [0..1]."""
        if self.get_property('max-position') > 0:
            return float(self.get_position())/self.get_property('max-position')
        else: return 0.5

    def set_relative(self, v):
        """Set the relative position of the separator, [0..1]."""
        return self.set_position(int(v * self.get_property('max-position')))

class RHPaned(RPaned, gtk.HPaned): pass
class RVPaned(RPaned, gtk.VPaned): pass

def ClearButton(entry=None):
    clear = gtk.Button()
    clear.add(gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_MENU))
    clear.set_tooltip_text(_("Clear search"))
    if entry is not None:
        clear.connect_object('clicked', entry.set_text, '')
    return clear

def EntryCompletion(words):
    """Simple string completion."""
    model = gtk.ListStore(str)
    for word in sorted(words):
        model.append(row=[word])
    comp = gtk.EntryCompletion()
    comp.set_model(model)
    comp.set_text_column(0)
    return comp

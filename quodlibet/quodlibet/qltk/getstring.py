# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk
from gi.repository import Gdk

from quodlibet.qltk.entry import UndoEntry

class GetStringDialog(Gtk.Dialog):
    def __init__(
        self, parent, title, text, options=[], okbutton=Gtk.STOCK_OPEN):
        super(GetStringDialog, self).__init__(title, parent)
        self.set_border_width(6)
        self.set_resizable(False)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         okbutton, Gtk.ResponseType.OK)
        self.vbox.set_spacing(6)
        self.set_default_response(Gtk.ResponseType.OK)

        box = Gtk.VBox(spacing=6)
        lab = Gtk.Label(label=text)
        box.set_border_width(6)
        lab.set_line_wrap(True)
        lab.set_justify(Gtk.Justification.CENTER)
        box.pack_start(lab, True, True, 0)

        if options:
            self._entry = Gtk.ComboBoxText.new_with_entry()
            for o in options: self._entry.append_text(o)
            self._val = self._entry.get_child()
            box.pack_start(self._entry, True, True, 0)
        else:
            self._val = UndoEntry()
            box.pack_start(self._val, True, True, 0)

        self.vbox.pack_start(box, True, True, 0)
        self.get_child().show_all()

    def _verify_clipboard(self, text):
        """Return an altered text or None if the content was invalid."""
        return

    def run(self, text="", clipboard=False, test=False):
        """Shows the dialog and returns the entered value.

        If clipboard is set, the initial value will be pulled from the
        clipboard and can be verified/altered by _verify_clipboard. In case the
        verification fails text will be used as fallback"""

        self.show()
        if clipboard:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clip = clipboard.wait_for_text()
            if clip is not None:
                clip = self._verify_clipboard(clip)
            if clip is not None:
                text = clip
        self._val.set_text(text)
        self._val.set_activates_default(True)
        self._val.grab_focus()
        resp = Gtk.ResponseType.OK
        if not test:
            resp = super(GetStringDialog, self).run()
        if resp == Gtk.ResponseType.OK:
            value = self._val.get_text()
        else: value = None
        self.destroy()
        return value

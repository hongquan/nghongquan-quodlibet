# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk
import mutagen

from quodlibet.qltk import gtk_version, pygobject_version
from quodlibet import const
from quodlibet import formats
from quodlibet.util import fver


class AboutDialog(Gtk.AboutDialog):
    def __init__(self, parent, player, name, icon):
        super(AboutDialog, self).__init__()
        self.set_transient_for(parent)
        self.set_program_name(name)
        self.set_version(const.VERSION)
        self.set_authors(const.AUTHORS)
        self.set_artists(const.ARTISTS)
        self.set_logo_icon_name(icon)
        fmts = ", ".join(formats.modules)
        text = []
        text.append(_("Supported formats: %s") % fmts)
        if player:
            text.append(_("Audio device: %s") % player.name)
        text.append("Mutagen: %s" % fver(mutagen.version))
        text.append("GTK+: %s / PyGObject: %s" %(
            fver(gtk_version), fver(pygobject_version)))
        if player:
            text.append(player.version_info)
        self.set_comments("\n".join(text))
        # Translators: Replace this with your name/email to have it appear
        # in the "About" dialog.
        self.set_translator_credits(_('translator-credits'))
        self.set_website("http://code.google.com/p/quodlibet")
        self.set_copyright(
            "Copyright © 2004-2012 Joe Wreschnig, Michael Urman, & others\n"
            "<quod-libet-development@googlegroups.com>")
        self.get_child().show_all()


class AboutQuodLibet(AboutDialog):
    def __init__(self, parent, player):
        super(AboutQuodLibet, self).__init__(
            parent, player, "Quod Libet", "quodlibet")


class AboutExFalso(AboutDialog):
    def __init__(self, parent, player=None):
        super(AboutExFalso, self).__init__(
            parent, player, "Ex Falso", "exfalso")

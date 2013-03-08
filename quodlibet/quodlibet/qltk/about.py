# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import mutagen

from quodlibet import const
from quodlibet import formats
from quodlibet.util import fver

class AboutDialog(gtk.AboutDialog):
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
        text.append("GTK+: %s / PyGTK: %s" %(
            fver(gtk.gtk_version), fver(gtk.pygtk_version)))
        if player:
            text.append(player.version_info)
        self.set_comments("\n".join(text))
        self.set_translator_credits("\n".join(const.TRANSLATORS))
        self.set_website("http://code.google.com/p/quodlibet")
        self.set_copyright(
            "Copyright © 2004-2012 Joe Wreschnig, Michael Urman, & others\n"
            "<quod-libet-development@googlegroups.com>")
        self.child.show_all()


class AboutQuodLibet(AboutDialog):
    def __init__(self, parent, player):
        super(AboutQuodLibet, self).__init__(
            parent, player, "Quod Libet", "quodlibet")


class AboutExFalso(AboutDialog):
    def __init__(self, parent, player=None):
        super(AboutExFalso, self).__init__(
            parent, player, "Ex Falso", "exfalso")

# Copyright 2005 Joe Wreschnig
#           2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

import const

EDIT_TAGS = 'ql-edit-tags'
PLUGINS = 'ql-plugins'
PREVIEW = 'ql-preview'
REMOVE = 'ql-remove'
ENQUEUE = 'ql-enqueue'
PLAYLISTS = 'ql-add-to-playlist'
DEVICES = 'ql-copy-to-device'
RENAME = 'ql-rename'

def init():
    theme = gtk.icon_theme_get_default()
    theme.append_search_path(const.IMAGEDIR)

    factory = gtk.IconFactory()

    gtk.stock_add([
        (EDIT_TAGS, _("Edit _Tags"), 0, 0, ""),
        (PLUGINS, _("_Plugins"), 0, 0, ""),
        (PREVIEW, _("_Preview"), 0, 0, ""),
        (ENQUEUE, _("Add to _Queue"), 0, 0, ""),
        (PLAYLISTS, _("_Add to Playlist"), 0, 0, ""),
        (DEVICES, _("_Copy to Device"), 0, 0, ""),
        (RENAME, _("_Rename"), 0, 0, ""),
        ])

    lookup = gtk.icon_factory_lookup_default
    factory.add(EDIT_TAGS, lookup(gtk.STOCK_PROPERTIES))
    factory.add(PLUGINS, lookup(gtk.STOCK_EXECUTE))
    factory.add(PREVIEW, lookup(gtk.STOCK_CONVERT))
    factory.add(ENQUEUE, lookup(gtk.STOCK_ADD))
    factory.add(PLAYLISTS, lookup(gtk.STOCK_ADD))
    factory.add(DEVICES, lookup(gtk.STOCK_COPY))
    factory.add(RENAME, lookup(gtk.STOCK_EDIT))
    factory.add(REMOVE, lookup(gtk.STOCK_REMOVE))

    # Translators: Only translate this if it conflicts with "Delete",
    # as is the case in e.g. Finnish. It should be disambiguated as
    # "Remove from Library" (as opposed to, from playlist, from disk, etc.)
    # Don't literally translate "ql-remove". It needs an access key, so
    # a sample translation would be "_Remove from Library".
    if _("ql-remove") == "ql-remove":
        # Use explicit text instead of ambiguous "Remove". See Issue 950.
        gtk.stock_add([(REMOVE, _("_Remove from library")) +
                       gtk.stock_lookup(gtk.STOCK_REMOVE)[2:]])
    else:
        gtk.stock_add([(REMOVE, _("ql-remove"), 0, 0, "")])

    for key, name in [
        # Translators: Only translate this if GTK does so incorrectly or not
        # at all. Don't literally translate media/next/previous/play/pause.
        # This string needs an access key.
        (gtk.STOCK_MEDIA_NEXT, _('gtk-media-next')),
        # Translators: Only translate this if GTK does so incorrectly or not
        # at all. Don't literally translate media/next/previous/play/pause.
        # This string needs an access key.
        (gtk.STOCK_MEDIA_PREVIOUS, _('gtk-media-previous')),
        # Translators: Only translate this if GTK does so incorrectly or not
        # at all. Don't literally translate media/next/previous/play/pause.
        # This string needs an access key.
        (gtk.STOCK_MEDIA_PLAY, _('gtk-media-play')),
        # Translators: Only translate this if GTK does so incorrectly or not
        # at all. Don't literally translate media/next/previous/play/pause.
        # This string needs an access key.
        (gtk.STOCK_MEDIA_PAUSE, _('gtk-media-pause')),
        ]:
        if key != name: # translated, so re-register with a good name
            gtk.stock_add([(key, name) + gtk.stock_lookup(key)[2:]])

    factory.add_default()

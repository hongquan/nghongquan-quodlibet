# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gst
import gobject

from quodlibet.plugins.gstelement import GStreamerPlugin
from quodlibet import qltk
from quodlibet import config
from quodlibet.util import gobject_weak


_PLUGIN_ID = "crossfeed"

_SETTINGS = {
    "preset": [_("_Preset:"), _("Filter preset")],
    "fcut": [_("_Frequency cut:"), _("Low-pass filter cut frequency")],
    "feed": [_("Feed _level:"), _("Feed level")],
}

_PRESETS = [
    ["default", _("Default"),
     _("Closest to virtual speaker placement (30°, 3 meter)"), 700, 45],
    ["cmoy", _("Chu Moy"),
     _("Close to Chu Moy's crossfeeder (popular)"), 700, 60],
    ["jmeier", _("Jan Meier"),
     _("Close to Jan Meier's CORDA amplifiers (little change)"), 650, 90],
    ["custom", _("Custom"), _("Custom settings"), -1, -1],
]

_CUSTOM_INDEX = 3


def get_cfg(option):
    cfg_option = "%s_%s" % (_PLUGIN_ID, option)

    if option == "feed":
        return config.getint("plugins", cfg_option, _PRESETS[0][4])
    elif option == "fcut":
        return config.getint("plugins", cfg_option, _PRESETS[0][3])


def set_cfg(option, value):
    cfg_option = "%s_%s" % (_PLUGIN_ID, option)
    if get_cfg(option) != value:
        config.set("plugins", cfg_option, value)


class Preferences(gtk.VBox):
    __gsignals__ = {
        'changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
    }

    def __init__(self):
        super(Preferences, self).__init__(spacing=12)

        table = gtk.Table(3, 2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        labels = {}
        for idx, key in enumerate(["preset", "fcut", "feed"]):
            text, tooltip = _SETTINGS[key]
            label = gtk.Label(text)
            labels[key] = label
            label.set_tooltip_text(tooltip)
            label.set_alignment(0.0, 0.5)
            label.set_padding(0, 6)
            label.set_use_underline(True)
            table.attach(label, 0, 1, idx, idx + 1,
                         xoptions=gtk.FILL | gtk.SHRINK)

        preset_combo = gtk.combo_box_new_text()
        self.__combo = preset_combo
        labels["preset"].set_mnemonic_widget(preset_combo)
        for preset in _PRESETS:
            preset_combo.append_text(preset[1])
        preset_combo.set_active(-1)
        table.attach(preset_combo, 1, 2, 0, 1)

        fcut_scale = gtk.HScale(gtk.Adjustment(700, 300, 2000, 10, 100))
        fcut_scale.set_tooltip_text(_SETTINGS["fcut"][1])
        labels["fcut"].set_mnemonic_widget(fcut_scale)
        fcut_scale.set_value_pos(gtk.POS_RIGHT)

        def format_hz(scale, value):
            return _("%d Hz") % value
        fcut_scale.connect('format-value', format_hz)
        table.attach(fcut_scale, 1, 2, 1, 2)

        def fcut_changed(scale):
            value = int(scale.get_value())
            set_cfg("fcut", value)
            self.__update_combo()
            self.emit("changed")
        fcut_scale.connect('value-changed', fcut_changed)
        fcut_scale.set_value(get_cfg("fcut"))

        level_scale = gtk.HScale(gtk.Adjustment(45, 10, 150, 1, 5))
        level_scale.set_tooltip_text(_SETTINGS["feed"][1])
        labels["feed"].set_mnemonic_widget(level_scale)
        level_scale.set_value_pos(gtk.POS_RIGHT)

        def format_db(scale, value):
            return _("%.1f dB") % (value / 10.0)
        level_scale.connect('format-value', format_db)
        table.attach(level_scale, 1, 2, 2, 3)

        def level_changed(scale):
            value = int(scale.get_value())
            set_cfg("feed", value)
            self.__update_combo()
            self.emit("changed")
        level_scale.connect('value-changed', level_changed)
        level_scale.set_value(get_cfg("feed"))

        def combo_change(combo, level_scale, fcut_scale):
            index = combo.get_active()
            if index == _CUSTOM_INDEX:
                combo.set_tooltip_text("")
                return
            tooltip, fcut, feed = _PRESETS[index][-3:]
            combo.set_tooltip_text(tooltip)
            level_scale.set_value(feed)
            fcut_scale.set_value(fcut)
        preset_combo.connect("changed", combo_change, level_scale, fcut_scale)
        self.__update_combo()

        self.pack_start(qltk.Frame(_("Preferences"), child=table))

    def __update_combo(self):
        feed = get_cfg("feed")
        fcut = get_cfg("fcut")
        for i, preset in enumerate(_PRESETS):
            def_fcut, def_feed = preset[-2:]
            if def_fcut == fcut and def_feed == feed:
                self.__combo.set_active(i)
                return
        self.__combo.set_active(_CUSTOM_INDEX)


class Crossfeed(GStreamerPlugin):
    PLUGIN_ID = _PLUGIN_ID
    PLUGIN_NAME = _("Crossfeed")
    PLUGIN_DESC = _("Mixes the left and right channel in a way that simulates"
                    " a speaker setup while using headphones, or to adjust "
                    "for early Stereo recordings.")
    PLUGIN_ICON = "audio-volume-high"

    @classmethod
    def setup_element(cls):
        try:
            return gst.element_factory_make('crossfeed', cls.PLUGIN_ID)
        except gst.ElementNotFoundError:
            pass

    @classmethod
    def update_element(cls, element):
        element.set_property("feed", get_cfg("feed"))
        element.set_property("fcut", get_cfg("fcut"))

    @classmethod
    def PluginPreferences(cls, window):
        prefs = Preferences()
        gobject_weak(prefs.connect, "changed", lambda *x: cls.queue_update())
        return prefs

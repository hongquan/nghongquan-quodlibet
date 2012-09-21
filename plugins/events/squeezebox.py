# Copyright 2011-2012 Nick Boultbee
#
# Inspired in parts by PySqueezeCenter (c) 2010 JingleManSweep
# SqueezeCenter and SqueezeBox are copyright Logitech
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#

from os import path
from quodlibet import qltk, config, print_w, print_d, app
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.msg import Message
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.plugins import PluginManager as PM
from telnetlib import Telnet
from threading import Thread
import _socket
import gtk
import socket
import time
import urllib
import gobject


class SqueezeboxServerSettings(dict):
    """Encapsulates Server settings"""
    def __str__(self):
        try:
            return _("Squeezebox server at {hostname}:{port}").format(**self)
        except KeyError:
            return _("unidentified Squeezebox server")

class SqueezeboxPlayerSettings(dict):
    """Encapsulates player settings"""
    def __str__(self):
        try:
            return "{name} [{playerid}]".format(**self)
        except KeyError:
            return _("unidentified Squeezebox player: %r" % self)

class SqueezeboxException(Exception):
    """Errors communicating with the Squeezebox"""


class SqueezeboxServer(object):
    """Encapsulates access to a Squeezebox player via a squeezecenter server"""

    _TIMEOUT = 10
    _MAX_FAILURES = 3
    telnet = None
    is_connected = False
    current_player = 0
    players = []
    config = SqueezeboxServerSettings()
    _debug = False

    def __init__(self, hostname="localhost", port=9090, user="", password="",
        library_dir='', current_player = 0, debug=False):
        self._debug = debug
        self.failures = 0
        self.delta = 600    # Default in ms
        if hostname:
            self.config = SqueezeboxServerSettings(locals())
            del self.config["self"]
            del self.config["current_player"]
            self.current_player = int(current_player) or 0
            try:
                if self._debug: print "Trying %s..." % self.config
                self.telnet = Telnet(hostname, port, self._TIMEOUT)
            except socket.error:
                print_w(_("Couldn't talk to %s") % (self.config,))
            else:
                result = self.__request("login %s %s" % (user, password))
                if result != (6 * '*'):
                    raise SqueezeboxException(
                        "Couldn't log in to squeezebox: response was '%s'"
                         % result)
                self.is_connected = True
                self.failures = 0
                print_d("Connected to Squeezebox Server! %s" % self)
                # Reset players (forces reload)
                self.players = []
                self.get_players()

    def get_library_dir(self):
        return self.config['library_dir']

    def __request(self, line, raw=False):
        """
        Send a request to the server, if connected, and return its response
        """
        line = line.strip()

        if not (self.is_connected or line.split()[0] == 'login'):
            print_d("Can't do '%s' - not connected" % line.split()[0], self)
            return None

        if self._debug: print ">>>> \"%s\"" % line
        try:
            self.telnet.write(line + "\n")
            raw_response = self.telnet.read_until("\n").strip()
        except _socket.error, e:
            print_w("Couldn't communicate with squeezebox (%s)" % e)
            self.failures += 1
            if self.failures >= self._MAX_FAILURES:
                print_w("Too many Squeezebox failures. Disconnecting")
                self.is_connected = False
                return None
        response = raw_response if raw else urllib.unquote(raw_response)
        if self._debug: print "<<<< \"%s\"" % (response,)
        return response[len(line) - 1:] if line.endswith("?")\
            else response[len(line) + 1:]

    def get_players(self):
        """ Returns (and caches) a list of the Squeezebox players available"""
        if self.players: return self.players
        pairs = self.__request("players 0 99", True).split(" ")

        def demunge(string):
            s = urllib.unquote(string)
            cpos = s.index(":")
            return (s[0:cpos], s[cpos + 1:])

        # Do a meaningful URL-unescaping and tuplification for all values
        pairs = map(demunge, pairs)

        # First element is always count
        count = int(pairs.pop(0)[1])
        self.players = []
        for pair in pairs:
            if pair[0] == "playerindex":
                playerindex = int(pair[1])
                self.players.append(SqueezeboxPlayerSettings())
            else:
                self.players[playerindex][pair[0]] = pair[1]
        if self._debug:
            print_d("Found %d player(s): %s" % (len(self.players),self.players),
                    self)
        assert (count == len(self.players))
        return self.players

    def player_request(self, line):
        if not self.is_connected: return
        try:
            return self.__request(
                "%s %s" % (self.players[self.current_player]["playerid"], line))
        except IndexError:
            return None

    def get_version(self):
        if self.is_connected:
            return self.__request("version ?")
        else:
            return "(not connected)"

    def play(self):
        """Plays the current song"""
        self.player_request("play")

    def is_stopped(self):
        """Returns whether the player is in any sort of non-playing mode"""
        response = self.player_request("mode ?")
        return "play" != response

    def playlist_play(self, path):
        """Play song immediately"""
        self.player_request("playlist play %s" % (urllib.quote(path)))

    def playlist_add(self, path):
        self.player_request("playlist add %s" % (urllib.quote(path)))

    def playlist_save(self, name):
        self.player_request("playlist save %s" % (urllib.quote(name)))

    def playlist_clear(self):
        self.player_request("playlist clear")

    def playlist_resume(self, name, resume, wipe=False):
        self.player_request("playlist resume %s noplay:%d wipePlaylist:%d" %
                            (urllib.quote(name), int(not resume), int(wipe)))

    def change_song(self, path):
        """Queue up a song"""
        self.player_request("playlist clear")
        self.player_request("playlist insert %s" % (urllib.quote(path)))

    def seek_to(self, ms):
        """Seeks the current song to `ms` milliseconds from start"""
        if not self.is_connected: return
        if self._debug:
            print_d("Requested %0.2f s, adding drift of %d ms..."
                    % (ms / 1000.0, self.delta))
        ms += self.delta
        start = time.time()
        self.player_request("time %d" % round(int(ms) / 1000))
        end = time.time()
        took = (end - start) * 1000
        reported_time = self.get_milliseconds()
        ql_pos = app.player.get_position()
        # Assume 50% of the time taken to complete is response.
        new_delta = ql_pos - reported_time
        # TODO: Better predictive modelling
        self.delta = (self.delta + new_delta) / 2
        if self._debug:
            print_d("Player at %0.0f but QL at %0.2f."
                    "(Took %0.0f ms). Drift was %+0.0f ms" %
                    (reported_time / 1000.0, ql_pos / 1000.0, took, new_delta))

    def get_milliseconds(self):
        secs = self.player_request("time ?") or 0
        return float(secs) * 1000.0

    def pause(self):
        self.player_request("pause 1")

    def unpause(self):
        if self.is_stopped(): self.play()
        ms = app.player.get_position()
        self.seek_to(ms)
        #self.player_request("pause 0")

    def stop(self):
        self.player_request("stop")

    def __str__(self):
        return str(self.config)


class GetPlayerDialog(gtk.Dialog):
    def __init__(self, parent, players, current=0):
        title = _("Choose Squeezebox player")
        super(GetPlayerDialog, self).__init__(title, parent)
        self.set_border_width(6)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)

        box = gtk.VBox(spacing=6)
        label = gtk.Label(_("Found Squeezebox server.\nPlease choose the player"))
        box.set_border_width(6)
        label.set_line_wrap(True)
        label.set_justify(gtk.JUSTIFY_CENTER)
        box.pack_start(label)

        player_combo = gtk.combo_box_new_text()
        for player in players:
            player_combo.append_text(player["name"])
        player_combo.set_active(current)
        self._val = player_combo
        box.pack_start(self._val)
        self.vbox.pack_start(box)
        self.child.show_all()

    def run(self, text=""):
        self.show()
        #self._val.set_activates_default(True)
        self._val.grab_focus()
        resp = super(GetPlayerDialog, self).run()
        if resp == gtk.RESPONSE_OK:
            value = self._val.get_active()
        else: value = None
        self.destroy()
        return value


class PluginConfigMixin(object):
    """Mixin for storage and editing of plugin config in a standard way"""

    @classmethod
    def _cfg_key(cls, name):
        try:
            prefix = cls.CONFIG_SECTION
        except AttributeError:
            prefix = cls.PLUGIN_ID.lower().replace(" ", "_")
        return "%s_%s" % (prefix, name)

    @classmethod
    def cfg_get(cls, name, default=None):
        """Gets a config string value for this plugin"""
        try:
            return config.get(PM.CONFIG_SECTION, cls._cfg_key(name))
        except config.error:
            # Set the missing config
            config.set(PM.CONFIG_SECTION, cls._cfg_key(name), default)
            return default

    @classmethod
    def cfg_set(cls, name, value):
        """Saves a config string value for this plugin"""
        try:
            config.set(PM.CONFIG_SECTION, cls._cfg_key(name), value)
        except config.error:
            print_d("Couldn't set config item '%s' to %r" % (name, value))

    @classmethod
    def cfg_get_bool(cls, name, default=False):
        """Gets a config boolean for this plugin"""
        return config.getboolean(PM.CONFIG_SECTION, cls._cfg_key(name),
            default)

    def cfg_entry_changed(self, entry, key):
        """React to a change in an gtk.Entry (by saving it to config)"""
        if entry.get_property('sensitive'):
            self.cfg_set(key, entry.get_text())

    @classmethod
    def ConfigCheckButton(cls, label, name, default=False):
        option = cls._cfg_key(name)
        try:
            config.getboolean(PM.CONFIG_SECTION, option)
        except config.error:
            cls.cfg_set(name, default)
        return ConfigCheckButton(label, PM.CONFIG_SECTION,
                                 option, populate=True)

class SqueezeboxPluginMixin(PluginConfigMixin):
    """
    All the Squeezebox connection / communication code in one delicious class
    """

    # Maintain a singleton; we only support one SB server live in QL
    server = None
    ql_base_dir = path.realpath(config.get("settings", "scan"))

    # We want all derived classes to share the config section
    CONFIG_SECTION="squeezebox"

    @classmethod
    def get_path(cls, song):
        """Gets a SB path to `song` by simple substitution"""
        path = song('~filename')
        return path.replace(cls.ql_base_dir, cls.server.get_library_dir())

    @classmethod
    def post_reconnect(cls):
        pass

    @staticmethod
    def _show_dialog(dialog_type, msg):
        dialog = Message(dialog_type, app.window, "Squeezebox", msg)
        dialog.connect('response', lambda dia, resp: dia.destroy())
        dialog.show()

    @staticmethod
    def quick_dialog(msg, dialog_type=gtk.MESSAGE_INFO):
        gobject.idle_add(SqueezeboxPluginMixin._show_dialog, dialog_type, msg)

    @classmethod
    def set_player(cls, val):
        cls.server.current_player = val
        cls.cfg_set("current_player", val)
        print_d("Setting player to #%d (%s)" % (val, cls.server.players[val]))

    @classmethod
    def check_settings(cls, button):
        cls.init_server()
        if cls.server.is_connected:
            ret = 0
            if len(cls.server.players) > 1:
                dialog = GetPlayerDialog(app.window, cls.server.players,
                                         cls.server.current_player)
                ret = dialog.run() or 0
            else:
                cls.quick_dialog("Squeezebox OK. Using the only player (%s)."
                                  % cls.server.players[0])
            cls.set_player(ret)
            # TODO: verify sanity of SB library path

            # Manage the changeover as best we can...
            cls.post_reconnect()

        else:
            cls.quick_dialog(_("Couldn't connect to %s") % (cls.server,),
                              gtk.MESSAGE_ERROR)

    @classmethod
    def PluginPreferences(cls, parent):
        def value_changed(entry, key):
            if entry.get_property('sensitive'):
                cls.server.config[key] = entry.get_text()
                config.set("plugins", "squeezebox_" + key, entry.get_text())

        vb = gtk.VBox(spacing=12)
        if not cls.server:
            cls.init_server()
        cfg = cls.server.config

        # Server settings Frame
        cfg_frame = gtk.Frame(_("<b>Squeezebox Server</b>"))
        cfg_frame.set_shadow_type(gtk.SHADOW_NONE)
        cfg_frame.get_label_widget().set_use_markup(True)
        cfg_frame_align = gtk.Alignment(0, 0, 1, 1)
        cfg_frame_align.set_padding(6, 6, 12, 12)
        cfg_frame.add(cfg_frame_align)

        # Tabulate all settings for neatness
        table = gtk.Table(3, 2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        rows = []

        ve = UndoEntry()
        ve.set_text(cfg["hostname"])
        ve.connect('changed', value_changed, 'server_hostname')
        rows.append((gtk.Label(_("Hostname:")), ve))

        ve = UndoEntry()
        ve.set_width_chars(5)
        ve.set_text(str(cfg["port"]))
        ve.connect('changed', value_changed, 'server_port')
        rows.append((gtk.Label(_("Port:")), ve))

        ve = UndoEntry()
        ve.set_text(cfg["user"])
        ve.connect('changed', value_changed, 'server_user')
        rows.append((gtk.Label(_("Username:")), ve))

        ve = UndoEntry()
        ve.set_text(str(cfg["password"]))
        ve.connect('changed', value_changed, 'server_password')
        rows.append((gtk.Label(_("Password:")), ve))

        ve = UndoEntry()
        ve.set_text(str(cfg["library_dir"]))
        ve.set_tooltip_text(_("Library directory the server connects to."))
        ve.connect('changed', value_changed, 'server_library_dir')
        rows.append((gtk.Label(_("Library path:")), ve))

        for (row,(label, entry)) in enumerate(rows):
            table.attach(label, 0, 1, row, row + 1)
            table.attach(entry, 1, 2, row, row + 1)

        # Add verify button
        button = gtk.Button(_("_Verify settings"))
        button.set_sensitive(cls.server is not None)
        button.connect('clicked', cls.check_settings)
        table.attach(button, 0, 2, row+1, row + 2)

        cfg_frame_align.add(table)
        vb.pack_start(cfg_frame)
        debug = cls.ConfigCheckButton(_("Debug"), "debug")
        vb.pack_start(debug)
        return vb

    @classmethod
    def init_server(cls):
        """Initialises a server, and connects to check if it's alive"""
        try:
            cur = int(cls.cfg_get("current_player", 0))
        except ValueError:
            cur = 0
        cls.server = SqueezeboxServer(
            hostname=cls.cfg_get("server_hostname", "localhost"),
            port=cls.cfg_get("server_port", 9090),
            user=cls.cfg_get("server_user", ""),
            password=cls.cfg_get("server_password", ""),
            library_dir=cls.cfg_get("server_library_dir", cls.ql_base_dir),
            current_player=cur,
            debug=cls.cfg_get_bool("debug", False))
        try:
            ver = cls.server.get_version()
            if cls.server.is_connected:
                print_d(
                    "Squeezebox server version: %s. Current player: #%d (%s)." %
                    (ver,
                     cur,
                     cls.server.get_players()[cur]["name"]))
        except (IndexError, KeyError), e:
            print_d("Couldn't get player info (%s)." % e)


class SqueezeboxSyncPlugin(EventPlugin, SqueezeboxPluginMixin):
    PLUGIN_ID = 'Squeezebox Output'
    PLUGIN_NAME = _('Squeezebox Sync')
    PLUGIN_DESC = _("Make Logitech Squeezebox mirror Quod Libet output, "
            "provided both read from an identical library")
    PLUGIN_ICON = gtk.STOCK_MEDIA_PLAY
    PLUGIN_VERSION = '0.3'
    server = None
    active = False
    _debug = False

    def __init__(self):
        super(EventPlugin, self).__init__()
        super(SqueezeboxPluginMixin, self).__init__()

    @classmethod
    def post_reconnect(cls):
        cls.server.stop()
        SqueezeboxPluginMixin.post_reconnect()
        player = app.player
        cls.plugin_on_song_started(player.info)
        cls.plugin_on_seek(player.info, player.get_position())

    def enabled(self):
        print_d("Debug is set to %s" % self._debug)
        self.active = True
        self.init_server()
        self.server.pause()
        if not self.server.is_connected:
            qltk.ErrorMessage(
                None,
                _("Error finding Squeezebox server"),
                _("Error finding %s. Please check settings") % self.server.config
            ).run()

    def disabled(self):
        # Stopping might be annoying in some situations, but seems more correct
        if self.server: self.server.stop()
        self.active = False

    @classmethod
    def plugin_on_song_started(cls, song):
        # Yucky hack to allow some form of immediacy on re-configuration
        cls.server._debug = cls._debug = cls.cfg_get_bool("debug", False)
        if cls._debug:
            print_d("Paused" if app.player.paused else "Not paused")
        if song and cls.server and cls.server.is_connected:
            path = cls.get_path(song)
            print_d("Requesting to play %s..." % path)
            if app.player.paused:
                cls.server.change_song(path)
            else:
                cls.server.playlist_play(path)

    @classmethod
    def plugin_on_paused(cls):
        if cls.server: cls.server.pause()

    @classmethod
    def plugin_on_unpaused(cls):
        if cls.server: cls.server.unpause()

    @classmethod
    def plugin_on_seek(cls, song, msec):
        if not app.player.paused:
            if cls.server:
                cls.server.seek_to(msec)
                cls.server.play()
        else: pass #cls.server.pause()


class SqueezeboxPlaylistPlugin(SongsMenuPlugin, SqueezeboxPluginMixin):
    PLUGIN_ID = "Export to Squeezebox Playlist"
    PLUGIN_NAME = _("Export to Squeezebox Playlist")
    PLUGIN_DESC = _("Dynamically export songs to Logitech Squeezebox "
                    "playlists, provided both share a directory structure. "
                    "Shares configuration with Squeezebox Sync plugin")
    PLUGIN_ICON = gtk.STOCK_EDIT
    PLUGIN_VERSION = '0.1'
    TEMP_PLAYLIST = "_temp"

    def __init__(self, songs):
        print_d("Calling SqueezeboxPluginMixin.__init__()...")
        SqueezeboxPluginMixin.__init__(self)
        SongsMenuPlugin.__init__(self, songs)


    def __add_songs(self, songs):
        self.server.playlist_save(self.TEMP_PLAYLIST)
        # app.player.paused = True
        self.server.playlist_clear()
        for song in songs:
            #print_d(song("~filename"))
            self.server.playlist_add(self.get_path(song))

    def __get_playlist_name(self):
        dialog = qltk.GetStringDialog(None,
            _("Export selection to Squeezebox playlist"),
            _("Playlist name (will overwrite existing)"),
            okbutton=gtk.STOCK_SAVE)
        name = dialog.run(text="Quod Libet playlist")
        return name

    def plugin_songs(self, songs):
        self.init_server()
        if not self.server.is_connected:
            qltk.ErrorMessage(
                None,
                _("Error finding Squeezebox server"),
                _("Error finding %s. Please check settings") %self.server.config
            ).run()
        else:
            paused = app.player.paused
            # Spin a worker thread.
            worker = Thread(target=self.__add_songs, args=(songs,))
            print_d("Starting worker thread...")
            worker.setDaemon(True)
            worker.start()
            print_d("Worker thread started")
            #self.quick_dialog("Adding %d songs..." % len(songs))
            name = self.__get_playlist_name()
            worker.join(timeout=30)
            # Only save once we're done adding
            self.server.playlist_save(name)
            app.player.paused = paused
            self.server.playlist_resume(self.TEMP_PLAYLIST,
                                        not app.player.paused, True)

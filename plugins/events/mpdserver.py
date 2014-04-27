# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import re
import shlex
import socket

from quodlibet import app
from quodlibet.plugins.events import EventPlugin

from gi.repository import Gtk, Gio, GLib


DEBUG = False


class AckError(object):
    NOT_LIST = 1
    ARG = 2
    PASSWORD = 3
    PERMISSION = 4
    UNKNOWN = 5
    NO_EXIST = 50
    PLAYLIST_MAX = 51
    SYSTEM = 52
    PLAYLIST_LOAD = 53
    UPDATE_ALREADY = 54
    PLAYER_SYNC = 55
    EXIST = 56


class ParseError(Exception):
    pass


def parse_command(line):
    """Parses a MPD command (without trailing newline)

    Returns (command, [arguments]) or raises ParseError in case of an error.
    """

    assert isinstance(line, bytes)

    parts = re.split("[ \\t]+", line, maxsplit=1)
    if not parts:
        raise ParseError("empty command")
    command = parts[0]

    if len(parts) > 1:
        lex = shlex.shlex(parts[1], posix=True)
        lex.whitespace_split = True
        lex.commenters = ""
        lex.quotes = "\""
        lex.whitespace = " \t"
        args = list(lex)
    else:
        args = []

    try:
        command = command.decode("utf-8")
    except ValueError as e:
        raise ParseError(e)

    dec_args = []
    for arg in args:
        try:
            arg = arg.decode("utf-8")
        except ValueError as e:
            raise ParseError(e)
        dec_args.append(arg)

    return command, dec_args


class BaseTCPServer(object):

    def __init__(self, port, connection_class):
        """port -- IP port
        connection_class -- BaseTCPConnection subclass
        """

        self._connections = []

        service = Gio.SocketService.new()
        service.add_inet_port(port, None) # FIXME: can raise
        service.connect("incoming", self._incoming_connection_cb)
        self._sock_service = service
        self.connection_class = connection_class

    def start(self):
        """Start accepting connections"""

        self._sock_service.start()

    def stop(self):
        """Stop accepting connections and close all existing connections"""

        if self._sock_service.is_active():
            self._sock_service.stop()

        for conn in list(self._connections):
            conn.close()

        assert not self._connections, self._connections

    def _remove_connection(self, conn):
        """Called by the connection class on close"""

        self._connections.remove(conn)
        del conn._gio_connection

    def _incoming_connection_cb(self, service, connection, *args):
        fd = connection.get_socket().get_fd()
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)

        tcp_conn = self.connection_class(self, sock)
        self._connections.append(tcp_conn)
        # XXX: set unneeded `connection` to keep the reference
        tcp_conn._gio_connection = connection
        tcp_conn.handle_init(self)


class BaseTCPConnection(object):
    """Abstract base class for TCP connections.

    Subclasses need to implement the handle_*() can_*() methods.
    """

    def __init__(self, server, sock):
        self._server = server
        self._sock = sock

        self._in_id = None
        self._out_id = None
        self._closed = False

    def log(self, msg):
        if DEBUG:
            print_d("[%d] %s" % (self._sock.fileno(), msg))

    def start_read(self):
        """Start to read and call handle_read() if data is available.

        Only call once.
        """

        assert self._in_id is None

        def can_read_cb(sock, flags, *args):
            if flags & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                self.close()
                return False

            if flags & GLib.IOCondition.IN:
                data = sock.recv(4096)
                # FIXME: handle eagain etc.
                if not data:
                    self.close()
                    return False

                self.handle_read(data)
                self.start_write()

            return True

        self._in_id = GLib.io_add_watch(
            self._sock, GLib.PRIORITY_DEFAULT,
            GLib.IOCondition.IN | GLib.IOCondition.ERR | GLib.IOCondition.HUP,
            can_read_cb)

    def start_write(self):
        """Trigger at least one call to handle_write() if can_write is True.

        Used to start writing to a client not triggered by a client request.
        """

        write_buffer = bytearray()

        def can_write_cb(sock, flags, *args):
            if flags & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                self.close()
                return False

            if flags & GLib.IOCondition.OUT:
                if self.can_write():
                    write_buffer.extend(self.handle_write())
                if not write_buffer:
                    self._out_id = None
                    return False

                result = sock.send(write_buffer)
                # FIXME: handle error
                del write_buffer[:result]

            return True

        if self._out_id is None:
            self._out_id = GLib.io_add_watch(
                self._sock, GLib.PRIORITY_DEFAULT,
                GLib.IOCondition.OUT | GLib.IOCondition.ERR |
                GLib.IOCondition.HUP,
                can_write_cb)

    def close(self):
        """Close this connection. Can be called multiple times.

        handle_close() will be called last.
        """

        if self._closed:
            return
        self._closed = True

        if self._in_id is not None:
            GLib.source_remove(self._in_id)
            self._in_id = None
        if self._out_id is not None:
            GLib.source_remove(self._out_id)
            self._out_id = None

        self.handle_close()
        self._server._remove_connection(self)
        self._sock.close()

    def handle_init(self, server):
        """Called first, gets passed the BaseServer instance"""

        raise NotImplementedError

    def handle_read(self, data):
        """Called if new data was read"""

        raise NotImplementedError

    def handle_write(self):
        """Called if new data can be written, should return the data"""

        raise NotImplementedError

    def can_write(self):
        """Should return True if handle_write() can return data"""

        raise NotImplementedError

    def handle_close(self):
        """Called last when the connection gets closed"""

        raise NotImplementedError


class MPDService(object):
    """This is the actual shared MPD service which the clients talk to"""

    version = (0, 12)

    def __init__(self):
        self._id = 0

    def play(self):
        if not app.player.song:
            app.player.reset()
        else:
            app.player.paused = False

    def pause(self):
        app.player.paused = True

    def stop(self):
        app.player.stop()

    def next(self):
        app.player.next()
        self._id += 1

    def previous(self):
        app.player.previous()
        self._id += 1

    def seek(self, songpos, time_):
        """time_ in seconds"""

        app.player.seek(time_ * 1000)

    def seekid(self, songid, time_):
        """time_ in seconds"""

        app.player.seek(time_ * 1000)

    def seekcur(self, value, relative):
        if relative:
            pos = app.player.get_position()
            app.player.seek(pos + value)
        else:
            app.player.seek(value)

    def setvol(self, value):
        """value: 0..100"""

        app.player.volume = value / 100.0

    def repeat(self, value):
        app.window.repeat.set_active(value)

    def stats(self):
        stats = [
            ("artists", 1),
            ("albums", 1),
            ("songs", 1),
            ("uptime", 1),
            ("playtime", 1),
            ("db_playtime", 1),
            ("db_update", 1252868674),
        ]

        return stats

    def status(self):
        info = app.player.info

        if info:
            if app.player.paused:
                state = "pause"
            else:
                state = "play"
        else:
            state = "stop"

        status = [
            ("volume", int(app.player.volume * 100)),
            ("repeat", int(app.window.repeat.get_active())),
            ("random", 0),
            ("single", 0),
            ("consume", 0),
            ("playlist", 0),
            ("playlistlength", 0),
            ("state", state),
            ("song", self._id),
            ("songid", self._id),
            ("nextsong", self._id + 1),
            ("nextsongid", self._id + 1),
            ("time", "%d:%d" % (
                int(app.player.get_position() / 1000),
                info and info("~#length") or 0)),
        ]

        return status

    def currentsong(self):
        song = app.player.info
        if song is None:
            return None

        stats = [
            ("file", song["~filename"]),
            ("Time", song("~#length")),
            ("Artist", song.comma("artist")),
            ("Title", song.comma("title")),
            ("Album", song.comma("album")),
            ("Pos", self._id),
            ("Id", self._id),
        ]

        return stats


class MPDServer(BaseTCPServer):

    def __init__(self, port):
        super(MPDServer, self).__init__(port, MPDConnection)
        self.service = MPDService()


class MPDRequestError(Exception):

    def __init__(self, msg, code=AckError.UNKNOWN, index=None):
        self.msg = msg
        self.code = code
        self.index = index


class MPDConnection(BaseTCPConnection):

    #  ------------ connection interface  ------------

    def handle_init(self, server):
        service = server.service
        self.service = service

        str_version = ".".join(map(str, service.version))
        self._buf = bytearray("OK MPD %s\n" % str_version)
        self._read_buf = bytearray()

        # begin - command processing state
        self._use_command_list = False
        # everything below is only valid if _use_command_list is True
        self._command_list_ok = False
        self._command_list = []
        self._command = None
        # end - command processing state

        self.start_write()
        self.start_read()

    def handle_read(self, data):
        self._feed_data(data)

        line = self._get_next_line()
        if line is None:
            return

        self.log(repr(line))

        try:
            cmd, args = parse_command(line)
        except ParseError:
            # TODO: not sure what to do here re command lists
            return

        try:
            self._handle_command(cmd, args)
        except MPDRequestError as e:
            self._error(e.msg, e.code, e.index)
            self._use_command_list = False
            del self._command_list[:]

    def handle_write(self):
        data = self._buf[:]
        del self._buf[:]
        return data

    def can_write(self):
        return bool(self._buf)

    def handle_close(self):
        del self.service

    #  ------------ rest ------------

    def _feed_data(self, new_data):
        """Feed new data into the read buffer"""

        self._read_buf.extend(new_data)

    def _get_next_line(self):
        """Returns the next line from the read buffer or None"""

        try:
            index = self._read_buf.index("\n")
        except ValueError:
            return None, []

        line = bytes(self._read_buf[:index])
        del self._read_buf[:index + 1]
        return line

    def _write_line(self, line):
        """Writes a line to the client"""

        assert isinstance(line, unicode)

        self._buf.extend(line.encode("utf-8", errors="replace") + "\n")

    def _ok(self):
        self._write_line(u"OK")

    def _error(self, msg, code, index):
        error = []
        error.append(u"ACK [%d" % code)
        if index is not None:
            error.append(u"@%d" % index)
        assert self._command is not None
        error.append("u] {%s}" % self._command)
        if msg is not None:
            error.append(u" %s" % msg)
        self._write_line(u"".join(error))

    def _handle_command(self, command, args):
        self._command = command

        if command == u"command_list_end":
            if not self._use_command_list:
                self._error(u"list_end without begin")
                return

            for i, (cmd, args) in enumerate(self._command_list):
                try:
                    self._exec_command(cmd, args)
                except MPDRequestError as e:
                    # reraise with index
                    raise MPDRequestError(e.msg, e.code, i)

                if self._command_list_ok:
                    self._write_line(U"list_OK")

            self._ok()
            self._use_command_list = False
            del self._command_list[:]
            return

        if command in (u"command_list_begin", u"command_list_ok_begin"):
            if self._use_command_list:
                raise MPDRequestError(u"begin without end")

            self._use_command_list = True
            self._command_list_ok = command == u"command_list_ok_begin"
            assert not self._command_list
            return

        if self._use_command_list:
            self._command_list.append((command, args))
        else:
            self._exec_command(command, args)

    def _exec_command(self, command, args):
        self._command = command

        try:
            cmd_method = getattr(self, u"_cmd_" + command)
        except AttributeError:
            # Unhandled command, default to OK for now..
            self._ok()
            return

        cmd_method(args)

    def _cmd_idle(self, args):
        # TODO: register for events
        pass

    def _cmd_close(self, args):
        self.close()

    def _cmd_play(self, args):
        self.service.play()
        self._ok()

    def _cmd_pause(self, args):
        self.service.pause()
        self._ok()

    def _cmd_stop(self, args):
        self.service.stop()
        self._ok()

    def _cmd_next(self, args):
        self.service.next()
        self._ok()

    def _cmd_previous(self, args):
        self.service.previous()
        self._ok()

    def _cmd_repeat(self, args):
        if not args:
            raise MPDRequestError("missing arg")

        try:
            value = int(args[0])
            if value not in (0, 1):
                raise ValueError
        except ValueError:
            raise MPDRequestError("invalid arg")

        self.service.repeat(value)
        self._ok()

    def _cmd_setvol(self, args):
        if not args:
            raise MPDRequestError("missing arg")

        try:
            value = int(args[0])
        except ValueError:
            raise MPDRequestError("invalid arg")

        self.service.setvol(value)
        self._ok()

    def _cmd_ping(self, args):
        self._ok()

    def _cmd_status(self, args):
        status = self.service.status()
        for k, v in status:
            self._write_line(u"%s: %s" % (k, v))
        self._ok()

    def _cmd_stats(self, args):
        status = self.service.stats()
        for k, v in status:
            self._write_line(u"%s: %s" % (k, v))
        self._ok()

    def _cmd_currentsong(self, args):
        stats = self.service.currentsong()
        if stats is None:
            self._ok()
            return

        for k, v in stats:
            self._write_line(u"%s: %s" % (k, v))
        self._ok()

    def _cmd_count(self, args):
        self._write_line(u"songs: 0")
        self._write_line(u"playtime: 0")
        self._ok()

    def _cmd_plchanges(self, args):
        self._cmd_currentsong(args)

    def _cmd_listallinfo(self, args):
        self._cmd_currentsong(args)

    def _cmd_seek(self, args):
        if len(args) != 2:
            raise MPDRequestError("wrong arg count")

        songpos, time_ = args

        try:
            songpos = int(songpos)
            time_ = int(time_)
        except ValueError:
            raise MPDRequestError("arg not a number")

        self.service.seek(songpos, time_)
        self._ok()

    def _cmd_seekid(self, args):
        if len(args) != 2:
            raise MPDRequestError("wrong arg count")

        songid, time_ = args

        try:
            songid = int(songid)
            time_ = int(time_)
        except ValueError:
            raise MPDRequestError("arg not a number")

        self.service.seekid(songid, time_)
        self._ok()

    def _cmd_seekcur(self, args):
        if len(args) != 1:
            raise MPDRequestError("wrong arg count")

        relative = False
        time_ = args[0]
        if time_.startswith(("+", "-")):
            relative = True

        try:
            time_ = int(time_)
        except ValueError:
            raise MPDRequestError("arg not a number")

        self.service.seekid(time_, relative)
        self._ok()


class MPDServerPlugin(EventPlugin):
    PLUGIN_ID = "mpd_server"
    PLUGIN_NAME = _("MPD Server")
    PLUGIN_DESC = _("Provides a MPD server interface")
    PLUGIN_ICON = Gtk.STOCK_CONNECT

    PORT = 6600

    def enabled(self):
        self.server = MPDServer(self.PORT)
        self.server.start()

    def disabled(self):
        self.server.stop()
        del self.server

# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Steven Robertson,
#           2011-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gi
try:
    gi.require_version("Gst", "1.0")
    gi.require_version("GstPbutils", "1.0")
except ValueError, e:
    raise ImportError(e)

from gi.repository import Gst, GLib, GstPbutils

import threading

from quodlibet import const
from quodlibet import config

from quodlibet.util import fver, sanitize_tags
from quodlibet.player import PlayerError
from quodlibet.player._base import BasePlayer
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk.notif import Task

from .util import (parse_gstreamer_taglist, TagListWrapper, iter_to_list,
    GStreamerSink, link_many, bin_debug)
from .plugins import GStreamerPluginHandler
from .prefs import GstPlayerPreferences

STATE_CHANGE_TIMEOUT = Gst.SECOND * 4


class BufferingWrapper(object):
    """A wrapper for a Gst.Element (usually GstPlayBin) which pauses the
    elmement in case buffering is needed, but hides the fact that it does.

    Probably not perfect...

    You have to call destroy() before it gets gc'd
    """

    def __init__(self, bin_, player):
        """
        bin_ -- the GstPlaybin instance to wrap
        player -- the GStreamerPlayer instance used
                  for aborting the buffer process
        """

        self.bin = bin_
        self._wanted_state = None
        self._task = None
        self._inhibit_play = False
        self._player = player

        bus = self.bin.get_bus()
        bus.add_signal_watch()
        self.__bus_id = bus.connect('message', self.__message)

    def __message(self, bus, message):
        if message.type == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            self.__update_buffering(percent)

    def __getattr__(self, name):
        return getattr(self.bin, name)

    def __update_buffering(self, percent):
        """Call this with buffer percent values from the bus"""

        if self._task:
            self._task.update(percent / 100.0)

        self.__set_inhibit_play(percent < 100)

    def __set_inhibit_play(self, inhibit):
        """Change the inhibit state"""

        if inhibit == self._inhibit_play:
            return
        self._inhibit_play = inhibit

        # task management
        if inhibit:
            if not self._task:
                def stop_buf(*args):
                    self._player.paused = True

                self._task = Task(_("Stream"), _("Buffering"), stop=stop_buf)
        elif self._task:
            self._task.finish()
            self._task = None

        # state management
        if inhibit:
            # save the current state
            status, state, pending = self.bin.get_state(
                timeout=STATE_CHANGE_TIMEOUT)
            if status == Gst.StateChangeReturn.SUCCESS and \
                    state == Gst.State.PLAYING:
                self._wanted_state = state
            else:
                # no idea, at least don't play
                self._wanted_state = Gst.State.PAUSED

            self.bin.set_state(Gst.State.PAUSED)
        else:
            # restore the old state
            self.bin.set_state(self._wanted_state)
            self._wanted_state = None

    def set_state(self, state):
        if self._inhibit_play:
            # PLAYING, PAUSED change the state for after buffering is finished,
            # everything else aborts buffering
            if state not in (Gst.State.PLAYING, Gst.State.PAUSED):
                # abort
                self.__set_inhibit_play(False)
                self.bin.set_state(state)
                return
            self._wanted_state = state
        else:
            self.bin.set_state(state)

    def get_state(self, *args, **kwargs):
        # get_state also is a barrier (seek/positioning),
        # so call every time but ignore the result in the inhibit case
        res = self.bin.get_state(*args, **kwargs)
        if self._inhibit_play:
            return self._wanted_state
        return res

    def destroy(self):
        if self.__bus_id:
            bus = self.bin.get_bus()
            bus.disconnect(self.__bus_id)
            bus.remove_signal_watch()
            self.__bus_id = None

        self.__set_inhibit_play(False)


class GStreamerPlayer(BasePlayer, GStreamerPluginHandler):
    __gproperties__ = BasePlayer._gproperties_
    __gsignals__ = BasePlayer._gsignals_

    _paused = True
    _in_gapless_transition = False
    _last_position = 0

    bin = None
    _vol_element = None
    _use_eq = False
    _eq_element = None

    __atf_id = None
    __bus_id = None

    __info_buffer = None

    def PlayerPreferences(self):
        return GstPlayerPreferences(self, const.DEBUG)

    def __init__(self, librarian=None):
        GStreamerPluginHandler.__init__(self)
        super(GStreamerPlayer, self).__init__()
        self.version_info = "GStreamer: %s" % fver(Gst.version())
        self._librarian = librarian
        self._pipeline_desc = None
        librarian.connect("changed", self.__songs_changed)
        self._active_seeks = []

    def __songs_changed(self, librarian, songs):
        # replaygain values might have changed, recalc volume
        if self.song and self.song in songs:
            self.volume = self.volume

    def destroy(self):
        self.__destroy_pipeline()

    @property
    def name(self):
        name = "GStreamer"
        if self._pipeline_desc:
            name += " (%s)" % self._pipeline_desc
        return name

    def _set_buffer_duration(self, duration):
        """Set the stream buffer duration in msecs"""

        config.set("player", "gst_buffer", float(duration) / 1000)

        if self.bin:
            value = duration * Gst.MSECOND
            self.bin.set_property('buffer-duration', value)

    def _print_pipeline(self):
        """Print debug information for the active pipeline to stdout
        (elements, formats, ...)
        """

        if self.bin:
            # self.bin is just a wrapper, so get the real one
            for line in bin_debug([self.bin.bin]):
                print_(line)
        else:
            print_e("No active pipeline.")

    def __init_pipeline(self):
        """Creates a gstreamer pipeline. Returns True on success."""

        if self.bin:
            return True

        pipeline = config.get("player", "gst_pipeline")
        pipeline, self._pipeline_desc = GStreamerSink(pipeline)
        if not pipeline:
            return False

        if self._use_eq and Gst.ElementFactory.find('equalizer-10bands'):
            # The equalizer only operates on 16-bit ints or floats, and
            # will only pass these types through even when inactive.
            # We push floats through to this point, then let the second
            # audioconvert handle pushing to whatever the rest of the
            # pipeline supports. As a bonus, this seems to automatically
            # select the highest-precision format supported by the
            # rest of the chain.
            filt = Gst.ElementFactory.make('capsfilter', None)
            filt.set_property('caps',
                              Gst.Caps.from_string('audio/x-raw,format=F32LE'))
            eq = Gst.ElementFactory.make('equalizer-10bands', None)
            self._eq_element = eq
            self.update_eq_values()
            conv = Gst.ElementFactory.make('audioconvert', None)
            resample = Gst.ElementFactory.make('audioresample', None)
            pipeline = [filt, eq, conv, resample] + pipeline

        # playbin2 has started to control the volume through pulseaudio,
        # which means the volume property can change without us noticing.
        # Use our own volume element for now until this works with PA.
        self._vol_element = Gst.ElementFactory.make('volume', None)
        pipeline.insert(0, self._vol_element)

        # Get all plugin elements and append audio converters.
        # playbin already includes one at the end
        plugin_pipeline = []
        for plugin in self._get_plugin_elements():
            plugin_pipeline.append(plugin)
            plugin_pipeline.append(
                Gst.ElementFactory.make('audioconvert', None))
            plugin_pipeline.append(
                Gst.ElementFactory.make('audioresample', None))
        pipeline = plugin_pipeline + pipeline

        bufbin = Gst.Bin()
        for element in pipeline:
            assert element is not None, pipeline
            bufbin.add(element)

        if len(pipeline) > 1:
            if not link_many(pipeline):
                print_w("Could not link GStreamer pipeline")
                self.__destroy_pipeline()
                return False

        # Test to ensure output pipeline can preroll
        bufbin.set_state(Gst.State.READY)
        result, state, pending = bufbin.get_state(timeout=STATE_CHANGE_TIMEOUT)
        if result == Gst.StateChangeReturn.FAILURE:
            bufbin.set_state(Gst.State.NULL)
            self.__destroy_pipeline()
            return False

        # Make the sink of the first element the sink of the bin
        gpad = Gst.GhostPad.new('sink', pipeline[0].get_static_pad('sink'))
        bufbin.add_pad(gpad)

        self.bin = Gst.ElementFactory.make('playbin', None)
        assert self.bin
        self.bin = BufferingWrapper(self.bin, self)
        self.__atf_id = self.bin.connect('about-to-finish',
            self.__about_to_finish)

        # set buffer duration
        duration = config.getfloat("player", "gst_buffer")
        self._set_buffer_duration(int(duration * 1000))

        # connect playbin to our pluing/volume/eq pipeline
        self.bin.set_property('audio-sink', bufbin)

        # by default playbin will render video -> suppress using fakesink
        fakesink = Gst.ElementFactory.make('fakesink', None)
        self.bin.set_property('video-sink', fakesink)

        # disable all video/text decoding in playbin
        GST_PLAY_FLAG_VIDEO = 1 << 0
        GST_PLAY_FLAG_TEXT = 1 << 2
        flags = self.bin.get_property("flags")
        flags &= ~(GST_PLAY_FLAG_VIDEO | GST_PLAY_FLAG_TEXT)
        self.bin.set_property("flags", flags)

        # find the (uri)decodebin after setup and use autoplug-sort
        # to sort elements like decoders
        def source_setup(*args):
            def autoplug_sort(decode, pad, caps, factories):
                def set_prio(x):
                    i, f = x
                    i = {
                        "mad": -1,
                        "mpg123audiodec": -2
                    }.get(f.get_name(), i)
                    return (i, f)
                return zip(*sorted(map(set_prio, enumerate(factories))))[1]

            for e in iter_to_list(self.bin.iterate_recurse):
                try:
                    e.connect("autoplug-sort", autoplug_sort)
                except TypeError:
                    pass
                else:
                    break
        self.bin.connect("source-setup", source_setup)

        # ReplayGain information gets lost when destroying
        self.volume = self.volume

        bus = self.bin.get_bus()
        bus.add_signal_watch()
        self.__bus_id = bus.connect('message', self.__message, self._librarian)

        if self.song:
            self.bin.set_property('uri', self.song("~uri"))

        return True

    def __destroy_pipeline(self):
        self._remove_plugin_elements()

        if self.__bus_id:
            bus = self.bin.get_bus()
            bus.disconnect(self.__bus_id)
            bus.remove_signal_watch()
            self.__bus_id = False

        if self.__atf_id:
            self.bin.disconnect(self.__atf_id)
            self.__atf_id = False

        if self.bin:
            self.bin.set_state(Gst.State.NULL)
            self.bin.get_state(timeout=STATE_CHANGE_TIMEOUT)
            # BufferingWrapper cleanup
            self.bin.destroy()
            self.bin = None

        self._in_gapless_transition = False
        self._last_position = 0
        self._active_seeks = []

        self._vol_element = None
        self._eq_element = None

    def _rebuild_pipeline(self):
        """If a pipeline is active, rebuild it and restore vol, position etc"""

        if not self.bin:
            return

        paused = self.paused
        pos = self.get_position()

        self.__destroy_pipeline()
        self.paused = True
        self.__init_pipeline()
        self.paused = paused
        self.seek(pos)

    def __message(self, bus, message, librarian):
        if message.type == Gst.MessageType.EOS:
            print_d("Stream EOS")
            if not self._in_gapless_transition:
                self._source.next_ended()
            self._end(False)
        elif message.type == Gst.MessageType.TAG:
            self.__tag(message.parse_tag(), librarian)
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            err = str(err).decode(const.ENCODING, 'replace')
            self._error(err)
        elif message.type == Gst.MessageType.STREAM_START:
            if self._in_gapless_transition:
                print_d("Stream changed")
                self._end(False)
        elif message.type == Gst.MessageType.ASYNC_DONE:
            if self._active_seeks:
                song, pos = self._active_seeks.pop(0)
                if song is self.song:
                    self.emit("seek", song, pos)
        elif message.type == Gst.MessageType.ELEMENT:
            message_name = message.get_structure().get_name()

            if message_name == "missing-plugin":
                self.stop()
                details = \
                    GstPbutils.missing_plugin_message_get_installer_detail(
                        message)
                if details is not None:
                    message = (_(
                        "No GStreamer element found to handle the following "
                        "media format: %(format_details)r") %
                        {"format_details": details})
                    print_w(message)

                    context = GstPbutils.InstallPluginsContext.new()

                    # TODO: track success
                    def install_done_cb(*args):
                        Gst.update_registry()
                    res = GstPbutils.install_plugins_async(
                        [details], context, install_done_cb, None)
                    print_d("Gstreamer plugin install result: %r" % res)
                    if res in (GstPbutils.InstallPluginsReturn.HELPER_MISSING,
                            GstPbutils.InstallPluginsReturn.INTERNAL_FAILURE):
                        self._error(message)

        return True

    def __about_to_finish(self, pipeline):
        print_d("About to finish")

        if config.getboolean("player", "gst_disable_gapless"):
            print_d("Gapless disabled")
            return

        # this can trigger twice, see issue 987
        if self._in_gapless_transition:
            return
        self._in_gapless_transition = True

        def change_in_main_loop(event, source):
            source.next_ended()
            event.set()

        # push in the main loop and wait for it to finish
        event = threading.Event()
        GLib.idle_add(change_in_main_loop, event, self._source,
                         priority=GLib.PRIORITY_HIGH)
        event.wait()

        song = self._source.current
        bin = self.bin

        if song and bin:
            bin.set_property('uri', song("~uri"))

    def stop(self):
        super(GStreamerPlayer, self).stop()
        self.__destroy_pipeline()

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self._volume = v
            if self.song and config.getboolean("player", "replaygain"):
                profiles = filter(None, self.replaygain_profiles)[0]
                fb_gain = config.getfloat("player", "fallback_gain")
                pa_gain = config.getfloat("player", "pre_amp_gain")
                scale = self.song.replay_gain(profiles, pa_gain, fb_gain)
                v = min(10.0, max(0.0, v * scale)) # volume supports 0..10
            if self.bin:
                self._vol_element.set_property('volume', v)
        else:
            raise AttributeError

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""

        p = self._last_position
        if self.song and self.bin:
            ok, p = self.bin.query_position(Gst.Format.TIME)
            if ok:
                p //= Gst.MSECOND
                # During stream seeking querying the position fails.
                # Better return the last valid one instead of 0.
                self._last_position = p
        return p

    def _set_paused(self, paused):
        if paused == self._paused:
            return
        self._paused = paused

        if not self.song:
            if paused:
                # Something wants us to pause between songs, or when
                # we've got no song playing (probably StopAfterMenu).
                self.emit('paused')
                self.__destroy_pipeline()
            return

        if paused:
            if self.bin:
                if self.song.is_file:
                    # fast path
                    self.bin.set_state(Gst.State.PAUSED)
                else:
                    # seekable streams (seem to) have a duration >= 0
                    ok, d = self.bin.query_duration(Gst.Format.TIME)
                    if not ok:
                        d = -1

                    if d >= 0:
                        self.bin.set_state(Gst.State.PAUSED)
                    else:
                        # destroy so that we rebuffer on resume
                        self.__destroy_pipeline()
        else:
            if self.bin:
                self.bin.set_state(Gst.State.PLAYING)
            else:
                if self.__init_pipeline():
                    self.bin.set_state(Gst.State.PLAYING)
                else:
                    # Backend error; show message and halt playback
                    ErrorMessage(None, _("Output Error"),
                        _("GStreamer output pipeline could not be "
                          "initialized. The pipeline might be invalid, "
                          "or the device may be in use. Check the "
                          "player preferences.")).run()
                    self.emit((paused and 'paused') or 'unpaused')
                    self._paused = paused = True

        self.emit((paused and 'paused') or 'unpaused')

    def _get_paused(self):
        return self._paused
    paused = property(_get_paused, _set_paused)

    def _error(self, message):
        print_w(message)
        self.emit('error', self.song, message)
        if not self.paused:
            self.next()

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""
        # Don't allow seeking during gapless. We can't go back to the old song.
        if not self.song or self._in_gapless_transition:
            return

        if self.__init_pipeline():
            # ensure any pending state changes have completed and we have
            # at least paused state, so we can seek
            state = self.bin.get_state(timeout=STATE_CHANGE_TIMEOUT)[1]
            if state < Gst.State.PAUSED:
                self.bin.set_state(Gst.State.PAUSED)
                self.bin.get_state(timeout=STATE_CHANGE_TIMEOUT)

            pos = max(0, int(pos))
            gst_time = pos * Gst.MSECOND
            event = Gst.Event.new_seek(
                1.0, Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                Gst.SeekType.SET, gst_time, Gst.SeekType.NONE, 0)
            if self.bin.send_event(event):
                # to get a good estimate for when get_position fails
                self._last_position = pos
                # For cases where we get the position directly after
                # a seek and the seek is not done, GStreamer returns
                # a valid 0 position. To prevent this we try to emit seek only
                # after it is done. Every flushing seek will trigger
                # an async_done message on the bus, so we queue the seek
                # event here and emit in the bus message callback.
                self._active_seeks.append((self.song, pos))

    def _end(self, stopped):
        print_d("End song")
        song, info = self.song, self.info

        # set the new volume before the signals to avoid delays
        if self._in_gapless_transition:
            self.song = self._source.current
            self.volume = self.volume

        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        self.__info_buffer = self.song = self.info = None
        if song is not info:
            self.emit('song-ended', info, stopped)
        self.emit('song-ended', song, stopped)

        # Then, set up the next song.
        self.song = self.info = self._source.current
        self.emit('song-started', self.song)

        print_d("Next song")
        if self.song is not None:
            if not self._in_gapless_transition:
                self.volume = self.volume
                # Due to extensive problems with playbin2, we destroy the
                # entire pipeline and recreate it each time we're not in
                # a gapless transition.
                self.__destroy_pipeline()
                if not self.__init_pipeline():
                    self.paused = True
            if self.bin:
                if self.paused:
                    self.bin.set_state(Gst.State.PAUSED)
                else:
                    self.bin.set_state(Gst.State.PLAYING)
        else:
            self.__destroy_pipeline()
            self.paused = True

        self._in_gapless_transition = False

    def __tag(self, tags, librarian):
        if self.song and self.song.multisong:
            self._fill_stream(tags, librarian)
        elif self.song and self.song.fill_metadata:
            pass

    def _fill_stream(self, tags, librarian):
        # get a new remote file
        new_info = self.__info_buffer
        if not new_info:
            new_info = type(self.song)(self.song["~filename"])
            new_info.multisong = False
            new_info.streamsong = True

            # copy from the old songs
            # we should probably listen to the library for self.song changes
            new_info.update(self.song)
            new_info.update(self.info)

        changed = False
        info_changed = False

        tags = TagListWrapper(tags, merge=True)
        tags = parse_gstreamer_taglist(tags)

        for key, value in sanitize_tags(tags, stream=False).iteritems():
            if self.song.get(key) != value:
                changed = True
                self.song[key] = value

        for key, value in sanitize_tags(tags, stream=True).iteritems():
            if new_info.get(key) != value:
                info_changed = True
                new_info[key] = value

        if info_changed:
            # in case the title changed, make self.info a new instance
            # and emit ended/started for the the old/new one
            if self.info.get("title") != new_info.get("title"):
                if self.info is not self.song:
                    self.emit('song-ended', self.info, False)
                self.info = new_info
                self.__info_buffer = None
                self.emit('song-started', self.info)
            else:
                # in case title didn't changed, update the values of the
                # old instance if there is one and tell the library.
                if self.info is not self.song:
                    self.info.update(new_info)
                    librarian.changed([self.info])
                else:
                    # So we don't loose all tags before the first title
                    # save it for later
                    self.__info_buffer = new_info

        if changed:
            librarian.changed([self.song])

    @property
    def eq_bands(self):
        if Gst.ElementFactory.find('equalizer-10bands'):
            return [29, 59, 119, 237, 474, 947, 1889, 3770, 7523, 15011]
        else:
            return []

    def update_eq_values(self):
        need_eq = any(self._eq_values)
        if need_eq != self._use_eq:
            self._use_eq = need_eq
            self._rebuild_pipeline()

        if self._eq_element:
            for band, val in enumerate(self._eq_values):
                self._eq_element.set_property('band%d' % band, val)

    def can_play_uri(self, uri):
        if not Gst.uri_is_valid(uri):
            return False
        try:
            Gst.Element.make_from_uri(Gst.URIType.SRC, uri, '')
        except GLib.GError:
            return False
        return True


def init(librarian):
    # Enable error messages by default
    if Gst.debug_get_default_threshold() == Gst.DebugLevel.NONE:
        Gst.debug_set_default_threshold(Gst.DebugLevel.ERROR)

    if Gst.Element.make_from_uri(
        Gst.URIType.SRC,
        "file:///fake/path/for/gst", ""):
        return GStreamerPlayer(librarian)
    else:
        raise PlayerError(
            _("Unable to open input files"),
            _("GStreamer has no element to handle reading files. Check "
                "your GStreamer installation settings."))

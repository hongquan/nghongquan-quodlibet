# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import popen2

import devices
import const

class Device(dict):
    # The default icon for this device.
    icon = os.path.join(const.BASEDIR, "device-generic.png")

    # The value of the HAL-property 'portable_audio_player.type' for this device.
    type = ""

    # The UDI of this device
    udi = None

    # Set this to a hash with default values for user-configurable properties
    defaults = None

    def __init__(self, udi):
        self.udi = udi
        self.__device = devices.get_interface(udi)

        # Find device volume.
        # FIXME: should we support more than one volume?
        for vol_udi in devices._hal.FindDeviceStringMatch(
            'info.parent', udi):
            volume = devices.get_interface(vol_udi)
            if volume.GetProperty('volume.is_mounted'):
                self.__volume = volume
                break

        # Load default properties.
        if self.defaults: self.update(self.defaults)

        # Load configured properties.
        if devices._config.has_section(udi):
            self.update(dict(devices._config.items(udi)))

        # Set a sensible name if none is set.
        if not self.has_key('name'):
            dict.__setitem__(self, 'name', "%s %s" % (
                self.__device.GetProperty('info.vendor'),
                self.__device.GetProperty('info.product')))

    # Store all changed properties in the ConfigParser.
    def __setitem__(self, key, value):
        print "__setitem__ hook called: %s => %s" % (key, value)
        if not devices._config.has_section(self.udi):
            devices._config.add_section(self.udi)
        devices._config.set(self.udi, key, value)
        dict.__setitem__(self, key, value)

    # Returns a list of AudioFile instances representing the songs
    # on this device. If rescan is False the list can be cached.
    def list(self, songlist, rescan=False): return []

    # Copies a song to the device. This will be called once for each song.
    # If the copy was successful, it should return an AudioFile instance,
    # which will be added to the songlist.
    # If the copy failed, it should return False or a string describing the
    # error.
    def copy(self, songlist, song): raise NotImplementedError

    # Deletes a song from the device. This will be called once for each song.
    # This is not needed if the device is file-based, i.e. the songs returned
    # by list() have is_file set to True.
    # If the delete was successful, it should return True.
    # If the delete failed, it should return False or a string describing the
    # error.
    #
    # def delete(self, songlist, song): ... return True
    delete = None

    # This will be called once after all songs have been copied/deleted.
    # The WaitLoadWindow can be (ab)used to display status messages.
    #
    # def cleanup(self, wlw, action='copy'/'delete'): ...
    cleanup = None

    # Should return True if the device is connected.
    def is_connected(self):
        return self.__volume.GetProperty('volume.is_mounted')

    # Return the mountpoint of the device's volume.
    def mountpoint(self):
        return str(self.__volume.GetProperty('volume.mount_point'))

    # Eject the device, should return True on success.
    # If the eject failed, it should return False or a string describing the
    # error.
    # If the device is not ejectable, set it to None.
    def eject(self):
        dev = self.__interface.GetProperty('block.dev')
        pipe = popen2.Popen4("eject %s" % dev)
        if pipe.wait() == 0: return True
        else: return pipe.fromchild.read()

    # Returns a tuple with the size of this device and the free space.
    def get_space(self):
        info = os.statvfs(self.mountpoint())
        space = info.f_bsize * info.f_blocks
        free = info.f_bsize * info.f_bavail
        return (space, free)

    # Returns a list of tuples for device-specific settings which should be
    # displayed in the properties dialog.
    #
    # The first value should be a string and will be used as a title.
    # Include an underline for changeable settings.
    #
    # The second value should be an appropriate gtk.Widget for the setting.
    # It can also be a string, in which case it will be displayed with a Label
    # and won't be changeable.
    #
    # The third value is the name of the object's key which should be
    # set when the widget is changed. If the second value is a string, this
    # will be ignored.
    #
    # Separators can be added by passing (None, None, None).
    def Properties(self): return []

# Copyright 2020 Andrzej Cichocki

# This file is part of Cowpox.
#
# Cowpox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cowpox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cowpox.  If not, see <http://www.gnu.org/licenses/>.

# This file incorporates work covered by the following copyright and
# permission notice:

# Copyright (c) 2010-2017 Kivy Team and other contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

cdef extern void android_sound_queue(int, char *, char *, long long, long long)
cdef extern void android_sound_play(int, char *, char *, long long, long long)
cdef extern void android_sound_stop(int)
cdef extern void android_sound_seek(int, float)
cdef extern void android_sound_dequeue(int)
cdef extern void android_sound_playing_name(int, char *, int)
cdef extern void android_sound_pause(int)
cdef extern void android_sound_unpause(int)

cdef extern void android_sound_set_volume(int, float)
cdef extern void android_sound_set_secondary_volume(int, float)
cdef extern void android_sound_set_pan(int, float)

cdef extern int android_sound_queue_depth(int)
cdef extern int android_sound_get_pos(int)
cdef extern int android_sound_get_length(int)

channels = set()
volumes = { }

def queue(channel, file, name, fadein=0, tight=False):

    channels.add(channel)

    real_fn = file.name
    base = getattr(file, "base", -1)
    length = getattr(file, "length", -1)

    android_sound_queue(channel, name, real_fn, base, length)

def play(channel, file, name, paused=False, fadein=0, tight=False):

    channels.add(channel)

    real_fn = file.name    
    base = getattr(file, "base", -1)
    length = getattr(file, "length", -1)

    android_sound_play(channel, name, real_fn, base, length)

def seek(channel, position):
   android_sound_seek(channel, position)

def stop(channel):
    android_sound_stop(channel)

def dequeue(channel, even_tight=False):
    android_sound_dequeue(channel)

def queue_depth(channel):
    return android_sound_queue_depth(channel)

def playing_name(channel):
    cdef char buf[1024]

    android_sound_playing_name(channel, buf, 1024)

    rv = buf
    if not len(rv):
        return None
    return rv

def pause(channel):
    android_sound_pause(channel)
    return

def unpause(channel):
    android_sound_unpause(channel)
    return

def unpause_all():
    for i in channels:
        unpause(i)

def pause_all():
    for i in channels:
        pause(i)

def fadeout(channel, ms):
    stop(channel)

def busy(channel):
    return playing_name(channel) != None

def get_pos(channel):
    return android_sound_get_pos(channel)

def get_length(channel):
    return android_sound_get_length(channel)

def set_volume(channel, volume):
    android_sound_set_volume(channel, volume)
    volumes[channel] = volume

def set_secondary_volume(channel, volume):
    android_sound_set_secondary_volume(channel, volume)

def set_pan(channel, pan):
    android_sound_set_pan(channel, pan)

def set_end_event(channel, event):
    return

def get_volume(channel):
    return volumes.get(channel, 1.0)

def init(freq, stereo, samples, status=False):
    return

def quit():
    for i in channels:
        stop(i)

def periodic():
    return

def alloc_event(surf):
    return

def refresh_event():
    return

def check_version(version):
    return


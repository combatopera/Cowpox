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

.PHONY: all build
VERSION := 2.0
ANN1 = udp://public.popcorn-tracker.org:6969/announce
ANN2 = udp://ipv4.tracker.harry.lu/announce
ANN3 = udp://tracker.opentrackr.org:1337/announce
ANN4 = udp://9.rarbg.com:2710/announce
ANN5 = udp://explodie.org:6969
ANN6 = udp://tracker.coppersurfer.tk:6969
ANN7 = udp://tracker.leechers-paradise.org:6969
ANN8 = udp://zer0day.ch:1337
TORRENT_ANNOUNCE := ${ANN1},${ANN2},${ANN3},${ANN4},${ANN5},${ANN6},${ANN7},${ANN8}
PACKAGE_FILENAME = kivy-buildozer-vm-${VERSION}.zip

all: packer repackage torrent upload

build:
	packer-io build template.json

repackage:
	cd output-kivy-buildozer-vm && mv Kivy kivy-buildozer-vm-${VERSION}
	cd output-kivy-buildozer-vm && zip -0 -r ${PACKAGE_FILENAME} kivy-buildozer-vm-${VERSION}

torrent:
	rm -f output-kivy-buildozer-vm/kivy-buildozer-vm.torrent
	mktorrent \
		-a ${TORRENT_ANNOUNCE} \
		-o output-kivy-buildozer-vm/kivy-buildozer-vm.torrent \
		-w http://txzone.net/files/torrents/${PACKAGE_FILENAME} \
		-v output-kivy-buildozer-vm/${PACKAGE_FILENAME}

upload:
	# txzone only for now, don't have access to kivy server
	rsync -avz --info=progress2 output-kivy-buildozer-vm/${PACKAGE_FILENAME} txzone.net:/var/www/websites/txzone.net/files/torrents/
	rsync -avz --info=progress2 output-kivy-buildozer-vm/kivy-buildozer-vm.torrent txzone.net:/var/www/websites/txzone.net/files/torrents/

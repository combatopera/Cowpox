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

FROM python AS base
RUN apt-get update && \
    apt-get install --yes --no-install-recommends apt-utils software-properties-common && \
    wget -qO - https://adoptopenjdk.jfrog.io/adoptopenjdk/api/gpg/key/public | apt-key add - && \
    add-apt-repository --yes https://adoptopenjdk.jfrog.io/adoptopenjdk/deb/ && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
    build-essential ccache cmake gettext adoptopenjdk-8-hotspot zip gradle
WORKDIR /root/project
COPY requirements.txt .
RUN pip install --upgrade -r requirements.txt

FROM base
RUN pip install pyflakes
COPY . .
RUN find -name '*.py' \
    -not -wholename ./pythonforandroid/recipes/android/src/android/__init__.py \
    -exec pyflakes '{}' +

FROM base
COPY . .
RUN pip install . && rm -rv "$PWD" | tail -1
ARG USER=bdoz
ARG GROUP=bdgp
ARG UID=7654
ARG GID=3210
RUN groupadd -g $GID $GROUP && useradd -g $GID -u $UID --create-home --shell /bin/bash $USER
WORKDIR /workspace
RUN bash -c 'home=$(eval "echo ~$USER") && volumes=($home/.buildozer $home/.gradle .buildozer bin . /mirror /project) && mkdir -pv "${volumes[@]}" && chown -v $USER:$GROUP "${volumes[@]}"' && git init
USER $USER
ENTRYPOINT ["Seizure", "/workspace", "/project"]
COPY workspace .
ENV P4A_bdozlib_DIR /project
WORKDIR /src

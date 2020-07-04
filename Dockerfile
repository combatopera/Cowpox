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

FROM python:3.8.3 AS base
RUN apt-get update && \
    apt-get install --yes --no-install-recommends apt-utils software-properties-common && \
    wget -qO - https://adoptopenjdk.jfrog.io/adoptopenjdk/api/gpg/key/public | apt-key add - && \
    add-apt-repository --yes https://adoptopenjdk.jfrog.io/adoptopenjdk/deb/ && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends adoptopenjdk-8-hotspot build-essential ccache cmake gettext gradle lld zip && \
    pip install pip==20.1.1 && \
    pip install pyven==43 && \
    echo /.pyven/ | tee ~/.gitignore_global && \
    git config --global core.excludesfile ~/.gitignore_global
WORKDIR /Cowpox
COPY project.arid .
RUN script='from pyven.projectinfo import ProjectInfo; from shlex import quote; print("pip install %s" % " ".join(quote(r) for r in ProjectInfo.seek(".").allrequires()))' && \
    eval "$(python -c "$script")" && \
    git init

FROM base AS test
COPY COPYING LICENSE.kivy .flakesignore ./
RUN tests # Prepare and cache environment.
COPY . .
RUN tests

FROM base
COPY . .
RUN pipify && pip install . && echo "extroot = $PWD" | tee /etc/settings.arid
ENTRYPOINT ["Cowpox"]
WORKDIR /workspace

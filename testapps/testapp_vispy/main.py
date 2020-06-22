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

"""
Demonstration of Tube
"""

print('testing!')
import ctypes
print('imported ctypes')
print(ctypes.__dict__)
print('dict done')
import ctypes.util
print('imported util')
print(ctypes.util.find_library)

import vispy
# vispy.set_log_level('debug')

import sys
from vispy import scene
from vispy.geometry.torusknot import TorusKnot

from colorsys import hsv_to_rgb
import numpy as np

canvas = scene.SceneCanvas(keys='interactive', bgcolor='white')
canvas.unfreeze()
canvas.view = canvas.central_widget.add_view()

points1 = TorusKnot(5, 3).first_component[:-1]
points1[:, 0] -= 20.
points1[:, 2] -= 15.

points2 = points1.copy()
points2[:, 2] += 30.

points3 = points1.copy()
points3[:, 0] += 41.
points3[:, 2] += 30

points4 = points1.copy()
points4[:, 0] += 41.

colors = np.linspace(0, 1, len(points1))
colors = np.array([hsv_to_rgb(c, 1, 1) for c in colors])

vertex_colors = np.random.random(8 * len(points1))
vertex_colors = np.array([hsv_to_rgb(c, 1, 1) for c in vertex_colors])

l1 = scene.visuals.Tube(points1,
                        shading='flat',
                        color=colors,  # this is overridden by
                                       # the vertex_colors argument
                        vertex_colors=vertex_colors,
                        tube_points=8)

l2 = scene.visuals.Tube(points2,
                        color=['red', 'green', 'blue'],
                        shading='smooth',
                        tube_points=8)

l3 = scene.visuals.Tube(points3,
                        color=colors,
                        shading='flat',
                        tube_points=8,
                        closed=True)

l4 = scene.visuals.Tube(points4,
                        color=colors,
                        shading='flat',
                        tube_points=8,
                        mode='lines')

canvas.view.add(l1)
canvas.view.add(l2)
canvas.view.add(l3)
canvas.view.add(l4)
canvas.view.camera = scene.TurntableCamera()
# tube does not expose its limits yet
canvas.view.camera.set_range((-20, 20), (-20, 20), (-20, 20))
canvas.show()

if __name__ == '__main__':
    if sys.flags.interactive != 1:
        canvas.app.run()

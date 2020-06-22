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

print('importing numpy')
import numpy as np
print('imported numpy')

print('importing matplotlib')

import matplotlib
print('imported matplotlib')

print('importing pyplot')

from matplotlib import pyplot as plt

print('imported pyplot')

fig, ax = plt.subplots()

print('created fig and ax')

ax.plot(np.random.random(50))

print('plotted something')

ax.set_xlabel('test label')

print('set a label')

fig.set_size_inches((5, 4))
fig.savefig('test.png')

print('saved fig')

from kivy.app import App
from kivy.base import runTouchApp
from kivy.uix.image import Image
from kivy.lang import Builder

class MatplotlibApp(App):
    def build(self):
        root = Builder.load_string("""
BoxLayout:
    orientation: 'vertical'
    Image:
        id: the_image
        source: 'test.png'
        allow_stretch: True
    Button:
        size_hint_y: None
        height: dp(40)
        text: 'new plot'
        on_release: app.generate_new_plot()
        """)
        return root
        
    def generate_new_plot(self):
        fig, ax = plt.subplots()
        ax.set_xlabel('test xlabel')
        ax.set_ylabel('test ylabel')
        ax.plot(np.random.random(50))
        ax.plot(np.sin(np.linspace(0, 3*np.pi, 30)))

        ax.legend(['random numbers', 'sin'])

        fig.set_size_inches((5, 4))
        fig.tight_layout()

        fig.savefig('test.png', dpi=150)

        self.root.ids.the_image.reload()
        



MatplotlibApp().run()
runTouchApp(Image(source='test.png', allow_stretch=True))

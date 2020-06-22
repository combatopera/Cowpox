// Copyright 2020 Andrzej Cichocki

// This file is part of Cowpox.
//
// Cowpox is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Cowpox is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Cowpox.  If not, see <http://www.gnu.org/licenses/>.

// This file incorporates work covered by the following copyright and
// permission notice:

// Copyright (c) 2010-2017 Kivy Team and other contributors
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

/**
 * This class takes care of managing resources for us. In our code, we
 * can't use R, since the name of the package containing R will
 * change. So this is the next best thing.
 */

package org.renpy.android;

import android.app.Activity;
import android.content.res.Resources;
import android.view.View;

import android.util.Log;

public class ResourceManager {

    private Activity act;
    private Resources res;

    public ResourceManager(Activity activity) {
        act = activity;
        res = act.getResources();
    }

    public int getIdentifier(String name, String kind) {
        Log.v("SDL", "getting identifier");
        Log.v("SDL", "kind is " + kind + " and name " + name);
        Log.v("SDL", "result is " + res.getIdentifier(name, kind, act.getPackageName()));
        return res.getIdentifier(name, kind, act.getPackageName());
    }

    public String getString(String name) {

        try {
            Log.v("SDL", "asked to get string " + name);
            return res.getString(getIdentifier(name, "string"));
        } catch (Exception e) {
            Log.v("SDL", "got exception looking for string!");
            return null;
        }
    }

    public View inflateView(String name) {
        int id = getIdentifier(name, "layout");
        return act.getLayoutInflater().inflate(id, null);
    }

    public View getViewById(View v, String name) {
        int id = getIdentifier(name, "id");
        return v.findViewById(id);
    }

}

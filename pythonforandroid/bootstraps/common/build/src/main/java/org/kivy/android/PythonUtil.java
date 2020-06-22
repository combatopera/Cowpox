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

package org.kivy.android;

import java.io.File;

import android.util.Log;
import java.util.ArrayList;
import java.io.FilenameFilter;
import java.util.regex.Pattern;


public class PythonUtil {
	private static final String TAG = "pythonutil";

    protected static void addLibraryIfExists(ArrayList<String> libsList, String pattern, File libsDir) {
        // pattern should be the name of the lib file, without the
        // preceding "lib" or suffix ".so", for instance "ssl.*" will
        // match files of the form "libssl.*.so".
        File [] files = libsDir.listFiles();

        pattern = "lib" + pattern + "\\.so";
        Pattern p = Pattern.compile(pattern);
        for (int i = 0; i < files.length; ++i) {
            File file = files[i];
            String name = file.getName();
            Log.v(TAG, "Checking pattern " + pattern + " against " + name);
            if (p.matcher(name).matches()) {
                Log.v(TAG, "Pattern " + pattern + " matched file " + name);
                libsList.add(name.substring(3, name.length() - 3));
            }
        }
    }

    protected static ArrayList<String> getLibraries(File libsDir) {
        ArrayList<String> libsList = new ArrayList<String>();
        addLibraryIfExists(libsList, "sqlite3", libsDir);
        addLibraryIfExists(libsList, "ffi", libsDir);
        addLibraryIfExists(libsList, "ssl.*", libsDir);
        addLibraryIfExists(libsList, "crypto.*", libsDir);
        libsList.add("python2.7");
        libsList.add("python3.5m");
        libsList.add("python3.6m");
        libsList.add("python3.7m");
        libsList.add("main");
        return libsList;
    }

    public static void loadLibraries(File filesDir, File libsDir) {
        String filesDirPath = filesDir.getAbsolutePath();
        boolean foundPython = false;

        for (String lib : getLibraries(libsDir)) {
            Log.v(TAG, "Loading library: " + lib);
            try {
                System.loadLibrary(lib);
                if (lib.startsWith("python")) {
                    foundPython = true;
                }
            } catch(UnsatisfiedLinkError e) {
                // If this is the last possible libpython
                // load, and it has failed, give a more
                // general error
                Log.v(TAG, "Library loading error: " + e.getMessage());
                if (lib.startsWith("python3.7") && !foundPython) {
                    throw new java.lang.RuntimeException("Could not load any libpythonYYY.so");
                } else if (lib.startsWith("python")) {
                    continue;
                } else {
                    Log.v(TAG, "An UnsatisfiedLinkError occurred loading " + lib);
                    throw e;
                }
            }
        }

        Log.v(TAG, "Loaded everything!");
	}
}

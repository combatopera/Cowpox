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

package org.kivy.android.launcher;

import java.io.UnsupportedEncodingException;
import java.io.File;
import java.io.FileInputStream;
import java.util.Properties;

import android.util.Log;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;


/**
 * This represents a project we've scanned for.
 */
public class Project {

    public String dir = null;
    String title = null;
    String author = null;
    Bitmap icon = null;
    public boolean landscape = false;

    static String decode(String s) {
        try {
            return new String(s.getBytes("ISO-8859-1"), "UTF-8");
        } catch (UnsupportedEncodingException e) {
            return s;
        }
    }

    /**
     * Scans directory for a android.txt file. If it finds one,
     * and it looks valid enough, then it creates a new Project,
     * and returns that. Otherwise, returns null.
     */
    public static Project scanDirectory(File dir) {

        // We might have a link file.
        if (dir.getAbsolutePath().endsWith(".link")) {
            try {

                // Scan the android.txt file.
                File propfile = new File(dir, "android.txt");
                FileInputStream in = new FileInputStream(propfile);
                Properties p = new Properties();
                p.load(in);
                in.close();

                String directory = p.getProperty("directory", null);

                if (directory == null) {
                    return null;
                }

                dir = new File(directory);

            } catch (Exception e) {
                Log.i("Project", "Couldn't open link file " + dir, e);
            }
        }

        // Make sure we're dealing with a directory.
        if (! dir.isDirectory()) {
            return null;
        }

        try {

            // Scan the android.txt file.
            File propfile = new File(dir, "android.txt");
            FileInputStream in = new FileInputStream(propfile);
            Properties p = new Properties();
            p.load(in);
            in.close();

            // Get the various properties.
            String title = decode(p.getProperty("title", "Untitled"));
            String author = decode(p.getProperty("author", ""));
            boolean landscape = p.getProperty("orientation", "portrait").equals("landscape");

            // Create the project object.
            Project rv = new Project();
            rv.title = title;
            rv.author = author;
            rv.icon = BitmapFactory.decodeFile(new File(dir, "icon.png").getAbsolutePath());
            rv.landscape = landscape;
            rv.dir = dir.getAbsolutePath();

            return rv;

        } catch (Exception e) {
            Log.i("Project", "Couldn't open android.txt", e);
        }

        return null;

    }
}

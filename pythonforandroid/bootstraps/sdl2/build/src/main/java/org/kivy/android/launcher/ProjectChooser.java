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

import android.app.Activity;
import android.os.Bundle;

import android.content.Intent;
import android.content.res.Resources;
import android.util.Log;
import android.view.View;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.AdapterView;
import android.os.Environment;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import android.net.Uri;

import org.renpy.android.ResourceManager;

public class ProjectChooser extends Activity implements AdapterView.OnItemClickListener {

    ResourceManager resourceManager;

    String urlScheme;

    @Override
    public void onStart()
    {
        super.onStart();

        resourceManager = new ResourceManager(this);

        urlScheme = resourceManager.getString("urlScheme");

        // Set the window title.
        setTitle(resourceManager.getString("appName"));

        // Scan the sdcard for files, and sort them.
        File dir = new File(Environment.getExternalStorageDirectory(), urlScheme);

        File entries[] = dir.listFiles();

        if (entries == null) {
            entries = new File[0];
        }

        Arrays.sort(entries);

        // Create a ProjectAdapter and fill it with projects.
        ProjectAdapter projectAdapter = new ProjectAdapter(this);

        // Populate it with the properties files.
        for (File d : entries) {
            Project p = Project.scanDirectory(d);
            if (p != null) {
                projectAdapter.add(p);
            }
        }

        if (projectAdapter.getCount() != 0) {        

            View v = resourceManager.inflateView("project_chooser");
            ListView l = (ListView) resourceManager.getViewById(v, "projectList");

            l.setAdapter(projectAdapter);                
            l.setOnItemClickListener(this);

            setContentView(v);

        } else {

            View v = resourceManager.inflateView("project_empty");
            TextView emptyText = (TextView) resourceManager.getViewById(v, "emptyText");

            emptyText.setText("No projects are available to launch. Please place a project into " + dir + " and restart this application. Press the back button to exit.");

            setContentView(v);
        }
    }

    public void onItemClick(AdapterView parent, View view, int position, long id) {
        Project p = (Project) parent.getItemAtPosition(position);

        Intent intent = new Intent(
                "org.kivy.LAUNCH",
                Uri.fromParts(urlScheme, p.dir, ""));

        intent.setClassName(getPackageName(), "org.kivy.android.PythonActivity");
        this.startActivity(intent);
        this.finish();
    }
}

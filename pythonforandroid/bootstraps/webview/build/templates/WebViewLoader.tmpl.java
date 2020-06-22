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

import android.util.Log;

import java.io.IOException;
import java.net.Socket;
import java.net.InetSocketAddress;

import android.os.SystemClock;

import android.os.Handler;

import org.kivy.android.PythonActivity;

public class WebViewLoader {
	private static final String TAG = "WebViewLoader";

    public static void testConnection() {

        while (true) {
            if (WebViewLoader.pingHost("localhost", {{ args.port }}, 100)) {
                Log.v(TAG, "Successfully pinged localhost:{{ args.port }}");
                Handler mainHandler = new Handler(PythonActivity.mActivity.getMainLooper());
                Runnable myRunnable = new Runnable() {
                        @Override
                        public void run() {
                            PythonActivity.mActivity.loadUrl("http://127.0.0.1:{{ args.port }}/");
                            Log.v(TAG, "Loaded webserver in webview");
                        }
                    };
                mainHandler.post(myRunnable);
                break;

            } else {
                Log.v(TAG, "Could not ping localhost:{{ args.port }}");
                try {
                    Thread.sleep(100);
                } catch(InterruptedException e) {
                    Log.v(TAG, "InterruptedException occurred when sleeping");
                }
            }
        }
    }

    public static boolean pingHost(String host, int port, int timeout) {
        Socket socket = new Socket();
        try {
            socket.connect(new InetSocketAddress(host, port), timeout);
            socket.close();
            return true;
        } catch (IOException e) {
            try {socket.close();} catch (IOException f) {return false;}
            return false; // Either timeout or unreachable or failed DNS lookup.
        }
    }
}

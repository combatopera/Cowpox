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
 * Copyright 2012 Kamran Zafar 
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); 
 * you may not use this file except in compliance with the License. 
 * You may obtain a copy of the License at 
 * 
 *      http://www.apache.org/licenses/LICENSE-2.0 
 * 
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
 * See the License for the specific language governing permissions and 
 * limitations under the License. 
 * 
 */

package org.kamranzafar.jtar;

import java.io.File;

/**
 * @author Kamran
 * 
 */
public class TarUtils {
	/**
	 * Determines the tar file size of the given folder/file path
	 * 
	 * @param path
	 * @return
	 */
	public static long calculateTarSize(File path) {
		return tarSize(path) + TarConstants.EOF_BLOCK;
	}

	private static long tarSize(File dir) {
		long size = 0;

		if (dir.isFile()) {
			return entrySize(dir.length());
		} else {
			File[] subFiles = dir.listFiles();

			if (subFiles != null && subFiles.length > 0) {
				for (File file : subFiles) {
					if (file.isFile()) {
						size += entrySize(file.length());
					} else {
						size += tarSize(file);
					}
				}
			} else {
				// Empty folder header
				return TarConstants.HEADER_BLOCK;
			}
		}

		return size;
	}

	private static long entrySize(long fileSize) {
		long size = 0;
		size += TarConstants.HEADER_BLOCK; // Header
		size += fileSize; // File size

		long extra = size % TarConstants.DATA_BLOCK;

		if (extra > 0) {
			size += (TarConstants.DATA_BLOCK - extra); // pad
		}

		return size;
	}

	public static String trim(String s, char c) {
		StringBuffer tmp = new StringBuffer(s);
		for (int i = 0; i < tmp.length(); i++) {
			if (tmp.charAt(i) != c) {
				break;
			} else {
				tmp.deleteCharAt(i);
			}
		}

		for (int i = tmp.length() - 1; i >= 0; i--) {
			if (tmp.charAt(i) != c) {
				break;
			} else {
				tmp.deleteCharAt(i);
			}
		}

		return tmp.toString();
	}
}

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

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.RandomAccessFile;

/**
 * @author Kamran Zafar
 * 
 */
public class TarOutputStream extends OutputStream {
	private final OutputStream out;
    private long bytesWritten;
    private long currentFileSize;
    private TarEntry currentEntry;

    public TarOutputStream(OutputStream out) {
        this.out = out;
        bytesWritten = 0;
        currentFileSize = 0;
    }

	public TarOutputStream(final File fout) throws FileNotFoundException {
		this.out = new BufferedOutputStream(new FileOutputStream(fout));
		bytesWritten = 0;
		currentFileSize = 0;
	}

	/**
	 * Opens a file for writing. 
	 */
	public TarOutputStream(final File fout, final boolean append) throws IOException {
		@SuppressWarnings("resource")
		RandomAccessFile raf = new RandomAccessFile(fout, "rw");
		final long fileSize = fout.length();
		if (append && fileSize > TarConstants.EOF_BLOCK) {
			raf.seek(fileSize - TarConstants.EOF_BLOCK);
		}
		out = new BufferedOutputStream(new FileOutputStream(raf.getFD()));
	}

    /**
     * Appends the EOF record and closes the stream
     * 
     * @see java.io.FilterOutputStream#close()
     */
    @Override
    public void close() throws IOException {
        closeCurrentEntry();
        write( new byte[TarConstants.EOF_BLOCK] );
        out.close();
    }
    /**
     * Writes a byte to the stream and updates byte counters
     * 
     * @see java.io.FilterOutputStream#write(int)
     */
    @Override
    public void write(int b) throws IOException {
        out.write( b );
        bytesWritten += 1;

        if (currentEntry != null) {
            currentFileSize += 1;
        }
    }

    /**
     * Checks if the bytes being written exceed the current entry size.
     * 
     * @see java.io.FilterOutputStream#write(byte[], int, int)
     */
    @Override
    public void write(byte[] b, int off, int len) throws IOException {
        if (currentEntry != null && !currentEntry.isDirectory()) {
            if (currentEntry.getSize() < currentFileSize + len) {
                throw new IOException( "The current entry[" + currentEntry.getName() + "] size["
                        + currentEntry.getSize() + "] is smaller than the bytes[" + ( currentFileSize + len )
                        + "] being written." );
            }
        }

        out.write( b, off, len );
        
        bytesWritten += len;

        if (currentEntry != null) {
            currentFileSize += len;
        }        
    }

    /**
     * Writes the next tar entry header on the stream
     * 
     * @param entry
     * @throws IOException
     */
    public void putNextEntry(TarEntry entry) throws IOException {
        closeCurrentEntry();

        byte[] header = new byte[TarConstants.HEADER_BLOCK];
        entry.writeEntryHeader( header );

        write( header );

        currentEntry = entry;
    }

    /**
     * Closes the current tar entry
     * 
     * @throws IOException
     */
    protected void closeCurrentEntry() throws IOException {
        if (currentEntry != null) {
            if (currentEntry.getSize() > currentFileSize) {
                throw new IOException( "The current entry[" + currentEntry.getName() + "] of size["
                        + currentEntry.getSize() + "] has not been fully written." );
            }

            currentEntry = null;
            currentFileSize = 0;

            pad();
        }
    }

    /**
     * Pads the last content block
     * 
     * @throws IOException
     */
    protected void pad() throws IOException {
        if (bytesWritten > 0) {
            int extra = (int) ( bytesWritten % TarConstants.DATA_BLOCK );

            if (extra > 0) {
                write( new byte[TarConstants.DATA_BLOCK - extra] );
            }
        }
    }
}

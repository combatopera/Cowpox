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

/**
 * @author Kamran Zafar
 * 
 */
public class Octal {

    /**
     * Parse an octal string from a header buffer. This is used for the file
     * permission mode value.
     * 
     * @param header
     *            The header buffer from which to parse.
     * @param offset
     *            The offset into the buffer from which to parse.
     * @param length
     *            The number of header bytes to parse.
     * 
     * @return The long value of the octal string.
     */
    public static long parseOctal(byte[] header, int offset, int length) {
        long result = 0;
        boolean stillPadding = true;

        int end = offset + length;
        for (int i = offset; i < end; ++i) {
            if (header[i] == 0)
                break;

            if (header[i] == (byte) ' ' || header[i] == '0') {
                if (stillPadding)
                    continue;

                if (header[i] == (byte) ' ')
                    break;
            }

            stillPadding = false;

            result = ( result << 3 ) + ( header[i] - '0' );
        }

        return result;
    }

    /**
     * Parse an octal integer from a header buffer.
     * 
     * @param value
     * @param buf
     *            The header buffer from which to parse.
     * @param offset
     *            The offset into the buffer from which to parse.
     * @param length
     *            The number of header bytes to parse.
     * 
     * @return The integer value of the octal bytes.
     */
    public static int getOctalBytes(long value, byte[] buf, int offset, int length) {
        int idx = length - 1;

        buf[offset + idx] = 0;
        --idx;
        buf[offset + idx] = (byte) ' ';
        --idx;

        if (value == 0) {
            buf[offset + idx] = (byte) '0';
            --idx;
        } else {
            for (long val = value; idx >= 0 && val > 0; --idx) {
                buf[offset + idx] = (byte) ( (byte) '0' + (byte) ( val & 7 ) );
                val = val >> 3;
            }
        }

        for (; idx >= 0; --idx) {
            buf[offset + idx] = (byte) ' ';
        }

        return offset + length;
    }

    /**
     * Parse the checksum octal integer from a header buffer.
     * 
     * @param value
     * @param buf
     *            The header buffer from which to parse.
     * @param offset
     *            The offset into the buffer from which to parse.
     * @param length
     *            The number of header bytes to parse.
     * @return The integer value of the entry's checksum.
     */
    public static int getCheckSumOctalBytes(long value, byte[] buf, int offset, int length) {
        getOctalBytes( value, buf, offset, length );
        buf[offset + length - 1] = (byte) ' ';
        buf[offset + length - 2] = 0;
        return offset + length;
    }

    /**
     * Parse an octal long integer from a header buffer.
     * 
     * @param value
     * @param buf
     *            The header buffer from which to parse.
     * @param offset
     *            The offset into the buffer from which to parse.
     * @param length
     *            The number of header bytes to parse.
     * 
     * @return The long value of the octal bytes.
     */
    public static int getLongOctalBytes(long value, byte[] buf, int offset, int length) {
        byte[] temp = new byte[length + 1];
        getOctalBytes( value, temp, 0, length + 1 );
        System.arraycopy( temp, 0, buf, offset, length );
        return offset + length;
    }

}

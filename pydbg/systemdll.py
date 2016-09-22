#
# PyDBG
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: system_dll.py 238 2010-04-05 20:40:46Z rgovostes $
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation;
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

"""
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
"""
import os
from ctypes import (
    POINTER, c_ulong, create_string_buffer,
    c_char, byref, windll, CDLL
)

from pydbg.defines import PAGE_READONLY, FILE_MAP_READ
from pydbg.windows_h import HANDLE, DWORD
from pydbg.errors import PDError

# MAC OS compatibility
try:
    kernel32 = windll.kernel32
    psapi = windll.psapi
except:
    kernel32 = CDLL(os.path.join(os.path.dirname(__file__), 'libmacdll.dylib'))
    psapi = kernel32


class SystemDLL:
    """System DLL descriptor object

    Used to keep track of loaded system DLLs and locations.

    @todo: Add PE parsing support.
    """

    def __init__(self, handle: HANDLE, base: DWORD):
        """

        Given a handle and base address of the loaded DLL,
        determine the DLL name and size to fully initialize
        the system DLL object.

        @type  handle: HANDLE
        @param handle: Handle to the loaded DLL
        @type  base:   DWORD
        @param base:   Loaded address of DLL

        @raise PDError: An exception is raised on failure.
        """

        self.handle = handle
        self.base = base
        self.name = None
        self.path = None
        self.pe = None
        self.size = 0

        # calculate the file size of the
        file_size_hi = c_ulong(0)
        file_size_lo = kernel32.GetFileSize(handle, byref(file_size_hi))
        self.size = (file_size_hi.value << 8) + file_size_lo

        # create a file mapping from the dll handle.
        file_map = kernel32.CreateFileMappingA(handle, 0, PAGE_READONLY, 0, 1, 0)

        if not file_map:
            raise PDError('CreateFileMappingA()', True)

        # Map a single byte of the dll into memory
        # so we can query for the file name.
        kernel32.MapViewOfFile.restype = POINTER(c_char)
        file_ptr = kernel32.MapViewOfFile(file_map, FILE_MAP_READ, 0, 0, 1)

        if file_ptr:
            # Query for the filename of the mapped file.
            filename = create_string_buffer(2048)
            psapi.GetMappedFileNameA(kernel32.GetCurrentProcess(),
                                     file_ptr, byref(filename), 2048)

            # Store the full path. this is kind of ghetto,
            # but i didn't want to mess with QueryDosDevice() etc ...
            self.path = os.sep + filename.value.split(os.sep, 3)[3]

            # Store the file name.
            # XXX - this really shouldn't be failing. but i've seen it happen.
            try:
                self.name = filename.value[filename.value.rindex(os.sep)+1:]
            except Exception:
                self.name = self.path

            kernel32.UnmapViewOfFile(file_ptr)

        kernel32.CloseHandle(file_map)

    def __del__(self):
        """Close the handle"""
        kernel32.CloseHandle(self.handle)


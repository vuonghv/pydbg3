#
# PyDBG
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: breakpoint.py 194 2007-04-05 15:31:53Z cameron $
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

import random
from pydbg.defines import DWORD, MEMORY_BASIC_INFORMATION


class Breakpoint(object):
    """Soft breakpoint object"""

    def __init__(self, address: DWORD = None,
                 original_byte: bytes = None,
                 description: str = '',
                 restore: bool = True,
                 handler=None):
        """
        @type  address:       DWORD
        @param address:       Address of breakpoint
        @type  original_byte: Byte
        @param original_byte: Original byte stored at breakpoint address
        @type  description:   String
        @param description:   (Optional) Description of breakpoint
        @type  restore:       Boolean
        @param restore:       (Optional, def=True) Flag controlling whether or not to restore the breakpoint
        @type  handler:       Function Pointer
        @param handler:       (Optional, def=None) Optional handler to call for this bp instead of the default handler
        """
        self.address = address
        self.original_byte = original_byte
        self.description = description
        self.restore = restore
        self.handler = handler


class MemBreakpoint(object):
    """Memory breakpoint object"""

    def __init__(self, address: DWORD = None, size: int = None,
                 mbi: MEMORY_BASIC_INFORMATION = None,
                 description: str = '', handler=None):
        """
        @type  address:     DWORD
        @param address:     Address of breakpoint
        @type  size:        Integer
        @param size:        Size of buffer we want to break on
        @type  mbi:         MEMORY_BASIC_INFORMATION
        @param mbi:         MEMORY_BASIC_INFORMATION of page containing buffer we want to break on
        @type  description: String
        @param description: (Optional) Description of breakpoint
        @type  handler:     Function Pointer
        @param handler:     (Optional, def=None) Optional handler to call for this bp instead of the default handler
        """

        self.address = address
        self.size = size
        self.mbi = mbi
        self.description = description
        self.handler = handler

        self.id = random.randint(0, 0xFFFFFFFF)  # unique breakpoint identifier
        self.read_count = 0   # number of times the target buffer was read from
        self.split_count = 0  # number of times this breakpoint was split
        self.copy_depth = 0   # degrees of separation from original buffer
        self.on_stack = False  # is this memory breakpoint on a stack buffer?


class HwBreakpoint(object):
    """Hardware breakpoint object"""

    def __init__(self, address: DWORD = None,
                 length: int = 0,
                 condition: int = None,
                 description: str = '',
                 restore: bool = True,
                 slot: int = None,
                 handler=None):
        """

        @type  address:     DWORD
        @param address:     Address to set hardware breakpoint at
        @type  length:      Integer (1, 2 or 4)
        @param length:      Size of hardware breakpoint (byte, word or dword)
        @type  condition:   Integer (HW_ACCESS, HW_WRITE, HW_EXECUTE)
        @param condition:   Condition to set the hardware breakpoint to activate on
        @type  description: String
        @param description: (Optional) Description of breakpoint
        @type  restore:     Boolean
        @param restore:     (Optional, def=True) Flag controlling whether or not to restore the breakpoint
        @type  slot:        Integer (0-3)
        @param slot:        (Optional, Def=None) Debug register slot this hardware breakpoint sits in.
        @type  handler:     Function Pointer
        @param handler:     (Optional, def=None) Optional handler to call for this bp instead of the default handler
        """

        self.address = address
        self.length = length
        self.condition = condition
        self.description = description
        self.restore = restore
        self.slot = slot
        self.handler = handler

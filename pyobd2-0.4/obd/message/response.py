#!/usr/bin/env python -3
########################################################################
# pyOBD-II -- a Python library for communicating with OBD-II vehicles
# Copyright (C) 2009 Peter J. Creath
#
# This file is part of pyOBD-II ("pyobd2").
#
# You can redistribute pyOBD-II and/or modify it under the terms of
# the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# To negotiate alternative licensing terms, please contact the author.
# See the LICENSE.txt file at the top of the source tree for further
# information.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyOBD-II.  If not, see <http://www.gnu.org/licenses/>.
########################################################################

"""Implementation of base Response classes"""

from obd.message.base import Message
from obd.util import untested
import obd.protocol

class Response(Message):
    """The base class (by convention) of response messages
    """
    pass


class VariableLengthResponse(Response):
    """The base class for variable-length response messages, whose
    representation varies somewhat between protocols (across multiple
    SIDs)

    length -- the length of the entire logical message
    item_count -- the number of items contained within the logical message    
    item_length -- set by subclasses, the number of bytes per each "item"
        in the response

    _get_item_bytes() -- used by subclasses to return the list of all items
        in the response
    """
    item_length = None  # subclasses need to set this

    def __init__(self, message_data, offset, pid):
        self.item_count_byte = None
        # For CAN responses, there's a preceding number-of-items byte, which
        # is necessary to determine the length of the response because
        # a single CAN message can contain multiple responses.  We need
        # to know the length before calling our parent's initializer.
        if isinstance(message_data.protocol, obd.protocol.ISO15765_4):
            self.item_count_byte = message_data.data_bytes[offset]
            self.item_count = self.item_count_byte
            self.length = self.item_count * self.item_length + 1
        Response.__init__(self, message_data, offset, pid)
        # In contrast, non-CAN protocols don't need the preceding byte,
        # because the number of items can be inferred from the message
        # length (since they only support one response per message)
        if self.item_count_byte == None:
            self.item_count = self.length // self.item_length
        return

    def _get_items_offset(self):
        """Return the starting byte (within self.data_bytes) of the items,
        taking into account any preceding item count ("NODI") byte.
        
        Some variable-length messages (such as VIN requests) have other
        preceding bytes (padding, etc.); they should override this.
        """
        if self.item_count_byte != None:
            offset = 1
        else:
            offset = 0
        return offset
    
    def _get_item_bytes(self):
        """Return the list of all items (as bytes) in the response; used by
        subclasses before decoding each item.
        """
        offset = self._get_items_offset()
        result = []
        for i in range(0, self.item_count):
            result.append(self.data_bytes[offset:offset+self.item_length])
            offset += self.item_length
        return result


# vim: softtabstop=4 shiftwidth=4 expandtab

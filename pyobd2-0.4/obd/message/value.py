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

import copy

from obd.util import untested
from obd.message.response import Response

"""
Support for querying and extracting values from OBD messages
"""

class Value(object):
    """Base class for encapsulating physical values returned by
    OBD requests
    """
    units = None
    _value_fmt = "%s"
    def __init__(self, label, value=None, raw_value=None, units=None):
        """label -- the label or name of the value instance
        value -- the substantive value (if already computed)
        raw_value -- the raw 8- or 16-bit integer in which
            this value is encoded in an OBD message, from
            which the substantive value will be computed
        units -- the relevant units (if any)
        """
        self.label = label
        if raw_value is not None:
            assert value is None
            value = self._convert_value(raw_value)
        self.value = value
        if units is not None:
            self.units = units
        return
    def _convert_value(self, raw_value):
        """Convert the value from the raw 8- or 16-bit integer
        into the actual value represented"""
        return raw_value
    def __str__(self):
        str = "%s=%s" % (self.label, self._value_str())
        if self.units:
            str += " " + self.units
        return str
    def _value_str(self):
        """Format the value as a string, customizable by subclass"""
        return self._value_fmt % self.value


class Factory(object):
    """Class for specifying which values appear in a message so that
    the appropriate Value subclass instances can be created automatically
    """
    def __init__(self, label, cls, byte_labels, convert=None):
        """
        label -- the label or name of the value specified
        cls -- the Value subclass to create to represent the value
        byte_labels -- the message byte labels (e.g. "A", "D") from
            which the value should be decoded
        convert -- an optional function to use to convert the 8-
            or 16-bit value extracted from the message into the
            true value; this is used for PIDs that use unique
            value encodings (unused by any other PID), which don't
            warrant an entirely separate Value subclass
        """
        self.label = label
        self.cls = cls
        self.set_range(byte_labels)
        self.convert = convert
        return
    def set_range(self, byte_labels):
        """
        Set the byte range that this factory will use when
        creating a value.
        
        byte_labels -- the message byte labels (e.g. "A", "D") from
            which the value should be decoded
        
        This method exists so that functions can clone existing
        factories and vary their range.
        """
        if not isinstance(byte_labels, list):
            byte_labels = [byte_labels]
        if len(byte_labels[0]) == 1:
            # A, B, etc.
            self.range = self._byte_range(byte_labels)
            self.extract_data = self._extract_byte_range
        else:
            # A0, D4, etc.
            self.range = self._bit_range(byte_labels)
            self.extract_data = self._extract_bit_range
        return
    def extract_value(self, message):
        """Return an instance of the appropriate Value subclass
        encapsulating the appropriate bytes of the given message.
        
        message -- the Message instance containing the bytes to
            extract
        """
        raw_value = self.extract_data(message, self.range)
        if self.convert:
            v = self.cls(self.label, value=self.convert(raw_value))
        else:
            v = self.cls(self.label, raw_value=raw_value)
        return v
    def _byte_range(self, labels):
        # The only lists we see in practice are singletons or
        # adjacent (e.g., A,B or C,D), so we don't actually
        # have to compute a range.  If that changes, these
        # assertions will fail.
        assert len(labels) <= 2
        if len(labels) == 2:
            assert ord(labels[1]) - ord(labels[0]) == 1
        return labels
    def _extract_byte_range(message, range):
        byte_values = [message.byte(l) for l in range]
        raw_value = message.decode_integer(byte_values)
        return raw_value
    _extract_byte_range = staticmethod(_extract_byte_range)
    def _bit_range(self, labels):
        # The only list we expect are singletons or inclusive
        # endpoints within the same byte
        assert len(labels) <= 2
        if len(labels) == 2:
            assert labels[0][0] == labels[1][0]
            byte_label = labels[0][0]
            lsb = int(labels[0][1:])
            msb = int(labels[1][1:])
            bits = range(msb, lsb-1, -1)
            labels = ["%s%d" % (byte_label, bit) for bit in bits]
        return labels
    def _extract_bit_range(message, range):
        bit_values = [message.bit(l) for l in range]
        raw_value = 0
        for b in bit_values:
            raw_value <<= 1
            raw_value |= b
        return raw_value
    _extract_bit_range = staticmethod(_extract_bit_range)
    

class ValueResponse(Response):
    """Base class for OBD responses whose contents can be
    completely defined and automatically extracted by Value
    factories
    
    values -- the list of values contained in the response,
        each value represented as an instance of a Value
        subclass
        
    See parent classes (e.g., Message) for other attributes.
    """
    _value_factories = []
    def __init__(self, message_data, offset, pid):
        """Initialize the object from the raw response from the vehicle"""
        Response.__init__(self, message_data, offset, pid)
        self.values = []
        for factory in self._value_factories:
            try:
                value = factory.extract_value(self)
                self.values.append(value)
            except IndexError:
                # Skip any values that weren't contained
                # in the message
                pass
        return
    def __str__(self):
        return "\n".join([str(v) for v in self.values])


class UntestedValueResponse(ValueResponse):
    """Internal test class for ValueResponse subclasses
    that have not yet been tested
    """
    def __init__(self, message_data, offset, pid):
        untested()
        ValueResponse.__init__(self, message_data, offset, pid)
        return


def value_response_variant(pid, base_class):
    """Create and return a PID-specific subclass of the given class
    with an overridable copy of its value factories so that they
    can be tweaked as needed
    """
    # Create a PID-specific subclass
    classname = base_class.__name__ + "%02X" % pid
    response_class = type(classname, (base_class,), {})
    # Copy the value factories so that the variant can be tweaked
    # without affecting the base class
    response_class._value_factories = copy.deepcopy(base_class._value_factories)
    return response_class


###################################
# Common value types

class Percentage(Value):
    units = "%"
    _value_fmt = "%3.1f"
    """Encapsulates percentage values encoded in OBD responses"""
    def __str__(self):
        return "%s=%s%%" % (self.label, self._value_str())
    def _value_str(self):
        """Override the default conversion of the value itself to
        a string, excluding label or unit"""
        return self._value_fmt % (self.value * 100.0)


class PositivePercentage(Percentage):
    """Encapsulates 0-100% values encoded in OBD responses"""
    def _convert_value(self, raw_value):
        return raw_value / 255.0


class Temperature(Value):
    """Encapsulates temperature values encoded in OBD responses"""
    units = "deg C"
    _value_fmt = "%.0f"
    def __str__(self):
        celsius = self._value_str()
        farenheit = self._value_fmt % ((self.value * 1.8) + 32.0)
        return "%s=%s deg C (%s deg F)" % (self.label, celsius, farenheit)

class Velocity(Value):
    """Encapsulates velocity values encoded in OBD responses"""
    units = "km/h"
    _value_fmt = "%.0f"
    def __str__(self):
        metric = self._value_str()
        imperial = self._value_fmt % (self.value / 1.609344)
        return "%s=%s km/h (%s mph)" % (self.label, metric, imperial)

class RPM(Value):
    """Encapsulates RPM values encoded in OBD responses"""
    units = "1/min"
    _value_fmt = "%.0f"

class ListValue(Value):
    """Parent class for list values encoded in OBD responses"""
    def _value_str(self):
        """Override the default conversion of the value itself to
        a string, excluding label or unit"""
        return ",".join([self._value_fmt % v for v in self.value])

class Bitfield(ListValue):
    """Encapsulates bitfield values encoded in OBD responses"""
    _fields = {}
    def _convert_value(self, raw_value):
        fields = []
        for mask in sorted(self._fields.keys()):
            if (raw_value & mask) == mask:
                fields.append(self._fields[mask])
                raw_value &= ~mask
        if raw_value:
            fields.append(raw_value)
        return fields

class Enumeration(Value):
    """Encapsulates enumerated values encoded in OBD responses"""
    _values = {}
    def _convert_value(self, raw_value):
        try:
            value = self._values[raw_value]
        except KeyError:
            untested()
            value = raw_value
        return value

class Duration(Value):
    """Encapsulates duration values encoded in OBD responses"""
    units = "sec"
    _value_fmt = "%.0f"

class Distance(Value):
    """Encapsulates distance values encoded in OBD responses"""
    units = "km"
    _value_fmt = "%.0f"
    def __str__(self):
        metric = self._value_str()
        imperial = self._value_fmt % (self.value / 1.609344)
        return "%s=%s km (%s miles)" % (self.label, metric, imperial)

class Voltage(Value):
    """Encapsulates voltage values encoded in OBD responses"""
    units = "V"
    _value_fmt = "%.2f"

class Current(Value):
    """Encapsulates voltage values encoded in OBD responses"""
    units = "mA"
    _value_fmt = "%.2f"

class Pressure(Value):
    """Encapsulates pressure values encoded in OBD responses"""
    units = "kPa"
    _value_fmt = "%.1f"
    def __str__(self):
        metric = self._value_str()
        imperial = self._value_fmt % (self.value * 0.1450377)
        return "%s=%s kPa (%s PSI)" % (self.label, metric, imperial)

class Timing(Value):
    """Encapsulates timing values encoded in OBD responses"""
    units = "deg"
    _value_fmt = "%.1f"

class Boolean(Value):
    """Encapsulates boolean values in OBD responses"""
    _label = ["NO", "YES"]
    def _value_str(self):
        """Override the default conversion of the value itself to
        a string"""
        return self._label[self.value]

class OnOffBoolean(Boolean):
    """Encapsulates on/off boolean values in OBD responses"""
    _label = ["OFF", "ON"]
    
class TextValue(Value):
    """Encapsulates text (ASCII) values in OBD responses"""
    pass

class CountValue(Value):
    """Encapsulates counter values in OBD responses"""
    units = "counts"

# vim: softtabstop=4 shiftwidth=4 expandtab

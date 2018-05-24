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

"""Support for Service $01 (Request Current Powertrain Diagnostic Data)
requests and responses"""

import copy

from obd.message import register_response_class
from obd.message.response import Response
from obd.message.value import *
from obd.util import *

###################################
# PID $00, $20, $40, $60, $80, $A0, $C0, $E0

class PIDSupportResponse(Response):
    """Encapsulates the response to PID-supported requests.
    
    This is also used for other similar requests, such as INFTYPs in SID $09.
    In addition to the standard Response (Message) attributes, this object
    provides:
    
    pid_supported[PID] -- a boolean value indicating whether a PID is supported;
        this will only include values reported by this response
        (pid+1...pid+0x20)
    supported_pids[] -- a list of the supported PIDs reported by this response;
        this makes iterating over supported PIDs very easy and legible
    """
    length = 4
    def __init__(self, message_data, offset, pid):
        assert (pid & 0x1F) == 0
        Response.__init__(self, message_data, offset, pid)

        self.pid_supported = {}
        self.supported_pids = []
        bits = self.decode_integer(self.data_bytes)
        for pid_bit in range(1, 33):
            # test each bit in the integer corresponding to each PID
            pid_supported = (bits & (1 << (32 - pid_bit))) != 0
            pid = self.pid + pid_bit
            self.pid_supported[pid] = pid_supported
            if pid_supported:
                self.supported_pids.append(pid)
        return


###################################
# PID $01

class MonitorTest(object):
    """Encapsulates one system monitor test as returned by Service $01, PID $01.
    
    The actual response (see MonitorStatusResponse) describes multiple such
    tests.
    
    name -- the name of the test
    supported -- a boolean indicating whether the test is supported by the
        vehicle
    ready -- only applicable if the test is supported, a boolean indicating
        whether the test is ready
    status() -- returns a string representing the test status
    """
    def __init__(self, name, supported, ready):
        self.name = name
        self.supported = supported
        self.ready = ready

    def status(self):
        """Return a string representing the system monitor's status.

        Ready/Not Ready only apply if the system monitor is supported.
        """
        status = "Not Supported"
        if (self.supported):
            if (self.ready):
                status = "Ready"
            else:
                status = "Not Ready"
        return status

    def __str__(self):
        return "%s: %s" % (self.name, self.status())


class TestReady(Boolean):
    """Encapsulates test "ready" values in OBD responses;
    for some insane reason, 0 = "ready", and 1 = not ready"""
    def _convert_value(self, raw_value):
        """Invert the raw bit into the actual value represented;
        i.e., ready is True or False"""
        return not raw_value


class MonitorStatusResponse(ValueResponse):
    """Encapsulates the response to a Mode 01, PID 01 request.

    mil -- a boolean indicating whether the Malfunction Indicator Light
        (MIL) is lighted
    dtc_count -- the number of Diagnostic Trouble Codes (DTCs) logged by the
        on-board diagnostics
    monitors -- a dict of MonitorTest objects, one for each system monitor
    continuous_monitors -- a list of Continuous Monitor keys
    non_continuous_monitors -- a list of Non-Continuous Monitor keys
    
    emissions_status() -- returns a string summarizing the readiness of
        common state emissions tests
    supported_monitors() -- returns a list of supported monitor keys
    incomplete_monitors() -- returns a list of incomplete (but supported)
        monitor keys
    """
    length = 4
    _value_factories = [
        Factory("DTC_CNT", Value, ["A0", "A6"]),
        Factory("MIL", OnOffBoolean, "A7"),
        Factory("MIS_SUP", Boolean, "B0"),
        Factory("FUEL_SUP", Boolean, "B1"),
        Factory("CCM_SUP", Boolean, "B2"),
        # B3 is used to select spark vs. compression ignition
        # (diesel) tests; see __init__()
        Factory("MIS_RDY", TestReady, "B4"),
        Factory("FUEL_RDY", TestReady, "B5"),
        Factory("CCM_RDY", TestReady, "B6")
    ]
    _spark_value_factories = [
        Factory("CAT_SUP", Boolean, "C0"),
        Factory("HCAT_SUP", Boolean, "C1"),
        Factory("EVAP_SUP", Boolean, "C2"),
        Factory("AIR_SUP", Boolean, "C3"),
        Factory("ACRF_SUP", Boolean, "C4"),
        Factory("O2S_SUP", Boolean, "C5"),
        Factory("HTR_SUP", Boolean, "C6"),
        Factory("EGR_SUP", Boolean, "C7"),
        Factory("CAT_RDY", TestReady, "D0"),
        Factory("HCAT_RDY", TestReady, "D1"),
        Factory("EVAP_RDY", TestReady, "D2"),
        Factory("AIR_RDY", TestReady, "D3"),
        Factory("ACRF_RDY", TestReady, "D4"),
        Factory("O2S_RDY", TestReady, "D5"),
        Factory("HTR_RDY", TestReady, "D6"),
        Factory("EGR_RDY", TestReady, "D7"),
    ]
    _diesel_value_factories = [
        Factory("HCCATSUP", Boolean, "C0"),
        Factory("NCAT_SUP", Boolean, "C1"),
        Factory("BP_SUP", Boolean, "C3"),
        Factory("EGS_SUP", Boolean, "C5"),
        Factory("PM_SUP", Boolean, "C6"),
        Factory("EGR_SUP", Boolean, "C7"),
        Factory("HCCATRDY", TestReady, "D0"),
        Factory("NCAT_RDY", TestReady, "D1"),
        Factory("BP_RDY", TestReady, "D3"),
        Factory("EGS_RDY", TestReady, "D5"),
        Factory("PM_RDY", TestReady, "D6"),
        Factory("EGR_RDY", TestReady, "D7"),
    ]

    _monitor_definitions = {
        # See http://obddiagnostics.com/obdinfo/pids1-2.html
        # and http://en.wikipedia.org/wiki/OBD-II_PIDs#Bitwise_encoded_PIDs
        "misfire":         ["Misfire",     "MIS_SUP",  "MIS_RDY"],
        "fuel_system":     ["Fuel System", "FUEL_SUP", "FUEL_RDY"],
        "components":      ["Components",  "CCM_SUP",  "CCM_RDY"],
        # Spark
        "catalyst":        ["Catalyst",             "CAT_SUP",  "CAT_RDY"],
        "catalyst_heater": ["Catalyst Heater",      "HCAT_SUP", "HCAT_RDY"],
        "evap":            ["Evaporative System",   "EVAP_SUP", "EVAP_RDY"],
        "secondary_air":   ["Secondary Air System", "AIR_SUP",  "AIR_RDY"],
        "ac":              ["A/C System",           "ACRF_SUP", "ACRF_RDY"],
        "o2":              ["O2 Sensor",            "O2S_SUP",  "O2S_RDY"],
        "o2_heater":       ["O2 Sensor Heater",     "HTR_SUP",  "HTR_RDY"],
        # Diesel
        "nmhc_catalyst":   ["NMHC Catalyst",      "HCCATSUP", "HCCATRDY"],
        "nox":             ["NOx Aftertreatment", "NCAT_SUP", "NCAT_RDY"],
        "egs":             ["Exhaust Gas Sensor", "EGS_SUP",  "EGS_RDY"],
        "pm_filter":       ["PM Filter",          "PM_SUP",   "PM_RDY"],
        # Both
        "egr":             ["Exhaust Gas Recirculation (EGR)", "EGR_SUP", "EGR_RDY"],
        }
    ordered_monitors = [ "misfire", "fuel_system", "components",
                         "catalyst", "catalyst_heater",
                         "evap", "secondary_air", "ac", "o2", "o2_heater",
                         "nmhc_catalyst", "nox", "egs", "pm_filter",
                         "egr" ]
    continuous_monitors = set([ "misfire", "fuel_system", "components" ])
    non_continuous_monitors = set(ordered_monitors) - continuous_monitors

    def __init__(self, message_data, offset, pid):
        """Initialize the object from the raw response from the vehicle"""
        ValueResponse.__init__(self, message_data, offset, pid)
        # Choose the appropriate ignition-specific factories
        self.diesel = self.bit("B3")
        if self.diesel:
            factories = self._diesel_value_factories
        else:
            factories = self._spark_value_factories
        # Extract ignition-specific values
        for factory in factories:
            value = factory.extract_value(self)
            self.values.append(value)
        # Create a temporary dict of values
        values = {}
        for value in self.values:
            values[value.label] = value.value
        # Set up the structured attributes based on the values
        self.mil = values["MIL"]
        self.dtc_count = values["DTC_CNT"]
        self.monitors = {}
        for key, defn in self._monitor_definitions.items():
            name, supported, ready = defn
            try:
                supported = values[supported]
                ready = values[ready]
                self.monitors[key] = MonitorTest(name, supported, ready)
            except KeyError as e:
                # skip the irrelevant (spark vs. diesel) monitors
                pass
        return

    def _monitors_status(self, monitors):
        """(Internal) Return a string of the status of the specified monitors.

        monitors -- a set of monitor keys to query"""
        s = ""
        for key in self.ordered_monitors:
            if key in monitors and key in self.monitors:
                m = self.monitors[key]
                s += "%-40s %s\n" % (m.name + " Monitor", m.status())
        return s

    def emissions_status(self):
        """Return a string approximating state inspection readiness results."""
        if self.diesel:
            untested()
        return self._monitors_status(self.non_continuous_monitors)

    def supported_monitors(self):
        """Return a set of supported monitor keys."""
        if self.diesel:
            untested()
        supported = set([])
        for key, m in self.monitors.items():
            if (m.status() != "Not Supported"):
                supported.add(key)
        return supported

    def incomplete_monitors(self):
        """Return a set of incomplete (but supported) monitor keys."""
        if self.diesel:
            untested()
        incomplete = set([])
        for key, m in self.monitors.items():
            if (m.status() == "Not Ready"):
                incomplete.add(key)
        return incomplete


###################################
# PID $03

class FuelSystemStatus(Bitfield):
    _fields = {
        0x01: "OL",
        0x02: "CL",
        0x04: "OL-Drive",
        0x08: "OL-Fault",
        0x10: "CL-Fault",
    }

class FuelSystemResponse(ValueResponse):
    """Encapsulates the response to a Mode 01, PID 03 request"""
    length = 2
    _value_factories = [
        Factory("FUELSYS1", FuelSystemStatus, "A"),
        Factory("FUELSYS2", FuelSystemStatus, "B")
    ]


###################################
# PID $04

class LoadValueResponse(ValueResponse):
    """Encapsulates the response to a Mode 01, PID 04 request"""
    length = 1
    _value_factories = [Factory("LOAD_PCT", PositivePercentage, "A")]


###################################
# PID $05

class LowTemperature(Temperature):
    """Encapsulates temperatures between -40 and +215 degC"""
    def _convert_value(self, raw_value):
        return raw_value - 40.0

class EngineCoolantTempResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 05 request"""
    length = 1
    _value_factories = [Factory("ECT", LowTemperature, "A")]


###################################
# PID $06-$09, $55-58

class FuelTrim(Percentage):
    """Encapsulates fuel trim values encoded in OBD responses"""
    def _convert_value(self, raw_value):
        return (raw_value / 128.0) - 1.0

class FuelTrimResponse(ValueResponse):
    """Encapsulates the response to Mode 01 fuel trim requests
    (PID 06-09, 55-58)"""
    # NOTE: length is variable, either 1 or 2 bytes depending on
    # how many banks of oxygen sensors there are.
    _value_factories = [
        Factory("A", FuelTrim, "A"),
        Factory("B", FuelTrim, "B")
    ]

def _fuel_trim_response(pid, labels):
    """Create the PID-specific variant of the fuel trim response"""
    response_class = value_response_variant(pid, FuelTrimResponse)
    assert len(labels) == len(response_class._value_factories)
    # Override the value factories using the given labels
    for i, label in enumerate(labels):
        response_class._value_factories[i].label = label
    return response_class


###################################
# PID $0A, $22, $23, $59

class FuelRailPressureResponse(ValueResponse):
    length = 1
    # 22, 23, and 59 use two bytes
    _value_factories = [Factory("FRP", Pressure, ["A", "B"])]

def _fuel_rail_pressure_response(pid, scale, byte_labels=None):
    response_class = value_response_variant(pid, FuelRailPressureResponse)
    # override the conversion function using the given scale factor
    factory = response_class._value_factories[0]
    factory.convert = lambda p: scale * p
    # override the byte labels if given (for PID $0A)
    if byte_labels:
        factory.set_range(byte_labels)
    response_class.length = len(factory.range)
    return response_class


###################################
# PID $0B

class ManifoldAbsolutePressureResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 33 request"""
    length = 1
    # TODO: tweak the pressure instance so that its imperial measure
    # is inHg instead of PSI
    _value_factories = [Factory("MAP", Pressure, "A")]


###################################
# PID $0C

class EngineRPM(RPM):
    """Encapsulates engine RPM encoded in OBD responses"""
    def _convert_value(self, raw_value):
        return raw_value / 4.0
        
class EngineRPMResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 0C request"""
    length = 2
    _value_factories = [Factory("RPM", EngineRPM, ["A", "B"])]


###################################
# PID $0D

class VehicleSpeedResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 0D request"""
    length = 1
    _value_factories = [Factory("VSS", Velocity, "A")]


###################################
# PID $0E

class IgnitionTiming(Timing):
    """Encapsulates ignition timing encoded in OBD responses"""
    def _convert_value(self, raw_value):
        return (raw_value - 128) * 0.5

class IgnitionTimingResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 0E request"""
    length = 1
    _value_factories = [Factory("SPARKADV", IgnitionTiming, "A")]


###################################
# PID $0F

class IntakeAirTempResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 0F request"""
    length = 1
    _value_factories = [Factory("IAT", LowTemperature, "A")]


###################################
# PID $10

class AirFlowRate(Value):
    """Encapsulates engine air flow rate encoded in OBD responses"""
    units = "g/s"
    def _convert_value(self, raw_value):
        return raw_value / 100.0
    _value_fmt = "%.2f"
    def __str__(self):
        metric = self._value_str()
        imperial = self.value * 60.0 / 453.59237
        imperial = self._value_fmt % imperial
        return "%s=%s g/s (%s lb/min)" % (self.label, metric, imperial)
        
class MassAirFlowResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 10 request"""
    length = 2
    _value_factories = [Factory("MAF", AirFlowRate, ["A", "B"])]


###################################
# PID $11

class AbsoluteThrottleResponse(ValueResponse):
    """Encapsulates the response to a Mode 01, PID 11 request"""
    length = 1
    _value_factories = [Factory("TP", PositivePercentage, "A")]


###################################
# PID $13

class O2SLocation2Bank(Bitfield):
    _fields = {
        0x01: "O2S11",
        0x02: "O2S12",
        0x04: "O2S13",
        0x08: "O2S14",
        0x10: "O2S21",
        0x20: "O2S22",
        0x40: "O2S23",
        0x80: "O2S24",
    }

class O2SLocation2BankResponse(ValueResponse):
    """Encapsulates the response to a Mode 01, PID 13 request"""
    length = 1
    _value_factories = [Factory("O2SLOC", O2SLocation2Bank, "A")]


###################################
# PID $14-1B

class O2SensorVoltage(Voltage):
    """Encapsulates voltages between 0V and 1.275V"""
    def _convert_value(self, raw_value):
        return raw_value * 0.005
    _value_fmt = "%.3f"
    
class O2SensorResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 14-1B requests"""
    length = 2
    _value_factories = [
        Factory("O2S", O2SensorVoltage, "A"),
        Factory("SHRTFT", FuelTrim, "B")
    ]
    def __init__(self, message_data, offset, pid):
        # TODO: remove the factories that don't apply to this vehicle;
        # this depends on PID $13 or $1D
        ValueResponse.__init__(self, message_data, offset, pid)
        return
    
def _o2_sensor_response(pid, base_response, banks_and_sensors):
    """Create the PID-specific variant of the O2 sensor response"""
    response_class = value_response_variant(pid, base_response)
    # Set up new value factories for each bank and sensor given
    factories = []
    for bank_and_sensor in banks_and_sensors:
        for factory in response_class._value_factories:
            factory = copy.deepcopy(factory)
            factory.label = factory.label + bank_and_sensor
            factories.append(factory)
    response_class._value_factories = factories
    return response_class


###################################
# PID $1C

class OBDSupport(Enumeration):
    _values = {
        0x01: "OBD II",
        0x02: "OBD",
        0x03: "OBD and OBD II",
        0x04: "OBD I",
        0x05: "NO OBD",
        0x06: "EOBD",
        0x07: "EOBD and OBD II",
        0x08: "EOBD and OBD",
        0x09: "EOBD, OBD, and OBD II",
        0x0A: "JOBD",
        0x0B: "JOBD and OBD II",
        0x0C: "JOBD and EOBD",
        0x0D: "JOBD, EOBD, and OBD II",
        0x11: "EMD",
        0x12: "EMD+",
        0x13: "HD OBD-C",
        0x14: "HD OBD",
        0x15: "WWH OBD",
        0x17: "HD EOBD-I",
        0x18: "HD EOBD-I N",
        0x19: "HD EOBD-II",
        0x1A: "HD EOBD-II N",
        0x1C: "OBDBr-1",
        0x1D: "OBDBr-2",
    }

class OBDSupportResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 1C request"""
    length = 1
    _value_factories = [Factory("OBDSUP", OBDSupport, "A")]


###################################
# PID $1D

class O2SLocation4Bank(Bitfield):
    _fields = {
        0x01: "O2S11",
        0x02: "O2S12",
        0x04: "O2S21",
        0x08: "O2S22",
        0x10: "O2S31",
        0x20: "O2S32",
        0x40: "O2S41",
        0x80: "O2S42",
    }

class O2SLocation4BankResponse(ValueResponse):
    """Encapsulates the response to a Mode 01, PID 1D request"""
    length = 1
    _value_factories = [Factory("O2SLOC", O2SLocation4Bank, "A")]


###################################
# PID $1F

class EngineRuntimeResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 1F request"""
    length = 2
    _value_factories = [Factory("RUNTM", Duration, ["A", "B"])]


###################################
# PID $21

class MILDistanceResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 21 request"""
    length = 2
    _value_factories = [Factory("MIL_DIST", Distance, ["A", "B"])]


###################################
# PID $24-2B

class O2SensorLambda(Value):
    """Encapsulates equivalence ratio (lambda)"""
    def _convert_value(self, raw_value):
        return raw_value * 0.0000305
    _value_fmt = "%.3f"
    
class O2SensorWideVoltage(Voltage):
    """Encapsulates voltages between 0V and 7.999V"""
    def _convert_value(self, raw_value):
        return raw_value * 8.0 / 65535.0
    _value_fmt = "%.3f"
    
class O2SensorWideResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 14-1B requests"""
    length = 4
    _value_factories = [
        Factory("LAMBDA", O2SensorLambda, ["A", "B"]),
        Factory("O2S", O2SensorWideVoltage, ["C", "D"]),
    ]
    def __init__(self, message_data, offset, pid):
        # TODO: remove the factories that don't apply to this vehicle;
        # this depends on PID $13 or $1D; we may change the class
        # hierarchy to inherit from O2SensorResponse
        # TODO: adjust the scaling at runtime depending on the
        # maximum values specified by PID $4F (when present)
        ValueResponse.__init__(self, message_data, offset, pid)
        return
    

###################################
# PID $2F

class FuelLevelResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 2F request"""
    length = 1
    _value_factories = [Factory("FLI", PositivePercentage, "A")]


###################################
# PID $33

class BarometricPressureResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 33 request"""
    length = 1
    # TODO: tweak the pressure instance so that its imperial measure
    # is inHg instead of PSI
    _value_factories = [Factory("BARO", Pressure, "A")]


###################################
# PID $34-3B

class O2SensorCurrent(Current):
    """Encapsulates voltages between 0V and 7.999V"""
    def _convert_value(self, raw_value):
        return (raw_value * 128.0 / 32768.0) - 128.0
    
class O2SensorCurrentResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 14-1B requests"""
    length = 4
    _value_factories = [
        Factory("LAMBDA", O2SensorLambda, ["A", "B"]),
        Factory("O2S", O2SensorCurrent, ["C", "D"]),
    ]
    def __init__(self, message_data, offset, pid):
        # TODO: remove the factories that don't apply to this vehicle;
        # this depends on PID $13 or $1D; we may change the class
        # hierarchy to inherit from O2SensorResponse
        # TODO: adjust the scaling at runtime depending on the
        # maximum values specified by PID $4F (when present)
        ValueResponse.__init__(self, message_data, offset, pid)
        return
    

###################################
# PID $42

class ControlModuleVoltage(Voltage):
    """Encapsulates engine RPM encoded in OBD responses"""
    def _convert_value(self, raw_value):
        return raw_value / 1000.0
        
class ControlModuleVoltageResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 42 request"""
    length = 2
    _value_factories = [Factory("VPWR", ControlModuleVoltage, ["A", "B"])]


###################################
# PID $45

class RelativeThrottleResponse(ValueResponse):
    """Encapsulates the response to a Mode 01, PID 45 request"""
    length = 1
    _value_factories = [Factory("TP_R", PositivePercentage, "A")]


###################################
# PID $46

class AmbientAirTempResponse(ValueResponse):
    """Encapsulates the response to Mode 01, PID 46 request"""
    length = 1
    _value_factories = [Factory("AAT", LowTemperature, "A")]


###################################
# Registration

_pid_classes = {
    0x00: PIDSupportResponse,
    0x01: MonitorStatusResponse,
    0x03: FuelSystemResponse,
    0x04: LoadValueResponse,
    0x05: EngineCoolantTempResponse,
    0x06: _fuel_trim_response(0x06, ["SHRTFT1", "SHRTFT3"]),
    0x07: _fuel_trim_response(0x07, ["LONGFT1", "LONGFT3"]),
    0x08: _fuel_trim_response(0x08, ["SHRTFT2", "SHRTFT4"]),
    0x09: _fuel_trim_response(0x09, ["LONGFT2", "LONGFT4"]),
    0x0A: _fuel_rail_pressure_response(0x0A, 3.0, ["A"]),
    0x0B: ManifoldAbsolutePressureResponse,
    0x0C: EngineRPMResponse,
    0x0D: VehicleSpeedResponse,
    0x0E: IgnitionTimingResponse,
    0x0F: IntakeAirTempResponse,
    0x10: MassAirFlowResponse,
    0x11: AbsoluteThrottleResponse,
    0x13: O2SLocation2BankResponse,
    0x14: _o2_sensor_response(0x14, O2SensorResponse, ["11"]),
    0x15: _o2_sensor_response(0x15, O2SensorResponse, ["12"]),
    0x16: _o2_sensor_response(0x16, O2SensorResponse, ["13", "21"]),
    0x17: _o2_sensor_response(0x17, O2SensorResponse, ["14", "22"]),
    0x18: _o2_sensor_response(0x18, O2SensorResponse, ["21", "31"]),
    0x19: _o2_sensor_response(0x19, O2SensorResponse, ["22", "32"]),
    0x1A: _o2_sensor_response(0x1A, O2SensorResponse, ["23", "41"]),
    0x1B: _o2_sensor_response(0x1B, O2SensorResponse, ["24", "42"]),
    0x1C: OBDSupportResponse,
    0x1D: O2SLocation4BankResponse,
    0x1F: EngineRuntimeResponse,
    0x20: PIDSupportResponse,
    0x21: MILDistanceResponse,
    0x22: _fuel_rail_pressure_response(0x22, 0.079),
    0x23: _fuel_rail_pressure_response(0x23, 10.0),
    0x24: _o2_sensor_response(0x24, O2SensorWideResponse, ["11"]),
    0x25: _o2_sensor_response(0x25, O2SensorWideResponse, ["12"]),
    0x26: _o2_sensor_response(0x26, O2SensorWideResponse, ["13", "21"]),
    0x27: _o2_sensor_response(0x27, O2SensorWideResponse, ["14", "22"]),
    0x28: _o2_sensor_response(0x28, O2SensorWideResponse, ["21", "31"]),
    0x29: _o2_sensor_response(0x29, O2SensorWideResponse, ["22", "32"]),
    0x2A: _o2_sensor_response(0x2A, O2SensorWideResponse, ["23", "41"]),
    0x2B: _o2_sensor_response(0x2B, O2SensorWideResponse, ["24", "42"]),
    0x2F: FuelLevelResponse,
    0x33: BarometricPressureResponse,
    0x34: _o2_sensor_response(0x34, O2SensorCurrentResponse, ["11"]),
    0x35: _o2_sensor_response(0x35, O2SensorCurrentResponse, ["12"]),
    0x36: _o2_sensor_response(0x36, O2SensorCurrentResponse, ["13", "21"]),
    0x37: _o2_sensor_response(0x37, O2SensorCurrentResponse, ["14", "22"]),
    0x38: _o2_sensor_response(0x38, O2SensorCurrentResponse, ["21", "31"]),
    0x39: _o2_sensor_response(0x39, O2SensorCurrentResponse, ["22", "32"]),
    0x3A: _o2_sensor_response(0x3A, O2SensorCurrentResponse, ["23", "41"]),
    0x3B: _o2_sensor_response(0x3B, O2SensorCurrentResponse, ["24", "42"]),
    0x40: PIDSupportResponse,
    0x42: ControlModuleVoltageResponse,
    0x45: RelativeThrottleResponse,
    0x46: AmbientAirTempResponse,
    0x55: _fuel_trim_response(0x55, ["STSO2FT1", "STSO2FT3"]),
    0x56: _fuel_trim_response(0x56, ["LGSO2FT1", "LGSO2FT3"]),
    0x57: _fuel_trim_response(0x57, ["STSO2FT2", "STSO2FT4"]),
    0x58: _fuel_trim_response(0x58, ["LGSO2FT2", "LGSO2FT4"]),
    0x59: _fuel_rail_pressure_response(0x59, 10.0),
    0x60: PIDSupportResponse,
    0x80: PIDSupportResponse,
    0xA0: PIDSupportResponse,
    0xC0: PIDSupportResponse,
    0xE0: PIDSupportResponse,
    }

for _pid, class_ in _pid_classes.items():
    register_response_class(sid=0x01, pid=_pid, cls=class_)

"""
lengths = {
    0x01: { # SID $01
        0x02: 2,
        0x03: 2,
        0x04: 1,
        0x05: 1,
        # 6-9 are 1-or-2
        0x0A: 1,
        0x0B: 1,
        0x0C: 2,
        0x0D: 1,
        0x0E: 1,
        0x0F: 1,
        0x10: 2,
        0x11: 1,
        0x12: 1,
        0x13: 1,
        0x14: 2,
        0x15: 2,
        0x16: 2,
        0x17: 2,
        0x18: 2,
        0x19: 2,
        0x1A: 2,
        0x1B: 2,
        0x1C: 1,
        0x1D: 1,        
        0x1E: 1,
        0x1F: 2,
        0x21: 2,
        0x22: 2,
        0x23: 2,
        0x24: 4,
        0x25: 4,
        0x26: 4,
        0x27: 4,
        0x28: 4,
        0x29: 4,
        0x2A: 4,
        0x2B: 4,
        0x2C: 1,
        0x2D: 1,
        0x2E: 1,
        0x2F: 1,
        0x30: 1,
        0x31: 2,
        0x32: 2,
        0x33: 1,
        0x34: 4,
        0x35: 4,
        0x36: 4,
        0x37: 4,
        0x38: 4,
        0x39: 4,
        0x3A: 4,
        0x3B: 4,
        0x3C: 2,
        0x3D: 2,
        0x3E: 2,
        0x3F: 2,
        0x41: 4,
        0x42: 2,
        0x43: 2,
        0x44: 2,
        0x45: 1,
        0x46: 1,
        0x47: 1,
        0x48: 1,
        0x49: 1,
        0x4A: 1,
        0x4B: 1,
        0x4C: 1,
        0x4D: 2,
        0x4E: 2,
        0x4F: 4,
        0x50: 4,
        0x51: 1,
        0x52: 1,
        0x53: 2,
        0x54: 2,
        # 55-58 are 1-or-2
        0x59: 2,
        0x5A: 1,
        0x5B: 1,
        0x5C: 1,
        0x5D: 2,
        0x5E: 2,
        0x5F: 1,
        0x61: 1,
        0x62: 1,
        0x63: 2,
        0x64: 5,
        0x65: 2,
        0x66: 5,
        0x67: 3,
        0x68: 7,
        0x69: 7,
        0x6A: 5,
        0x6B: 5,
        0x6C: 5,
        0x6D: 11,
        0x6E: 9,
        0x6F: 3,
        0x70: 10,
        0x71: 6,
        0x72: 5,
        0x73: 5,
        0x74: 5,
        0x75: 7,
        0x76: 7,        
        0x77: 5,
        0x78: 9,
        0x79: 9,
        0x7A: 7,
        0x7B: 7,
        0x7C: 9,
        0x7D: 1,
        0x7E: 1,
        0x7F: 13,
        0x81: 41,
        0x82: 41,
        0x83: 9,
        0x84: 1,
        0x85: 10,
        0x86: 5,
        0x87: 5,
        0x88: 13,
        0x89: 41,
        0x8A: 41,
        0x8B: 8,        
        },
"""


# vim: softtabstop=4 shiftwidth=4 expandtab

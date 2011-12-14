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

import testharness
from testharness import create_obd_message_from_ascii
import obd
from obd.message.value import *


#######################
# Functions for defining expected values for PIDs containing
# many values in a single response

def _readiness_tests(variants={}, diesel=False):
    # default values
    tests = [
        ("DTC_CNT", Value, 0, None),
        ("MIL", Boolean, False, None),
        ("MIS_SUP", Boolean, False, None),
        ("FUEL_SUP", Boolean, False, None),
        ("CCM_SUP", Boolean, False, None),
        ("MIS_RDY", Boolean, True, None),
        ("FUEL_RDY", Boolean, True, None),
        ("CCM_RDY", Boolean, True, None)
    ]
    spark_tests = [
        ("CAT_SUP", Boolean, False, None),
        ("HCAT_SUP", Boolean, False, None),
        ("EVAP_SUP", Boolean, False, None),
        ("AIR_SUP", Boolean, False, None),
        ("ACRF_SUP", Boolean, False, None),
        ("O2S_SUP", Boolean, False, None),
        ("HTR_SUP", Boolean, False, None),
        ("EGR_SUP", Boolean, False, None),
        ("CAT_RDY", Boolean, True, None),
        ("HCAT_RDY", Boolean, True, None),
        ("EVAP_RDY", Boolean, True, None),
        ("AIR_RDY", Boolean, True, None),
        ("ACRF_RDY", Boolean, True, None),
        ("O2S_RDY", Boolean, True, None),
        ("HTR_RDY", Boolean, True, None),
        ("EGR_RDY", Boolean, True, None),
    ]
    diesel_tests = [
        ("HCCATSUP", Boolean, False, None),
        ("NCAT_SUP", Boolean, False, None),
        ("BP_SUP", Boolean, False, None),
        ("EGS_SUP", Boolean, False, None),
        ("PM_SUP", Boolean, False, None),
        ("EGR_SUP", Boolean, False, None),
        ("HCCATRDY", Boolean, True, None),
        ("NCAT_RDY", Boolean, True, None),
        ("BP_RDY", Boolean, True, None),
        ("EGS_RDY", Boolean, True, None),
        ("PM_RDY", Boolean, True, None),
        ("EGR_RDY", Boolean, True, None),
    ]
    # Create default list depending on the ignition type
    if diesel:
        tests.extend(diesel_tests)
    else:
        tests.extend(spark_tests)
    # Update the expected values with any given variants
    for i, test in enumerate(tests):
        (label, cls, value, units) = test
        if label in variants:
            value = variants[label]
            tests[i] = (label, cls, value, units)
    return tests
    
def _readiness_diesel_tests(variants={}):
    return _readiness_tests(variants, diesel=True)


#######################
# The actual test cases

value_tests = {
    "41 01 00 00 00 00": _readiness_tests(),
    "41 01 7F 00 00 00": _readiness_tests({"DTC_CNT": 127}),
    "41 01 29 00 00 00": _readiness_tests({"DTC_CNT": 41}),
    "41 01 80 00 00 00": _readiness_tests({"MIL": True}),
    "41 01 00 01 00 00": _readiness_tests({"MIS_SUP": True}),
    "41 01 00 02 00 00": _readiness_tests({"FUEL_SUP": True}),
    "41 01 00 04 00 00": _readiness_tests({"CCM_SUP": True}),
    "41 01 00 10 00 00": _readiness_tests({"MIS_RDY": False}),
    "41 01 00 20 00 00": _readiness_tests({"FUEL_RDY": False}),
    "41 01 00 40 00 00": _readiness_tests({"CCM_RDY": False}),

    "41 01 00 00 01 00": _readiness_tests({"CAT_SUP": True}),
    "41 01 00 00 02 00": _readiness_tests({"HCAT_SUP": True}),
    "41 01 00 00 04 00": _readiness_tests({"EVAP_SUP": True}),
    "41 01 00 00 08 00": _readiness_tests({"AIR_SUP": True}),
    "41 01 00 00 10 00": _readiness_tests({"ACRF_SUP": True}),
    "41 01 00 00 20 00": _readiness_tests({"O2S_SUP": True}),
    "41 01 00 00 40 00": _readiness_tests({"HTR_SUP": True}),
    "41 01 00 00 80 00": _readiness_tests({"EGR_SUP": True}),
    "41 01 00 00 00 01": _readiness_tests({"CAT_RDY": False}),
    "41 01 00 00 00 02": _readiness_tests({"HCAT_RDY": False}),
    "41 01 00 00 00 04": _readiness_tests({"EVAP_RDY": False}),
    "41 01 00 00 00 08": _readiness_tests({"AIR_RDY": False}),
    "41 01 00 00 00 10": _readiness_tests({"ACRF_RDY": False}),
    "41 01 00 00 00 20": _readiness_tests({"O2S_RDY": False}),
    "41 01 00 00 00 40": _readiness_tests({"HTR_RDY": False}),
    "41 01 00 00 00 80": _readiness_tests({"EGR_RDY": False}),

    "41 01 00 08 01 00": _readiness_diesel_tests({"HCCATSUP": True}),
    "41 01 00 08 02 00": _readiness_diesel_tests({"NCAT_SUP": True}),
    "41 01 00 08 08 00": _readiness_diesel_tests({"BP_SUP": True}),
    "41 01 00 08 20 00": _readiness_diesel_tests({"EGS_SUP": True}),
    "41 01 00 08 40 00": _readiness_diesel_tests({"PM_SUP": True}),
    "41 01 00 08 80 00": _readiness_diesel_tests({"EGR_SUP": True}),
    "41 01 00 08 00 01": _readiness_diesel_tests({"HCCATRDY": False}),
    "41 01 00 08 00 02": _readiness_diesel_tests({"NCAT_RDY": False}),
    "41 01 00 08 00 08": _readiness_diesel_tests({"BP_RDY": False}),
    "41 01 00 08 00 20": _readiness_diesel_tests({"EGS_RDY": False}),
    "41 01 00 08 00 40": _readiness_diesel_tests({"PM_RDY": False}),
    "41 01 00 08 00 80": _readiness_diesel_tests({"EGR_RDY": False}),

    "41 03 01 02": [
                ("FUELSYS1", Bitfield, ["OL"], None),
                ("FUELSYS2", Bitfield, ["CL"], None)],
    "41 03 04 08": [
                ("FUELSYS1", Bitfield, ["OL-Drive"], None),
                ("FUELSYS2", Bitfield, ["OL-Fault"], None)],
    "41 03 10 00": [
                ("FUELSYS1", Bitfield, ["CL-Fault"], None),
                ("FUELSYS2", Bitfield, [], None)],
    "41 04 00": ("LOAD_PCT", Percentage, 0.0, "%"),
    "41 04 FF": ("LOAD_PCT", Percentage, 1.0, "%"),
    "41 05 00": ("ECT", Temperature, -40, "deg C"),
    "41 05 FF": ("ECT", Temperature, +215, "deg C"),
    # 06-09 added by _define_fuel_trim_tests
    "41 0A 00": ("FRP", Pressure, 0.0, "kPa"),
    "41 0A FF": ("FRP", Pressure, 765.0, "kPa"),
    "41 0B 00": ("MAP", Pressure, 0.0, "kPa"),
    "41 0B FF": ("MAP", Pressure, 255.0, "kPa"),
    "41 0C 00 00": ("RPM", RPM, 0.0, "1/min"),
    "41 0C FF FF": ("RPM", RPM, 16383.75, "1/min"),
    "41 0D 00": ("VSS", Velocity, 0.0, "km/h"),
    "41 0D FF": ("VSS", Velocity, 255.0, "km/h"),
    "41 0E 00": ("SPARKADV", Timing, -64.0, "deg"),
    "41 0E 80": ("SPARKADV", Timing, 0.0, "deg"),
    "41 0E FF": ("SPARKADV", Timing, 63.5, "deg"),
    "41 0F 00": ("IAT", Temperature, -40, "deg C"),
    "41 0F FF": ("IAT", Temperature, +215, "deg C"),
    "41 10 00 00": ("MAF", Value, 0.0, "g/s"),
    "41 10 FF FF": ("MAF", Value, 655.35, "g/s"),    
    "41 11 00": ("TP", Percentage, 0.0, "%"),
    "41 11 FF": ("TP", Percentage, 1.0, "%"),

    "41 13 00": ("O2SLOC", Bitfield, [], None),
    "41 13 01": ("O2SLOC", Bitfield, ["O2S11"], None),
    "41 13 02": ("O2SLOC", Bitfield, ["O2S12"], None),
    "41 13 04": ("O2SLOC", Bitfield, ["O2S13"], None),
    "41 13 08": ("O2SLOC", Bitfield, ["O2S14"], None),
    "41 13 10": ("O2SLOC", Bitfield, ["O2S21"], None),
    "41 13 20": ("O2SLOC", Bitfield, ["O2S22"], None),
    "41 13 40": ("O2SLOC", Bitfield, ["O2S23"], None),
    "41 13 80": ("O2SLOC", Bitfield, ["O2S24"], None),
    "41 13 03": ("O2SLOC", Bitfield, ["O2S11","O2S12"], None),
    "41 13 30": ("O2SLOC", Bitfield, ["O2S21","O2S22"], None),
    "41 13 CC": ("O2SLOC", Bitfield, ["O2S13","O2S14","O2S23","O2S24"], None),
    # 14-1B added by _define_o2_sensor_tests
    "41 1C 01": ("OBDSUP", Enumeration, "OBD II", None),
    "41 1C 02": ("OBDSUP", Enumeration, "OBD", None),
    "41 1C 03": ("OBDSUP", Enumeration, "OBD and OBD II", None),
    "41 1C 04": ("OBDSUP", Enumeration, "OBD I", None),
    "41 1C 05": ("OBDSUP", Enumeration, "NO OBD", None),
    "41 1C 06": ("OBDSUP", Enumeration, "EOBD", None),
    "41 1C 07": ("OBDSUP", Enumeration, "EOBD and OBD II", None),
    "41 1C 08": ("OBDSUP", Enumeration, "EOBD and OBD", None),
    "41 1C 09": ("OBDSUP", Enumeration, "EOBD, OBD, and OBD II", None),
    "41 1C 0A": ("OBDSUP", Enumeration, "JOBD", None),
    "41 1C 0B": ("OBDSUP", Enumeration, "JOBD and OBD II", None),
    "41 1C 0C": ("OBDSUP", Enumeration, "JOBD and EOBD", None),
    "41 1C 0D": ("OBDSUP", Enumeration, "JOBD, EOBD, and OBD II", None),
    "41 1C 11": ("OBDSUP", Enumeration, "EMD", None),
    "41 1C 12": ("OBDSUP", Enumeration, "EMD+", None),
    "41 1C 13": ("OBDSUP", Enumeration, "HD OBD-C", None),
    "41 1C 14": ("OBDSUP", Enumeration, "HD OBD", None),
    "41 1C 15": ("OBDSUP", Enumeration, "WWH OBD", None),
    "41 1C 17": ("OBDSUP", Enumeration, "HD EOBD-I", None),
    "41 1C 18": ("OBDSUP", Enumeration, "HD EOBD-I N", None),
    "41 1C 19": ("OBDSUP", Enumeration, "HD EOBD-II", None),
    "41 1C 1A": ("OBDSUP", Enumeration, "HD EOBD-II N", None),
    "41 1C 1C": ("OBDSUP", Enumeration, "OBDBr-1", None),
    "41 1C 1D": ("OBDSUP", Enumeration, "OBDBr-2", None),
    "41 1D 00": ("O2SLOC", Bitfield, [], None),
    "41 1D 01": ("O2SLOC", Bitfield, ["O2S11"], None),
    "41 1D 02": ("O2SLOC", Bitfield, ["O2S12"], None),
    "41 1D 04": ("O2SLOC", Bitfield, ["O2S21"], None),
    "41 1D 08": ("O2SLOC", Bitfield, ["O2S22"], None),
    "41 1D 10": ("O2SLOC", Bitfield, ["O2S31"], None),
    "41 1D 20": ("O2SLOC", Bitfield, ["O2S32"], None),
    "41 1D 40": ("O2SLOC", Bitfield, ["O2S41"], None),
    "41 1D 80": ("O2SLOC", Bitfield, ["O2S42"], None),
    "41 1D 03": ("O2SLOC", Bitfield, ["O2S11","O2S12"], None),
    "41 1D 30": ("O2SLOC", Bitfield, ["O2S31","O2S32"], None),
    "41 1D CC": ("O2SLOC", Bitfield, ["O2S21","O2S22","O2S41","O2S42"], None),
    
    "41 1F 00 00": ("RUNTM", Duration, 0.0, "sec"),
    "41 1F FF FF": ("RUNTM", Duration, 65535.0, "sec"),

    "41 21 00 00": ("MIL_DIST", Distance, 0.0, "km"),
    "41 21 FF FF": ("MIL_DIST", Distance, 65535.0, "km"),
    "41 22 00 00": ("FRP", Pressure, 0.0, "kPa"),
    "41 22 FF FF": ("FRP", Pressure, 5177.27, "kPa"),
    "41 23 00 00": ("FRP", Pressure, 0.0, "kPa"),
    "41 23 FF FF": ("FRP", Pressure, 655350.0, "kPa"),
    # 24-2B added by _define_o2_wide_sensor_tests
    
    "41 2F 00": ("FLI", Percentage, 0.0, "%"),
    "41 2F FF": ("FLI", Percentage, 1.0, "%"),
    
    "41 33 00": ("BARO", Pressure, 0.0, "kPa"),
    "41 33 FF": ("BARO", Pressure, 255.0, "kPa"),
    # 34-3B added by _define_o2_current_sensor_tests
    
    "41 42 00 00": ("VPWR", Voltage, 0.0, "V"),
    "41 42 FF FF": ("VPWR", Voltage, 65.535, "V"),
    
    "41 45 00": ("TP_R", Percentage, 0.0, "%"),
    "41 45 FF": ("TP_R", Percentage, 1.0, "%"),
    "41 46 00": ("AAT", Temperature, -40, "deg C"),
    "41 46 FF": ("AAT", Temperature, +215, "deg C"),
    
    # 55-58 added by _define_fuel_trim_tests
    "41 59 00 00": ("FRP", Pressure, 0.0, "kPa"),
    "41 59 FF FF": ("FRP", Pressure, 655350.0, "kPa"),
    }




#######################
# Families of PIDs that share identical data formats with slightly
# different semantics per PID

def _define_fuel_trim_tests(pid, label1, label2):
    tests = {
        "41 %02X 00" % pid: (label1, Percentage, -1.0, "%"),
        "41 %02X 80" % pid: (label1, Percentage, 0.0, "%"),
        "41 %02X FF" % pid: (label1, Percentage, 0.9922, "%"),
        "41 %02X FF 00" % pid: [(label1, Percentage, 0.9922, "%"),
                                (label2, Percentage, -1.0, "%")],
        "41 %02X 00 80" % pid: [(label1, Percentage, -1.0, "%"),
                                (label2, Percentage, 0.0, "%")],
        "41 %02X 00 FF"% pid: [(label1, Percentage, -1.0, "%"),
                                (label2, Percentage, 0.9922, "%")],
    }
    global value_tests
    value_tests.update(tests)
    return

_define_fuel_trim_tests(0x06, "SHRTFT1", "SHRTFT3")
_define_fuel_trim_tests(0x07, "LONGFT1", "LONGFT3")
_define_fuel_trim_tests(0x08, "SHRTFT2", "SHRTFT4")
_define_fuel_trim_tests(0x09, "LONGFT2", "LONGFT4")
_define_fuel_trim_tests(0x55, "STSO2FT1", "STSO2FT3")
_define_fuel_trim_tests(0x56, "LGSO2FT1", "LGSO2FT3")
_define_fuel_trim_tests(0x57, "STSO2FT2", "STSO2FT4")
_define_fuel_trim_tests(0x58, "LGSO2FT2", "LGSO2FT4")


def _o2_sensor_test(value1, value2, labels):
    tests = []
    for bank, sensor in labels:
        label1 = "O2S%d%d" % (bank, sensor)
        label2 = "SHRTFT%d%d" % (bank, sensor)
        tests.extend([(label1, Voltage, value1, "V"),
                      (label2, Percentage, value2, "%")])
    return tests

def _define_o2_sensor_tests(pid, labels):
    tests = {
        "41 %02X FF 00" % pid: _o2_sensor_test(1.275, -1.0, labels),
        "41 %02X 00 00" % pid: _o2_sensor_test(0, -1.0, labels),
        "41 %02X 00 80" % pid: _o2_sensor_test(0, 0.0, labels),
        "41 %02X 00 FF" % pid: _o2_sensor_test(0, 0.9922, labels),
    }
    global value_tests
    value_tests.update(tests)
    return

_define_o2_sensor_tests(0x14, [(1, 1)])
_define_o2_sensor_tests(0x15, [(1, 2)])
_define_o2_sensor_tests(0x16, [(1, 3), (2, 1)])
_define_o2_sensor_tests(0x17, [(1, 4), (2, 2)])
_define_o2_sensor_tests(0x18, [(2, 1), (3, 1)])
_define_o2_sensor_tests(0x19, [(2, 2), (3, 2)])
_define_o2_sensor_tests(0x1A, [(2, 3), (4, 1)])
_define_o2_sensor_tests(0x1B, [(2, 4), (4, 2)])


def _o2_wide_sensor_test(value1, value2, labels):
    tests = []
    for bank, sensor in labels:
        label1 = "LAMBDA%d%d" % (bank, sensor)
        label2 = "O2S%d%d" % (bank, sensor)
        tests.extend([(label1, Value, value1, None),
                      (label2, Voltage, value2, "V")])
    return tests

def _define_o2_wide_sensor_tests(pid, labels):
    tests = {
        "41 %02X 00 00 00 00" % pid: _o2_wide_sensor_test(0, 0.0, labels),
        "41 %02X FF FF 00 00" % pid: _o2_wide_sensor_test(1.999, 0.0, labels),
        "41 %02X 00 00 FF FF" % pid: _o2_wide_sensor_test(0, 8.0, labels),
    }
    global value_tests
    value_tests.update(tests)
    return

_define_o2_wide_sensor_tests(0x24, [(1, 1)])
_define_o2_wide_sensor_tests(0x25, [(1, 2)])
_define_o2_wide_sensor_tests(0x26, [(1, 3), (2, 1)])
_define_o2_wide_sensor_tests(0x27, [(1, 4), (2, 2)])
_define_o2_wide_sensor_tests(0x28, [(2, 1), (3, 1)])
_define_o2_wide_sensor_tests(0x29, [(2, 2), (3, 2)])
_define_o2_wide_sensor_tests(0x2A, [(2, 3), (4, 1)])
_define_o2_wide_sensor_tests(0x2B, [(2, 4), (4, 2)])


def _o2_current_sensor_test(value1, value2, labels):
    tests = []
    for bank, sensor in labels:
        label1 = "LAMBDA%d%d" % (bank, sensor)
        label2 = "O2S%d%d" % (bank, sensor)
        tests.extend([(label1, Value, value1, None),
                      (label2, Current, value2, "mA")])
    return tests

def _define_o2_current_sensor_tests(pid, labels):
    tests = {
        "41 %02X FF FF 00 00" % pid: _o2_current_sensor_test(1.999, -128, labels),
        "41 %02X 00 00 00 00" % pid: _o2_current_sensor_test(0, -128, labels),
        "41 %02X 00 00 80 00" % pid: _o2_current_sensor_test(0, 0, labels),
        "41 %02X 00 00 FF FF" % pid: _o2_current_sensor_test(0, 127.996, labels),
    }
    global value_tests
    value_tests.update(tests)
    return

_define_o2_current_sensor_tests(0x34, [(1, 1)])
_define_o2_current_sensor_tests(0x35, [(1, 2)])
_define_o2_current_sensor_tests(0x36, [(1, 3), (2, 1)])
_define_o2_current_sensor_tests(0x37, [(1, 4), (2, 2)])
_define_o2_current_sensor_tests(0x38, [(2, 1), (3, 1)])
_define_o2_current_sensor_tests(0x39, [(2, 2), (3, 2)])
_define_o2_current_sensor_tests(0x3A, [(2, 3), (4, 1)])
_define_o2_current_sensor_tests(0x3B, [(2, 4), (4, 2)])


#######################
# The actual test routines

def fp_eq(value, benchmark):
    """Compare two floating-point numbers using only the precision
    specified by the benchmark; return True if they are equal within
    that precision.
    """
    s = str(benchmark)
    precision = len(s) - s.index(".") - 1
    value = round(value, precision)
    return value == benchmark


def test_values():
    for key in sorted(value_tests.keys()):
        tests = value_tests[key]
        if isinstance(tests, tuple):
            tests = [tests]

        message = create_obd_message_from_ascii(key)
        assert len(tests) == len(message.values), "[%s] has %d values" % (key, len(message.values))

        for i, test in enumerate(tests):
            (label, cls, value, units) = test
            prefix = "[%s][%d] %s: " % (key, i, label)
            val = message.values[i]
            assert val.label == label, "%s%s != %s" % (prefix, val.label, label)
            assert isinstance(val, cls), "%s%s is not a %s" % (prefix, type(val).__name__, cls.__name__)
            if isinstance(value, float):
                assert fp_eq(val.value, value), "%s%f != %f" % (prefix, val.value, value)
            else:
                assert val.value == value, "%s%s != %s" % (prefix, str(val.value), str(value))
            assert val.units == units, "%s%s != %s" % (prefix, val.units, units)
    return


if __name__ == "__main__":
    test_values()

# vim: softtabstop=4 shiftwidth=4 expandtab

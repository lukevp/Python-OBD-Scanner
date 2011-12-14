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

"""Debugging and logging functions."""

import sys
import traceback
import os

DEBUG_FILE=sys.stderr
DEBUG_FLAGS = {}

def set_debug_file(f):
    """Change the file to which debugging messages are written.
    
    The default is sys.stderr.
    """
    global DEBUG_FILE
    DEBUG_FILE=f
    return

DEBUG_ALL = [ "error", "warn", "info", "debug" ]
def set_debug_level(level):
    """Configure which debug messages are emitted at a coarse level.
    
    level -- 0 = none, 1 = errors only, and the higher the more verbose
    """
    set_debug_flags(DEBUG_ALL[0:level])
    return

def set_debug_flags(flags):
    """Configure precisely which debug messages are emitted.
    
    flags -- a list of the types of debug messages desired; see
        DEBUG_ALL for the full list
    """
    global DEBUG_FLAGS
    DEBUG_FLAGS = {}
    for flag in flags:
        DEBUG_FLAGS[flag] = True
    return

def error(message):
    """Emit a debug message if 'error' logging is enabled"""
    if "error" in DEBUG_FLAGS: _debug_message(message, print_location=False)
    return
    
def warn(message):
    """Emit a debug message if 'warn' logging is enabled"""
    if "warn" in DEBUG_FLAGS: _debug_message(message, print_location=False)
    return
        
def info(message):
    """Emit a debug message if 'info' logging is enabled"""
    if "info" in DEBUG_FLAGS: _debug_message(message, print_location=False)
    return

def debug(message, print_location=True):
    """Emit a debug message if 'debug' logging is enabled
    
    message -- the message to emit
    print_location -- False to suppress the file and line where debug()
        was called"""
    if "debug" in DEBUG_FLAGS: _debug_message(message, print_location=print_location)

def _debug_message(message, print_location=True):
    """Print the message to the debug file prefixed by the file and line
    where the caller (debug(), error(), etc.) was called.
    """
    if not DEBUG_FILE: return
    prefix = ""
    if print_location:
        file, line = _get_caller_file_and_line(depth_offset=2)
        prefix = "%s:%d: " % (file, line)
    DEBUG_FILE.write("%s%s\n" % (prefix, message))
    return

def untested(message=""):
    """Print a banner any time an untested code path is reached.
    
    If the program has been invoked via "python -m pdb" this will also drop
    into the debugger for manual tracing.
    """
    file, line = _get_caller_file_and_line(depth_offset=1)
    debug("UNTESTED: %s (%s:%d)" % (message, file, line), print_location=False)
    # break into the debugger if run via "python -m pdb"
    # except when running under py.test
    if "py.test" in sys.modules:
        import py.test
        py.test.fail("reached untested code")
    elif "pdb" in sys.modules:
        import pdb
        pdb.set_trace()
    return

def unimplemented(message=""):
    """Print a banner any time an unimplemented feature is reached."""
    file, line = _get_caller_file_and_line(depth_offset=1)
    warn("UNIMPLEMENTED: %s (%s:%d)" % (message, file, line))
    return

def _get_caller_file_and_line(depth_offset=0):
    """Return the appropriate file name and line number
    
    depth_offset -- which frame on the call stack to examine"""
    caller = traceback.extract_stack(limit=2+depth_offset)[0]
    filepath = caller[0]
    line = caller[1]
    filename = os.path.basename(filepath)
    return (filename, line)


def _test():
    """Minimal test"""
    set_debug_flags(DEBUG_ALL)
    error("error")
    warn("warning")
    info("info")
    debug("debug")
    untested("untested")
    unimplemented("not yet implemented")
    set_debug_level(2)
    error("error")
    warn("warning")
    info("you shouldn't see this")
    debug("you shouldn't see this")
    untested("you shouldn't see this")
    unimplemented("not yet implemented")
    return

if __name__ == "__main__":
    _test()

# vim: softtabstop=4 shiftwidth=4 expandtab

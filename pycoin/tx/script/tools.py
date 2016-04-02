# -*- coding: utf-8 -*-
"""
Some tools for traversing Bitcoin VM scripts.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import binascii
import io
import logging
import struct

from . import ScriptError
from .opcodes import OPCODE_TO_INT, INT_TO_OPCODE
from ...intbytes import (bytes_from_int, bytes_to_ints, to_bytes, from_bytes,
                         int_to_bytes)

logger = logging.getLogger(__name__)


def get_opcode(script, pc):
    """Step through the script, returning a tuple with the next opcode, the next
    piece of data (if the opcode represents data), and the new PC."""
    opcode = ord(script[pc:pc + 1])
    pc += 1
    data = None
    if opcode <= OPCODE_TO_INT["OP_PUSHDATA4"]:
        if opcode < OPCODE_TO_INT["OP_PUSHDATA1"]:
            size = opcode
        elif opcode == OPCODE_TO_INT["OP_PUSHDATA1"]:
            size = from_bytes(script[pc:pc + 1], byteorder="little")
            pc += 1
        elif opcode == OPCODE_TO_INT["OP_PUSHDATA2"]:
            size = from_bytes(script[pc:pc + 2], byteorder="little")
            pc += 2
        elif opcode == OPCODE_TO_INT["OP_PUSHDATA4"]:
            size = from_bytes(script[pc:pc + 4], byteorder="little")
            pc += 4
        data = script[pc:pc + size]
        if len(data) < size:
            raise ScriptError("unexpected end of data when literal expected")
        pc += size
    return opcode, data, pc


def write_push_data(data_list, f):
    # return bytes that causes the given data to be pushed onto the stack
    for t in data_list:
        if len(t) == 0:
            f.write(bytes_from_int(OPCODE_TO_INT["OP_0"]))
            continue
        if len(t) == 1:
            v = bytes_to_ints(t)[0]
            if v <= 16:
                f.write(bytes_from_int(OPCODE_TO_INT["OP_%d" % v]))
                continue
        if len(t) <= 255:
            if len(t) > 75:
                f.write(bytes_from_int(OPCODE_TO_INT["OP_PUSHDATA1"]))
            f.write(int_to_bytes(len(t)))
            f.write(t)
        elif len(t) <= 65535:
            f.write(bytes_from_int(OPCODE_TO_INT["OP_PUSHDATA2"]))
            f.write(struct.pack("<H", len(t)))
            f.write(t)
        else:
            # This will never be used in practice as it makes the scripts too long.
            f.write(bytes_from_int(OPCODE_TO_INT["OP_PUSHDATA4"]))
            f.write(struct.pack("<L", len(t)))
            f.write(t)


def bin_script(data_list):
    f = io.BytesIO()
    write_push_data(data_list, f)
    return f.getvalue()


def compile(s):
    """Compile the given script. Returns a bytes object with the compiled script."""
    f = io.BytesIO()
    for t in s.split():
        if t in OPCODE_TO_INT:
            f.write(bytes_from_int(OPCODE_TO_INT[t]))
        elif ("OP_%s" % t) in OPCODE_TO_INT:
            f.write(bytes_from_int(OPCODE_TO_INT["OP_%s" % t]))
        elif t.startswith("0x"):
            d = binascii.unhexlify(t[2:])
            f.write(d)
        else:
            if (t[0], t[-1]) == ('[', ']'):
                t = t[1:-1]
            if t.startswith("'") and t.endswith("'"):
                v = t[1:-1].encode("utf8")
            else:
                v = binascii.unhexlify(t)
            write_push_data([v], f)
    return f.getvalue()


def disassemble_for_opcode_data(opcode, data):
    if data is not None and len(data) > 0:
        return "[%s]" % binascii.hexlify(data).decode("utf8")
    return INT_TO_OPCODE.get(opcode, "???")


def opcode_list(script):
    """Disassemble the given script. Returns a list of opcodes."""
    opcodes = []
    pc = 0
    while pc < len(script):
        opcode, data, pc = get_opcode(script, pc)
        opcodes.append(disassemble_for_opcode_data(opcode, data))
    return opcodes


def disassemble(script):
    """Disassemble the given script. Returns a string."""
    return ' '.join(opcode_list(script))


def delete_subscript(script, subscript):
    """Returns a script with the given subscript removed. The subscript
    must appear in the main script aligned to opcode boundaries for it
    to be removed."""
    new_script = bytearray()
    pc = 0
    while pc < len(script):
        opcode, data, new_pc = get_opcode(script, pc)
        section = script[pc:new_pc]
        if section != subscript:
            new_script.extend(section)
        pc = new_pc
    return bytes(new_script)

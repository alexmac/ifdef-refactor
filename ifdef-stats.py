#!/usr/bin/env python
# -*- Mode: Python; indent-tabs-mode: nil -*-
# vi: set ts=4 sw=4 expandtab:
#
# The MIT License
#
# Copyright (c) 2011 Alexander Macdonald
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import shutil
import tempfile
import re
import sys
import optparse
from ifdef.parser import *

def computestats(x, sizemap):
    if isinstance(x, Ifdef):
        for c in x.children:
            computestats(c, sizemap)
    elif isinstance(x, Branch):
        if x.cond is not None:
            tokens = gettokens(expr.parse((x.cond.expr))[0])
            for t in tokens:
                if t not in sizemap:
                    sizemap[t] = 0
                if x.size is None:
                    print "FAIL!"
                sizemap[t] += x.size
        for c in x.children:
            computestats(c, sizemap) 

def stats(file, sizemap):
    print "Gathering stats for %s" % file
    root = parsefile(file)
    calculatesizes(root)
    computestats(root, sizemap)

# ------------------------------------------------------------------------------
# Main Entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    optParser = optparse.OptionParser(usage='usage: %prog [ files ]\n\nIf no files are given then a recursive search for files ending\nwith c/cpp/mm/h is performed in the current directory.')
    optParser.set_defaults()    
    (opts, args) = optParser.parse_args()

    sizemap = {}
    
    if len(args) == 0:
        for (path, dirs, files) in os.walk("."):
            for file in files:
                if any(file.endswith(x) for x in [".c", ".cpp", ".h", ".mm"]):
                    fullpath = "%s/%s" % (path, file)
                    stats(fullpath, sizemap)
    else:
        for fullpath in args:
            stats(fullpath, sizemap)

    ss = sorted([(v,k) for (k,v) in sizemap.items()])
    for s in ss:
        print "%d %s" % s
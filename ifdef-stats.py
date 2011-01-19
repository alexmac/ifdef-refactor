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
                t = str(t)
                if t not in sizemap:
                    sizemap[t] = 0
                if x.size is None:
                    print "FAIL!"
                sizemap[t] += x.size
        for c in x.children:
            computestats(c, sizemap) 

def stats(file, sizemap):
    print "Gathering stats for %s" % file
    try:
        root = parsefile(file)
        calculatesizes(root)
        computestats(root, sizemap)
    except KeyboardInterrupt:
        exit(0)
    except:
        print "-- Error with file %s:" % file
        print sys.exc_info()[1]

def dumpstats(sizemap, outfile):
    if len(sizemap) == 0:
        return
    print "Dumping stats to %s" % outfile
    out = open(outfile, 'w')
    ss = sorted([(v,k) for (k,v) in sizemap.items()])
    for s in ss:
        out.write("%d %s\n" % s)
    out.close()

def accumulatestats(sizemap, infile):
    for line in open(infile, 'r').readlines():
        if line.startswith("#"):
            continue
        size = int(line.split()[0])
        token = line.split()[1]
        if token not in sizemap:
            sizemap[token] = size
        else:
            sizemap[token] += size

# ------------------------------------------------------------------------------
# Main Entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    optParser = optparse.OptionParser(usage='usage: %prog [ files ]\n\nIf no files are given then a recursive search for files ending\nwith c/cpp/mm/h is performed in the current directory.')
    optParser.set_defaults()
    optParser.add_option( '-m', '--merge-stats', dest="mergestats", default=False, action="store_true")
    optParser.add_option( '-t', '--generate-ifdef-tester', dest="generatetester", default=False, action="store_true")
    (opts, args) = optParser.parse_args()
    
    sizemap = {}
    
    if opts.mergestats:
        for (path, dirs, files) in os.walk("."):
            for file in files:
                fullpath = "%s/%s" % (path, file)
                if file == "ifdefstats.txt":
                    print "# merging stats from %s" % fullpath
                    accumulatestats(sizemap, fullpath)
        ss = sorted([(v,k) for (k,v) in sizemap.items()], reverse=True)
        for s in ss:
            print "%d %s" % s
        exit(0)
    
    if opts.generatetester:
        if len(args) != 1:
            print "point at the stats file you want to use"
            exit(0)
        accumulatestats(sizemap, args[0])
        ss = sorted(sizemap.items())
        for (k,v) in ss:
            try:
		int(k)
		continue
            except ValueError,TypeError:
		pass
            if k.find("\\") >= 0:
		continue
            print "#if defined(%s)" % k
            print "  #warning %s is ENABLED" % (k)
            print "#else"
            print "  #warning %s is DISABLED" % k
            print "#endif\n"
        exit(0)

    if len(args) == 0:
        for (path, dirs, files) in os.walk("."):
            for file in files:
                if any(file.endswith(x) for x in [".c", ".cpp", ".h", ".mm"]):
                    fullpath = "%s/%s" % (path, file)
                    stats(fullpath, sizemap)
            dumpstats(sizemap, path + "/ifdefstats.txt")
            sizemap = {}
    else:
        for fullpath in args:
            stats(fullpath, sizemap)
        ss = sorted([(v,k) for (k,v) in sizemap.items()])
        for s in ss:
            print "%d %s" % s

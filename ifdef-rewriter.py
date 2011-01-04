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

def serializeifdefs(xs, dst, opts):
    # we only tag the else/endif with the conditional if it
    # is further than 'threshold' lines away from the
    # if/ifdef/ifndef/elif that declared it.
    threshold = 4

    for x in xs:
        if isinstance(x, Ifdef):

            rewrite = True
            d = x.children[0].cond.expr
            if len(opts.enabled) > 0 or len(opts.disabled) > 0:
                found = False
                if d is None:
                    continue
                for n in opts.enabled + opts.disabled:
                    if d.find(n) >= 0:
                        found = True
                        break
                if found:
                    newcond = expr.parse(d)[0]
                    for n in opts.enabled:
                        newcond = substitutevalue(newcond, n, DefinedValue(1))
                    for n in opts.disabled:
                        newcond = substitutevalue(newcond, n, None)
                    newcond = evalexpr(newcond)
                    
                    if len(x.children) == 1:
                        if newcond is False or newcond is None:
                            # simple removal
                            continue
                        elif newcond is True:
                            # preserve contents of if, removing ifdefs
                            serializeifdefs(x.children[0].children, dst, opts)
                            continue
                        else:
                            # re-write expr!
                            x.children[0].cond.expr = newcond
                    if len(x.children) == 2 and x.children[1].cond == None:
                        if newcond is False or newcond is None:
                            # remove if, preserve else
                            serializeifdefs(x.children[1].children, dst, opts)
                            continue
                        elif newcond is True:
                            # preserve contents of if, remove ifdefs and else block
                            serializeifdefs(x.children[0].children, dst, opts)
                            continue
                        else:
                            # re-write expr!
                            x.children[0].cond.expr = newcond
                else:
                    rewrite = False
            
            if rewrite:
                prevbranch = None
                for b in x.children:
                    d = b.cond
                    if d is None:  
                        # This is an "else" branch
                        d = parseline(b.startline)
                        if opts.updatecomments:
                            d.comment = ""
                            if b.startpos - prevbranch.startpos > threshold:
                                e = printifdefexpr(prevbranch.cond).strip()
                                if prevbranch.cond.token == "ifndef":
                                    e = "!(%s)" % e
                                d.comment = "// " + e
        
                    dst.write(printifdef(d) + "\n")
                    serializeifdefs(b.children, dst, opts)
                    prevbranch = b
                if opts.updatecomments:
                    d = parseline(x.children[-1].endline)
                    d.comment = ""
                    if x.children[-1].endpos - x.children[-1].startpos > threshold:
                        c = x.children[-2].cond if x.children[-1].cond is None else x.children[-1].cond
                        e = printifdefexpr(c).strip()
                        if c.token == "ifndef":
                            e = "!(%s)" % e
                            d.comment = "// " + e
                    dst.write(printifdef(d) + "\n")
                else:
                    dst.write(x.children[-1].endline)
            else:
                for b in x.children:
                    dst.write(b.startline)
                    serializeifdefs(b.children, dst, opts)
                dst.write(x.children[-1].endline)
                
        elif isinstance(x, Branch):
            serializeifdefs(x.children, dst, opts)
        else:
            dst.write(x)

def tidyifdefs(file, opts):
    print "Tidying ifdefs in %s" % file
    root = parsefile(file)

    dst = tempfile.NamedTemporaryFile()

    serializeifdefs(root.children, dst, opts)

    # close the output file, then replace the
    # source with the cleaned file
    dst.flush()
    shutil.copyfile(dst.name, file)
    dst.close()

# ------------------------------------------------------------------------------
# Main Entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    optParser = optparse.OptionParser(usage='usage: %prog [ files ]\n\nIf no files are given then a recursive search for files ending\nwith c/cpp/mm/h is performed in the current directory.')
    optParser.set_defaults()
    optParser.add_option( '-e', '--always-enabled', dest="enabled", default = [], action="append")
    optParser.add_option( '-d', '--always-disabled', dest="disabled", default = [], action="append")
    optParser.add_option( '-u', '--update-comments', dest="updatecomments", default = False, action="store_false")     
    (opts, args) = optParser.parse_args()

    if len(args) == 0:
        for (path, dirs, files) in os.walk("."):
            for file in files:
                if any(file.endswith(x) for x in [".c", ".cpp", ".h", ".mm"]):
                    fullpath = "%s/%s" % (path, file)
                    tidyifdefs(fullpath, opts)
    else:
        for fullpath in args:
            tidyifdefs(fullpath, opts)
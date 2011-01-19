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
import optparse
from lepl import *

# ------------------------------------------------------------------------------
# Expression parser
# ------------------------------------------------------------------------------

class ASTNode(object):
    def __init__(self, pr):
        self.args = pr
class ExprNode(ASTNode): pass
class AndExpr(ExprNode): pass
class OrExpr(ExprNode):  pass
class NotExpr(ExprNode): pass
class ArithExpr(ExprNode): pass
class EqExpr(ArithExpr): pass
class AddExpr(ArithExpr): pass
class NotEqExpr(ArithExpr): pass
class GtEqExpr(ArithExpr): pass
class LtEqExpr(ArithExpr): pass
class GtExpr(ArithExpr): pass
class LtExpr(ArithExpr): pass
class DefinedValue(ASTNode): pass
class DefinedExpr(ASTNode): pass

with DroppedSpace():
    expr = Delayed()
    basicexpr = Delayed()
    bracketedexpr = Drop('(') & expr & Drop(')')
    number = Digit()[1:,...] >> int
    strlit  = SingleLineString(quote="'")
    ident  = Word(Letter() | '_', Letter() | '_' | Digit())
    definedexpr = ((Drop("defined") & ident) | (Drop("defined") & Drop("(") & ident & Drop(")"))) > DefinedExpr
    notexpr = Drop("!") & basicexpr > NotExpr
    basicexpr += definedexpr | ident | strlit | number | notexpr | bracketedexpr
    addexpr = basicexpr & Drop("+") & expr > AddExpr
    noteqexpr = basicexpr & Drop("!=") & expr > NotEqExpr
    eqexpr = basicexpr & Drop("==") & expr > EqExpr
    gteqexpr = basicexpr & Drop(">=") & expr > GtEqExpr
    lteqexpr = basicexpr & Drop("<=") & expr > LtEqExpr
    gtexpr = basicexpr & Drop(">") & expr > GtExpr
    ltexpr = basicexpr & Drop("<") & expr > LtExpr
    andexpr = basicexpr & Drop("&&") & expr > AndExpr
    orexpr = basicexpr & Drop("||") & expr > OrExpr
    expr += andexpr | orexpr | gteqexpr | lteqexpr | ltexpr | gtexpr | eqexpr | noteqexpr | addexpr | basicexpr

def printexpr(r, addBrackets=False):
    if isinstance(r, OrExpr):
        r = printexpr(r.args[0], not isinstance(r.args[0], OrExpr)) + " || " + printexpr(r.args[1], not isinstance(r.args[1], OrExpr))
    elif isinstance(r, AndExpr):
        r = printexpr(r.args[0], not isinstance(r.args[0], AndExpr)) + " && " + printexpr(r.args[1], not isinstance(r.args[1], AndExpr))
    elif isinstance(r, GtEqExpr):
        r = printexpr(r.args[0]) + " >= " + printexpr(r.args[1])
    elif isinstance(r, LtEqExpr):
        r = printexpr(r.args[0]) + " <= " + printexpr(r.args[1])
    elif isinstance(r, GtExpr):
        r = printexpr(r.args[0]) + " > " + printexpr(r.args[1])
    elif isinstance(r, LtExpr):
        r = printexpr(r.args[0]) + " < " + printexpr(r.args[1])
    elif isinstance(r, EqExpr):
        r = printexpr(r.args[0]) + " == " + printexpr(r.args[1])
    elif isinstance(r, NotEqExpr):
        r = printexpr(r.args[0]) + " != " + printexpr(r.args[1])
    elif isinstance(r, AddExpr):
        r = printexpr(r.args[0]) + " + " + printexpr(r.args[1])
    elif isinstance(r, DefinedExpr):
        return "defined(%s)" % r.args[0]
    elif isinstance(r, NotExpr):
        return "!%s" % printexpr(r.args[0], isinstance(r.args[0], ExprNode))
    else:
        return str(r)

    return str("(%s)" % r if addBrackets else r)

def printifdefexpr(ifdef):
    if isinstance(ifdef.expr, basestring) and ifdef.expr != "":
        ifdef.expr = expr.parse(ifdef.expr)[0]
    e = ifdef.expr
    if ifdef.token in ["if", "ifdef", "ifndef"]:
        if isinstance(ifdef.expr, DefinedExpr):
            e = ifdef.expr.args[0]
            ifdef.token = "ifdef"
        elif isinstance(ifdef.expr, NotExpr) and isinstance(ifdef.expr.args[0], DefinedExpr):
            e = ifdef.expr.args[0].args[0]
            ifdef.token = "ifndef"
    return printexpr(e)

def printifdef(ifdef):
    s = printifdefexpr(ifdef) + ifdef.comment
    if s != "" and not s.startswith(" "):
        s = " " + s
    return ifdef.hash + ifdef.token + s

def evalexpr(r):
    if isinstance(r, OrExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        if lhs is None or lhs == False:
            return rhs
        elif rhs is None or rhs == False:
            return lhs
        elif lhs == True or rhs == True:
            return True
        return OrExpr([lhs,rhs])
    elif isinstance(r, AndExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        if lhs is None or lhs is True:
            return rhs
        elif rhs is None or rhs is True:
            return lhs
        elif lhs is False or rhs is False:
            return False
        return AndExpr([lhs,rhs])
    elif isinstance(r, EqExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        return EqExpr([lhs,rhs])
    elif isinstance(r, NotEqExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        return NotEqExpr([lhs,rhs])
    elif isinstance(r, LtEqExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        return LtEqExpr([lhs,rhs])
    elif isinstance(r, GtEqExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        return GtEqExpr([lhs,rhs])
    elif isinstance(r, LtExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        return LtExpr([lhs,rhs])
    elif isinstance(r, GtExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        return GtExpr([lhs,rhs])
    elif isinstance(r, AddExpr):
        lhs = evalexpr(r.args[0])
        rhs = evalexpr(r.args[1])
        return AddExpr([lhs,rhs])
    elif isinstance(r, NotExpr):
        operand = evalexpr(r.args[0])
        if operand is False or operand is True:
            return not operand
        elif operand is None:
            return None
        return NotExpr([operand])
    elif isinstance(r, DefinedExpr):
        if isinstance(r.args[0], DefinedValue):
            return True
        elif r.args[0] is None:
            return False
    return r

def gettokens(e):
    if any(isinstance(e,t) for t in [ExprNode, ArithExpr]):
        tokens = []
        for arg in e.args:
            tokens += gettokens(arg)
        return tokens
    elif isinstance(e, DefinedExpr):
        return [e.args[0]]
    return [e]

def substitutevalue(r, name, value):
    if isinstance(r, OrExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return OrExpr([lhs,rhs])
    elif isinstance(r, AndExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return AndExpr([lhs,rhs])
    elif isinstance(r, GtEqExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return GtEqExpr([lhs,rhs])
    elif isinstance(r, LtEqExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return LtEqExpr([lhs,rhs])
    elif isinstance(r, GtExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return GtExpr([lhs,rhs])
    elif isinstance(r, LtExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return LtExpr([lhs,rhs])
    elif isinstance(r, EqExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return EqExpr([lhs,rhs])
    elif isinstance(r, NotEqExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return NotEqExpr([lhs,rhs])
    elif isinstance(r, AddExpr):
        lhs = substitutevalue(r.args[0], name, value)
        rhs = substitutevalue(r.args[1], name, value)
        return AddExpr([lhs,rhs])
    elif isinstance(r, DefinedExpr):
        return DefinedExpr([substitutevalue(r.args[0], name, value)])
    elif isinstance(r, NotExpr):
        return NotExpr([substitutevalue(r.args[0], name, value)])
    else:
        return value if str(r) == name else r

# ------------------------------------------------------------------------------
# Ifdef parser
# ------------------------------------------------------------------------------

class Branch:
    def __init__(self, pos, cond, startline):
        self.cond = cond
        self.startpos = pos
        self.endpos = 0
        self.startline = startline
        self.endline = None
        self.children = list()
        self.size = None
            
    def __repr__(self):
        return "branch (%d,%d) '%s'" % (self.startpos, self.endpos, self.cond)

class Ifdef:
    def __init__(self):
        self.children = list()
        self.size = None

class Directive:
    def __init__(self, hash, token, expr, comment):
        self.hash = hash
        self.token = token
        self.expr = expr
        self.comment = comment

# This regex contains three named groups, one for
# the whitespace around and including the hash,
# one for the preprocessor token and one for
# the actual conditional expression
regex = re.compile('(?P<hash>\s*#\s*)(?P<token>(ifdef)|(ifndef)|(if)|(elif)|(else)|(endif))(?P<contents>.*)')

def parseline(line):
    global regex
    bits = regex.match(line)
    if bits is None:
        return None
        
    bits = bits.groupdict()
    hash = bits['hash']
    token = bits['token']
    contents = bits['contents'].strip()
    
    comment = ""
    commentpos = contents.find("//")
    if commentpos >= 0:
        comment = " // " + contents[commentpos+2:].strip()
        contents = contents[0:commentpos].strip()

    removed = True
    while removed:
        commentpos = contents.find("/*")
        if commentpos >= 0:
            endpos = contents.find("*/")
            if endpos == len(contents)-2 and comment == "":
                comment = " // " + contents[commentpos+2:endpos].strip()
            elif endpos == -1:
                # multiline comment... ignore for now
                contents = (contents[0:commentpos]).strip()
            else:
                contents = (contents[0:commentpos] + contents[endpos+2:]).strip()

            removed = True
        else:
            removed = False

    return Directive(hash, token, contents, comment)

def parsefile(file):
    src = open(file, 'r')
    
    root = Ifdef()
    currentifdef = root
    currentifdef.children.append(Branch(0, None, None))
    currentstring = ""
    activeifdefs = [currentifdef]

    pos = 0
    for line in src:
        pos += 1

        #print "Parsing line %d in file %s" % (pos, file)

        dir = parseline(line)
        if dir is None:
            currentstring += line
            continue
        elif currentstring != "":
            if not isinstance(currentifdef.children[-1], Branch):
                print "Fail at line %d in file %s: '%s'" % (pos, file, currentifdef.children[-1])
            currentifdef.children[-1].children.append(currentstring)
            currentstring = ""
            
        if dir.token in ["if", "ifdef", "ifndef", "elif"]:
            if dir.token == "ifndef":
                dir.expr = "!defined(%s)" % dir.expr
            elif dir.token == "ifdef":
                dir.expr = "defined(%s)" % dir.expr
            
            if dir.token == "elif":
                if currentifdef is None:
                    print "Fail at line %d in file %s" % (pos, file)
                currentifdef.children[-1].endpos = pos
                currentifdef.children[-1].endline = line
            else:
                newifdef = Ifdef()
                currentifdef.children[-1].children.append(newifdef)
                currentifdef = newifdef
                activeifdefs.append(currentifdef)
            currentifdef.children.append(Branch(pos, dir, line))
        elif dir.token == "else":
            if currentifdef is None:
                    print "Fail at line %d in file %s" % (pos, file)
            currentifdef.children[-1].endpos = pos
            currentifdef.children[-1].endline = line
            currentifdef.children.append(Branch(pos, None, line))
        elif dir.token == "endif":
            if currentifdef is None:
                print "Fail at line %d in file %s" % (pos, file)
            currentifdef.children[-1].endpos = pos
            currentifdef.children[-1].endline = line
            activeifdefs.pop()
            currentifdef = activeifdefs[-1]
    
    if currentstring != "":
        currentifdef.children[-1].children.append(currentstring)
            
    src.close()
    return root

def calculatesizes(x):
    if isinstance(x, Ifdef) or isinstance(x, Branch):
        x.size = 0
        for c in x.children:
            x.size += calculatesizes(c)
        return x.size
    else:
        return len(x)
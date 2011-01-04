
# The contents of this file are subject to the Mozilla Public License
# (MPL) Version 1.1 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License
# at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
# the License for the specific language governing rights and
# limitations under the License.
#
# The Original Code is LEPL (http://www.acooke.org/lepl)
# The Initial Developer of the Original Code is Andrew Cooke.
# Portions created by the Initial Developer are Copyright (C) 2009-2010
# Andrew Cooke (andrew@acooke.org). All Rights Reserved.
#
# Alternatively, the contents of this file may be used under the terms
# of the LGPL license (the GNU Lesser General Public License,
# http://www.gnu.org/licenses/lgpl.html), in which case the provisions
# of the LGPL License are applicable instead of those above.
#
# If you wish to allow use of your version of this file only under the
# terms of the LGPL License and not to allow others to use your version
# of this file under the MPL, indicate your decision by deleting the
# provisions above and replace them with the notice and other provisions
# required by the LGPL License.  If you do not delete the provisions
# above, a recipient may use your version of this file under either the
# MPL or the LGPL License.

'''
Tests related to a bug when Word() is specified inside Token() with
line-aware parsing.
'''

from unittest import TestCase

from lepl import *
from lepl.offside.regexp import LineAwareAlphabet, make_hide_sol_eol_parser
from lepl.regexp.str import make_str_parser

class WordBugTest(TestCase):
    
    def test_simple(self):
        with DroppedSpace():
            line = (Word()[:] & Drop('\n')) > list
            lines = line[:]
        result = lines.parse('abc de f\n pqr\n')
        assert result == [['abc', 'de', 'f'], ['pqr']], result

    def test_tokens(self):
        word = Token(Word())
        newline = ~Token('\n')
        line = (word[:] & newline) > list
        lines = line[:]
        result = lines.parse('abc de f\n pqr\n')
        assert result == [['abc', 'de', 'f'], ['pqr']], result
        
    def test_line_any(self):
        word = Token('[a-z]+')
        line = Line(word[:]) > list
        lines = line[:]
        lines.config.default_line_aware()
        result = lines.parse('abc de f\n pqr\n')
        assert result == [['abc', 'de', 'f'], ['pqr']], result

    def test_line_word(self):
        word = Token(Word())
        line = Line(word[:]) > list
        lines = line[:]
        lines.config.default_line_aware()
        result = lines.parse('abc de f\n pqr\n')
        assert result == [['abc', 'de', 'f'], ['pqr']], result

    def test_line_notnewline(self):
        word = Token('[^\n ]+')
        line = Line(word[:]) > list
        lines = line[:]
        lines.config.default_line_aware()
        result = lines.parse('abc de f\n pqr\n')
        assert result == [['abc', 'de', 'f'], ['pqr']], result
        
    def test_line_word_explicit(self):
        word = Token(Word())
        line = (~LineAwareSol() & word[:] & ~LineAwareEol()) > list
        lines = line[:]
        lines.config.default_line_aware()
        result = lines.parse('abc de f\n pqr\n')
        assert result == [['abc', 'de', 'f'], ['pqr']], result

    def test_line_word_explicit_no_tokens(self):
        with DroppedSpace():
            words = Word()[:]
            newline = ~Any('\n')
            line = (~SOL() & words & newline & ~EOL()) > list
            lines = line[:]
        lines.config.default_line_aware()
        result = lines.parse('abc de f\n pqr\n')
        assert result == [['abc', 'de', 'f'], ['pqr']], result

    def test_parse(self):
        unicode = UnicodeAlphabet()
        assert unicode.parse(r'[\\x00-\\x08\\x0e-\\x1f!-\\uffff](?:[\\x00-\\x08\\x0e-\\x1f!-\\uffff])*')
        assert unicode.parse('[\\x00-\\x08\\x0e-\\x1f!-\\uffff](?:[\\x00-\\x08\\x0e-\\x1f!-\\uffff])*')
        line_aware = LineAwareAlphabet(unicode, make_hide_sol_eol_parser)
        assert line_aware.parse(r'[(*SOL)-\\x08\\x0e-\\x1f!-(*EOL)](?:[(*SOL)-\\x08\\x0e-\\x1f!-(*EOL)])*')
        assert line_aware.parse('[(*SOL)-\\x08\\x0e-\\x1f!-(*EOL)](?:[(*SOL)-\\x08\\x0e-\\x1f!-(*EOL)])*')
        line_aware = LineAwareAlphabet(unicode, make_str_parser)
        assert line_aware.parse(r'[(*SOL)-\\x08\\x0e-\\x1f!-(*EOL)](?:[(*SOL)-\\x08\\x0e-\\x1f!-(*EOL)])*')
        assert line_aware.parse('[(*SOL)-\\x08\\x0e-\\x1f!-(*EOL)](?:[(*SOL)-\\x08\\x0e-\\x1f!-(*EOL)])*')
        
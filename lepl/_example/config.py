
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
An example config file format using blocks with three levels.
'''

from string import ascii_letters
from lepl._example.support import Example
from lepl import *

def config_parser():
    word        = Token(Any(ascii_letters)[1:, ...])
    key_value   = (word & ~Token(':') & word) > tuple
    subsection  = BLine(word) & (Block(BLine(key_value)[1:] > dict)) > list
    section     = BLine(word) & Block(subsection[1:]) > list
    config_file = (section | ~Line(Empty()))[:] > list
    
    config_file.config.default_line_aware(block_policy=rightmost)
    return config_file.get_parse()

class ConfigExample(Example):
    
    def test_config(self):
        parser = config_parser()
        parsed = parser('''
one
   a
      foo: bar
      baz: poop
   b
      snozzle: berry

two
   c
      apple: orange
''')[0]
        self.examples([(lambda: parsed,
                        "[['one', ['a', {'foo': 'bar', 'baz': 'poop'}], ['b', {'snozzle': 'berry'}]], ['two', ['c', {'apple': 'orange'}]]]")])

##
# pitweb - Web interface for git repository written in python
# ------------------------------------------------------------
# Copyright (c)2010 Daniel Fiser <danfis@danfis.cz>
#
#
#  This file is part of pitweb.
#
#  pitweb is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation; either version 3 of
#  the License, or (at your option) any later version.
#
#  pitweb is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

from mod_python import apache, util

class ModPythonOutput(object):
    """ Class able to produce output using mod_python's request object """

    def __init__(self, req):
        self._req = req

    def _esc(self, s):
        """ Replaces special characters by HTML escape sequences """
        s = s.replace('<', '&lt;')
        s = s.replace('>', '&gt;')
        s = s.replace('\n', '<br />')
        return s

    def write(self, s):
        self._req.write(s)

    def setContentType(self, type):
        self._req.content_type = type

    def setFilename(self, filename):
        self._req.headers_out['Content-disposition'] = ' attachment; filename="{0}"'.format(filename)

    def run(self):
        self.write("This method should be overloaded")
        return apache.OK


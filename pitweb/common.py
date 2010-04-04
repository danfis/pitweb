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


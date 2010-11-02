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
import os

from project import Project
import common


class ProjectListBase(common.ModPythonOutput):
    def __init__(self, req, projects = [], basepath = '/'):
        super(ProjectListBase, self).__init__(req)

        # set default content-type to text/html
        self.setContentType('text/html')

        self._projects = projects
        self._basepath = basepath


    def _uri(self):
        uri = self._req.uri.split('/')
        uri = filter(lambda x: len(x) > 0, uri)
        return uri

    def run(self):
        uri = self._uri()
        if len(uri) > 0:
            prj_name = uri[-1]
            for p in self._projects:
                if prj_name == p.projectName():
                    return p.run()

        self.write(self.tpl(self._fProjectList()))
        return apache.OK

    def _fProjectList(self):
        html = ''
        html += '<table class="projects">'

        html += '<tr class="header">'
        html += '<td>Project</td>'
        html += '<td>Owner</td>'
        html += '<td>Description</td>'
        html += '<td>Last change</td>'
        html += '</tr>'

        for prj in self._projects:
            name        = self._esc(prj.projectName())
            owner       = self._esc(prj.owner())
            desc        = self._esc(prj.description())
            last_change = self._esc(prj.lastChange())

            html += '<tr>'
            html += '<td><a href="{0}{1}">{1}</a></td>'.format(self._basepath, name)
            html += '<td>{0}</td>'.format(owner)
            html += '<td>{0}</td>'.format(desc)
            html += '<td>{0}</td>'.format(last_change)
            html += '</tr>'

        html += '</table>'
        return html
        
    def tpl(self, content):
        html = '''
<html>
    <head>
        <style type="text/css">
        {css}
        </style>

        <title>pitweb</title>
    </head>

    <body>
        <div class="content">
            {content}
        </div>
    </body>
</html>
'''.format(css = self.css(), content = content)
        return html


    def css(self):
        h = '''
html * { font-family: sans; font-size: 13px; }
body { padding: 5px; }

table tr td { vertical-align: top; padding-left: 4px; padding-right: 4px; }
table tr.header { font-weight: bold; font-size: 15px; }
table tr.title td { padding: 3px; padding-left: 7px; font-size: 16px; font-weight: bold; background-color: #edece6; }
table tr:hover { background-color: #fbfaf7; }

a { color: #0000cc; text-decoration: none; } 
a:hover { text-decoration: underline; }
a.comment { font-weight: bold; color: #666666; }
a.tag { display: block-inline; background-color: #ffffaa; border: 1px solid #f1ee00; color: black;
        margin-left: 2px; margin-right: 2px;
        padding-left: 4px; padding-right: 4px; padding-top: 1px; padding-bottom: 1px; }
a.branch { display: block-inline; background-color: #88ff88; border: 1px solid #39ba39; color: black;
           margin-left: 2px; margin-right: 2px;
           padding-left: 4px; padding-right: 4px; padding-top: 1px; padding-bottom: 1px; }
a.remote { display: block-inline; background-color: #AAAAFF; border: 1px solid #8888ff; color: black;
           margin-left: 2px; margin-right: 2px;
           padding-left: 4px; padding-right: 4px; padding-top: 1px; padding-bottom: 1px; }
a.blob { color: black; }
a.menu { font-family: sans !important; font-size: 11px !important; }
        '''
        return h


class ProjectListDir(ProjectListBase):
    """ List of projects is based on one directory.
        All subdirectories which contain config file (piteweb.py) are taken
        as project.
    """

    def __init__(self, req, dir, basepath = '/'):
        projects = self._projects(req, dir, basepath)
        super(ProjectListDir, self).__init__(req, projects, basepath = basepath)

    def _projects(self, req, parent_dir, basepath):
        projects = []

        dirs = sorted(os.listdir(parent_dir), key=str.lower)
        for dir in dirs:
            path   = os.path.join(parent_dir, dir)
            config = os.path.join(path, 'pitweb.py')
            if os.path.isdir(path) and os.path.isfile(config):
                projects.append(Project(req, path, basepath))

        return projects

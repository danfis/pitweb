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
import string
import re
import math
import mimetypes
import os
import imp
import hashlib

pygments = False
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename
    from pygments.formatters import HtmlFormatter
    pygments = True
except:
    pass

import common
import git


class ProjectBase(common.ModPythonOutput):
    """ HTML interface for project specified by its directory. """

    def __init__(self, req, dir):
        super(ProjectBase, self).__init__(req)

        self._dir = dir

        self._git = git.Git(dir)

        self._errors = []
        self._status = apache.OK

        self._config()
        self._params()

    def _config(self):
        config = None

        # Load configuration from file
        if os.path.exists(os.path.join(self._dir, 'pitweb.py')):
            file = pathname = desc = None
            try:
                file, pathname, desc = imp.find_module('pitweb', [self._dir]) 
            except ImportError:
                pass

            try:
                if file and pathname and desc:
                    f = open(pathname, 'r')
                    hash = hashlib.sha256(pathname + f.read())
                    f.close()

                    name = 'config-' + hash.hexdigest()

                    config = imp.load_module(name, file, pathname, desc)
            except Exception as e:
                msg = "Can't load configuration file: "
                msg += str(e)
                self._errors.append(msg)

        self._setProjectName(config)
        self._commits_per_page = self._configParam(config, 'commits_per_page', 50)
        self._commits_in_summary = self._configParam(config, 'commits_in_summary', 15)
        self._description = self._configParam(config, 'description', None)
        self._owner = self._configParam(config, 'owner', None)
        self._urls = self._configParam(config, 'urls', [])
        self._homepage = self._configParam(config, 'homepage', None)
        self._one_line_comment_max_len = self._configParam(config, 'one_line_comment_max_len', 50)
        self._setSnapshots(config)

    def _configParam(self, config, name, default):
        if config and hasattr(config, name):
            return getattr(config, name)
        return default

    def _setProjectName(self, config):
        name = self._configParam(config, 'project_name', None)
        if name:
            self._project_name = name
            return

        name = ''

        p = self._dir.split('/')
        p = filter(lambda x: len(x) > 0, p)
        if len(p) > 0:
            name = p[-1]
            if len(name) > 4 and name[-4:] == '.git':
                name = name[:-4]

        self._project_name = name

    def _setSnapshots(self, config):
        snapshots = self._configParam(config, 'snapshots', ['tgz', 'tbz2'])

        # filter invalid values
        snapshots = filter(lambda x: x in ['tgz', 'tbz2', 'txz', 'zip'], snapshots)

        self._snapshots = snapshots

        self._snapshots_map = { 'tgz'  : '.tar.gz',
                                'tbz2' : '.tar.bz2',
                                'txz'  : '.tar.xz',
                                'zip'  : '.zip' }

    def _setStatus(self, s):
        self._status = s

    def _params(self):
        args = self._parseArgs()
        self._a       = args.get('a', 'summary')
        self._id      = args.get('id', 'HEAD')
        self._id2     = args.get('id2', None)
        self._treeid  = args.get('treeid', self._id)
        self._blobid  = args.get('blobid', 'HEAD')
        self._filename = args.get('filename', '')
        self._showmsg = args.get('showmsg', '0')
        if self._showmsg == '0':
            self._showmsg = False
        else:
            self._showmsg = True

        self._page    = int(args.get('page', '1'))
        self._path    = args.get('path', '')
        self._format  = args.get('format', 'tgz')

    def _parseArgs(self):
        args = {}

        if not self._req.args:
            return args

        strargs = self._req.args
        if strargs[0] == '?':
            strargs = strargs[1:]

        hunks = strargs.split(';')
        for hunk in hunks:
            s = hunk.split('=', 1)
            if len(s) == 2:
                args[s[0]] = s[1]

        return args

    def projectName(self):
        return self._project_name

    def owner(self, default = ''):
        if self._owner:
            return self._owner
        return default

    def description(self, default = ''):
        if self._description:
            return self._description
        return default

    def lastChange(self, default = ''):
        commits = self._git.revList(None, all = True, max_count = 1)
        if len(commits) > 0:
            date   = commits[0].committer.date
            date   = date.format('%Y-%m-%d %H:%M:%S')
            return date
        return ''


    def run(self):
        self._section = self._a
        if self._a == 'log':
            self.log(id = self._id, showmsg = self._showmsg, page = self._page)
        elif self._a == 'refs':
            self.refs()
        elif self._a == 'summary':
            self.summary()
        elif self._a == 'commit':
            self.commit(id = self._id)
        elif self._a == 'diff':
            self.diff(id = self._id, id2 = self._id2)
        elif self._a == 'patch':
            self.patch(id = self._id, id2 = self._id2)
        elif self._a == 'tree':
            self.tree(id = self._id, treeid = self._treeid, path = self._path)
        elif self._a == 'blob':
            self._section = 'tree'
            self.blob(id = self._id, blobid = self._blobid, treeid = self._treeid, \
                      path = self._path, filename = self._filename)
        elif self._a == 'blob-raw':
            self.blobRaw(blobid = self._blobid, filename = self._filename)
        elif self._a == 'snapshot':
            self.snapshot(id = self._id, format = self._format)
        elif self._a == 'pull':
            self.pull(path = self._path)

        return self._status


class Project(ProjectBase):
    def __init__(self, req, dir, projects = None):
        super(Project, self).__init__(req, dir)

        self._projects = projects

    def _fileOut(self, data, filename):
        type = mimetypes.guess_type(filename)
        mime_type = type[0]
        if not mime_type:
            mime_type = 'application/octet-stream'

        self.setContentType(mime_type)
        self.setFilename(filename)
        self.write(data)


    def anchor(self, html, cls, v):
        href = '?'
        for k in v:
            href += '{k}={v};'.format(k = k, v = v[k])

        app = ''
        if cls and len(cls) > 0:
            app += ' class="{0}"'.format(cls)

        return '<a href="{href}"{app}>{html}</a>'.format(html = html, href = href, app = app)


    def anchorLog(self, html, id, showmsg, page, cls = ''):
        if showmsg:
            showmsg = '1'
        else:
            showmsg = '0'
        return self.anchor(html, cls = cls, v = { 'a' : 'log', 'id' : id, 'showmsg' : showmsg, 'page' : page })

    def anchorCommit(self, html, id, cls = ''):
        return self.anchor(html, v = { 'a' : 'commit', 'id' : id }, cls = cls)


    def log(self, id = 'HEAD', showmsg = False, page = 1):
        max_count = self._commits_per_page * page;
        commits = self._git.revList(id, max_count = max_count)
        commits = commits[self._commits_per_page * (page - 1):]

        tags, heads, remotes = self._git.refs()
        commits = self._git.commitsSetRefs(commits, tags, heads, remotes)

        html = ''

        if not showmsg:
            expand = self.anchorLog('Expand', id, not showmsg, page)
        else:
            expand = self.anchorLog('Collapse', id, not showmsg, page)

        # Navigation
        nav = ''
        nav += '<div class="log_nav">'
        if page <= 1:
            nav += '<span>prev</span>'
        else:
            nav += self.anchorLog('prev', id, showmsg, page - 1)

        nav += '<span class="sep">|</span>'

        nav += self.anchorLog('next', id, showmsg, page + 1)
        nav += '</div>'

        html += nav
        html += self._fLog(commits, longcomment = True, id = id, showmsg = showmsg, page = page)
        html += nav

        self.write(self.tpl(html))


    def refs(self):
        tags, heads, remotes = self._git.refs()

        html = ''

        # heads
        if len(heads) > 0:
            html += self._fHeads(heads)
            html += '<br />'

        # tags
        if len(tags) > 0:
            html += self._fTags(tags)
            html += '<br />'

        # remotes
        if len(remotes) > 0:
            html += self._fRemotes(remotes)
            html += '<br />'

        self.write(self.tpl(html))

    def summary(self):
        tags, heads, remotes = self._git.refs()
        commits = self._git.revList('HEAD', max_count = self._commits_in_summary)
        commits = self._git.commitsSetRefs(commits, tags, heads, remotes)

        html = ''

        html +=  self._fSummaryInfo()
        html += '<br />'

        if len(heads) > 0:
            html += self._fHeads(heads)
            html += '<br />'

        if len(tags) > 0:
            html += self._fTags(tags, 10)
            html += '<br />'

        html += self._fLog(commits)

        self.write(self.tpl(html))


    def commit(self, id):
        commit = self._git.commit(id)
        parent = None
        if len(commit.parents) == 1:
            parent = commit.parents[0]
        diff_trees = self._git.diffTree(id, parent, patch = True)

        html = ''
        if commit:
            html += self._fCommitInfo(commit)
            html += '<br />'
            html += self._fDiffTree(diff_trees)

        self.write(self.tpl(html))

    def patch(self, id, id2):
        patch = self._git.formatPatch(id, id2)
        self.setContentType('text/plain')
        self.write(patch)

    def diff(self, id, id2):
        diff_trees = self._git.diffTree(id, id2, patch = True)

        html = ''
        html += self._fDiffTree(diff_trees)

        self.write(self.tpl(html))


    def tree(self, id, treeid, path = ''):
        html = ''

        objs = self._git.tree(id = treeid)

        spath = path.split('/')
        spath = filter(lambda x: len(x) > 0, spath)
        for p in spath:
            found = False
            for obj in objs:
                if type(obj) is git.GitTree \
                   and obj.name == p:
                    objs = self._git.tree(id = obj.id)
                    found = True
                    break

            if not found:
                break

        html += self._fTreePath(path, treeid)
        html += '<br />'

        html += '''<table class="tree">
        <tr class="header">
            <td>Mode</td>
            <td>Size</td>
            <td>Name</td>
            <td></td>
        </tr>
        '''

        if len(spath) > 0:
            v = { 'a'      : 'tree',
                  'id'     : self._id,
                  'treeid' : treeid,
                  'path'   : string.join(spath[:-1], '/') }
            cls = 'tree'
            aname = self.anchor('..', v = v, cls = cls)

            html += '<tr>'
            html += '<td>drwxr-xr-x</td>'
            html += '<td></td>'
            html += '<td>' + aname + '</td>'
            html += '<td>' + '</td>'
            html += '</tr>'
            

        for obj in objs:
            if type(obj) is git.GitTree:
                v = { 'a'      : 'tree',
                      'id'     : self._id,
                      'treeid' : treeid,
                      'path'   : path + '/' + obj.name }
                cls = 'tree'

                menu = self.anchor('tree', v = v, cls = 'menu')
            else:
                v = { 'a'      : 'blob',
                      'id'     : self._id,
                      'blobid' : obj.id,
                      'treeid' : treeid,
                      'path'   : path,
                      'filename' : obj.name }
                cls = 'blob'

                vraw = { 'a'        : 'blob-raw',
                         'filename' : obj.name,
                         'blobid'   : obj.id }
                menu = self.anchor('blob', v = v, cls = 'menu')
                menu += '|'
                menu += self.anchor('raw', v = vraw, cls = 'menu')

            aname = self.anchor(obj.name, v = v, cls = cls)

            html += '<tr>'
            html += '<td>' + obj.modeStr(obj.mode_oct) + '</td>'
            html += '<td>' + obj.size + '</td>'
            html += '<td>' + aname + '</td>'
            html += '<td>' + menu + '</td>'
            html += '</tr>'
        html += '</table>'

        self.write(self.tpl(html))


    def blob(self, id, blobid, treeid, path = '', filename = ''):
        html = ''

        blob = self._git.blob(blobid)

        html += self._fTreePath(path, treeid, filename, blobid)
        html += '<br />'
        html += self._fBlob(blob, filename)

        self.write(self.tpl(html))


    def blobRaw(self, blobid, filename):
        blob = self._git.blob(blobid)
        return self._fileOut(blob.data, filename)

    def snapshot(self, id, format):
        (data, filename) = self._git.archive(id, self._project_name, format)
        return self._fileOut(data, filename)

    def pull(self, path):
        if path.find('..') >= 0:
            self._setStatus(apache.HTTP_NOT_FOUND)
            return

        fn = self._dir + '/' + path
        try:
            f = open(fn, 'r')
            c = f.read()
            self.write(c)
        except:
            self._setStatus(apache.HTTP_NOT_FOUND)

    def _fTreePath(self, path, treeid, blobname = None, blobid = None):
        html = ''

        spath = path.split('/')
        spath = filter(lambda x: len(x) > 0, spath)
        if len(spath) > 0 or blobname:
            html += '<div>'

            html += 'path: '
            html += self.anchor('root', v = { 'a' : 'tree', 'id' : self._id, 'treeid' : treeid }, cls = '')

            for i in range(0, len(spath)):
                v = { 'a' : 'tree',
                      'id' : self._id,
                      'treeid' : treeid,
                      'path'   : string.join(spath[0:i+1], '/') }
                html += ' / '
                html += self.anchor(spath[i], v = v, cls = '')

            if blobname:
                v = { 'a' : 'blob',
                      'id' : self._id,
                      'treeid' : treeid,
                      'path'   : path,
                      'blobid' : blobid,
                      'filename' : blobname }
                html += ' / '
                html += self.anchor(blobname, v = v, cls = 'blob')

            html += '</div>'

        return html

    def _fBlob(self, blob, filename = ''):
        html = ''

        data = blob.data

        lexer     = None
        formatter = None
        if pygments and len(filename) > 0:
            try:
                lexer     = get_lexer_for_filename(filename)
                formatter = HtmlFormatter(nowrap = True, noclasses = True, style = 'trac')
                data = highlight(data, lexer, formatter)
            except:
                lexer     = None
                formatter = None

        lines = data.split('\n')
        if len(lines[-1]) == 0:
            lines = lines[:-1]

        digits = 0
        if len(lines) > 0:
            digits = int(math.ceil(math.log(len(lines), 10)))

        linepat = '<div class="blob-line">'
        linepat += '<span class="blob-linenum"> {{0: >{0}d}} </span>'
        linepat += '<span class="blob-line"> {{1}}</span>'
        linepat += '</div>'
        linepat = linepat.format(digits)

        if not lexer:
            lines = map(lambda x: self._esc(x), lines)

        html += '<div class="blob">'
        for i in range(0, len(lines)):
            line = lines[i]
            html += linepat.format(i + 1, line)
        html += '</div>'

        return html


    def _fSummaryInfo(self):
        h = '<table class="summary-info">'

        # description
        if self._description:
            h += '<tr>'
            h += '<td>Description</td>'
            h += '<td>' + self._esc(self._description) + '</td>'
            h += '</tr>'

        # owner
        if self._owner:
            h += '<tr>'
            h += '<td>Owner</td>'
            h += '<td>' + self._esc(self._owner) + '</td>'
            h += '</tr>'

        # last change
        h += '<tr>'
        h += '<td>Last change</td>'
        h += '<td>' + self.lastChange() + '</td>'
        h += '</tr>'

        # homepage
        if self._homepage:
            a = '<a href="{0}">{1}</a>'.format(self._homepage, self._esc(self._homepage))
            h += '<tr>'
            h += '<td>Homepage</td>'
            h += '<td>' + a + '</td>'
            h += '</tr>'

        # urls
        if len(self._urls) > 0:
            h += '<tr>'
            h += '<td>URL</td>'
            h += '<td>' + self._esc(self._urls[0]) + '</td>'
            h += '</tr>'

            for u in self._urls[1:]:
                h += '<tr>'
                h += '<td></td>'
                h += '<td>' + self._esc(u) + '</td>'
                h += '</tr>'

        h += '</table>'

        return h


    def _fHeads(self, heads):
        html = '''
        <table class="refs">
        <tr class="header">
            <td>Head</td>
            <td>Commit message</td>
            <td>Author</td>
            <td>Age</td>
            <td></td>
        </tr>
        '''
        for h in heads:
            comm = h.commit()

            line = self._esc(comm.commentFirstLine())
            if len(line) > self._one_line_comment_max_len:
                line = line[:self._one_line_comment_max_len] + '...'
            line = line.replace('{', '{{').replace('}', '}}')

            v = { 'a'  : 'log',
                  'id' : comm.id }
            commanchor = self.anchor(line, v = v, cls = 'comment')

            v = { 'a' : 'log',
                  'id' : h.id }
            nameanchor = self.anchor(self._esc(h.name), v = v, cls = 'head')

            html += '<tr>'
            html += '<td>' + nameanchor + '</td>'
            html += '<td>' + commanchor + '</td>'
            html += '<td><i>' + comm.author.name() + '</i></td>'
            html += '<td title="' + comm.author.date.format('%Y-%m-%d %H:%M:%S') +'">'
            html +=   comm.author.date.format('%Y-%m-%d')
            html += '</td>'
            html += '<td>' + '</td>'
            html += '</tr>'

        html += '</table>'
        return html

    def _fTags(self, tags, max = None):
        html = '''
        <table class="refs">
        <tr class="header">
            <td>Tag</td>
            <td>Message</td>
            <td>Tagger</td>
            <td>Age</td>
            <td></td>
        </tr>
        '''

        if not max:
            max = len(tags)

        for t in tags[:max]:
            v = { 'a' : 'log',
                  'id' : t.id }
            nameanchor = self.anchor(self._esc(t.name), v = v, cls = 'ref_tag')

            html += '<tr>'
            html += '<td>' + nameanchor + '</td>'
            html += '<td>' + self._esc(t.msg) + '</td>'
            html += '<td><i>' + self._esc(t.tagger.name()) + '</i></td>'
            html += '<td title="' + t.tagger.date.format('%Y-%m-%d %H:%M:%S') + '">'
            html +=   t.tagger.date.format('%Y-%m-%d')
            html += '</td>'

            html += '<td>'
            html += self._fMenuLinks(t.name, t.id)
            html += '</td>'
            html += '</tr>'

        if len(tags) > max:
            html += '<tr><td colspan="6">'
            html += self.anchor('[ ... ]', v = { 'a' : 'refs' }, cls = 'ref_tag')
            html += '</td></tr>'
        html += '</table>'
        html += '<br />'
        return html

    def _fRemotes(self, remotes):
        html = '''
        <table class="refs">
        <tr class="header">
            <td>Remote head</td>
            <td>Commit message</td>
            <td>Author</td>
            <td>Age</td>
            <td></td>
        </tr>
        '''
        for r in remotes:
            comm = r.commit()

            line = self._esc(comm.commentFirstLine())
            if len(line) > self._one_line_comment_max_len:
                line = line[:self._one_line_comment_max_len] + '...'
            line = line.replace('{', '{{').replace('}', '}}')

            v = { 'a'  : 'log',
                  'id' : comm.id }
            commanchor = self.anchor(line, v = v, cls = 'comment')

            v = { 'a' : 'log',
                  'id' : r.id }
            nameanchor = self.anchor(self._esc(r.name), v = v, cls = 'ref_remote')

            html += '<tr>'
            html += '<td>' + nameanchor + '</td>'
            html += '<td>' + commanchor + '</td>'
            html += '<td><i>' + self._esc(comm.author.name()) + '</i></td>'
            html += '<td title="' + comm.author.date.format('%Y-%m-%d %H:%M:%S') + '">'
            html +=   comm.author.date.format('%Y-%m-%d')
            html += '</td>'
            html += '<td>' + '</td>'
            html += '</tr>'

        html += '</table>'
        return html

    def _fSnapshotLinks(self, id):
        html = ''

        anchors = []
        for s in self._snapshots:
            v = { 'a'      : 'snapshot',
                  'id'     : id,
                  'format' : s }
            anchors.append(self.anchor(self._snapshots_map[s], v = v, cls = 'menu'))

        html += string.join(anchors, ',&nbsp;')

        return html

    def _fMenuLinks(self, id, treeid = None):
        html = ''

        html += self.anchor('commit', v = { 'a' : 'commit', 'id' : id }, cls = 'menu') 

        html += '&nbsp;|&nbsp;'
        html += self.anchor('diff', v = { 'a' : 'diff', 'id' : id }, cls = 'menu')

        if treeid:
            html += '&nbsp;|&nbsp;'
            v = { 'a'      : 'tree',
                  'id'     : id,
                  'treeid' : treeid }
            html += self.anchor('tree', v = v, cls = 'menu')

        html += '&nbsp;|&nbsp;'
        html += self._fSnapshotLinks(id)

        return html


    def _fLog(self, commits, id = 'HEAD', longcomment = False, showmsg = False, page = 1):
        html = ''

        expand = ''
        if longcomment:
            if not showmsg:
                expand = self.anchorLog('Expand', id, not showmsg, page)
            else:
                expand = self.anchorLog('Collapse', id, not showmsg, page)
            expand = ' (' + expand + ')'

        html += '''
<table class="log">
        <tr class="log_header">
            <td>Age</td>
            <td>Author</td>
            <td>Commit message{0}</td>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
        </tr>
        '''.format(expand)

        for commit in commits:
            h = '''
        <tr>
            <td title="{date_full}">{date}</td>
            <td><i>{author}</i></td>
            <td>'''

            line = self._esc(commit.commentFirstLine())
            if not showmsg and len(line) > self._one_line_comment_max_len:
                line = line[:self._one_line_comment_max_len] + '...'
            line = line.replace('{', '{{')
            line = line.replace('}', '}}')

            h += self.anchorCommit(line, commit.id, cls = 'comment')

            for b in commit.heads:
                h += self.anchorLog(self._esc(b.name), b.id, showmsg, 1, cls = "branch")

            for t in commit.tags:
                h += self.anchorLog(self._esc(t.name), t.id, showmsg, 1, cls = "tag")

            for r in commit.remotes:
                h += self.anchorLog('remotes/' + self._esc(r.name), r.id, showmsg, 1, cls = "remote")

            h += '{longcomment}</td>'
            h += '<td>'
            h += self._fMenuLinks(commit.id, commit.tree)
            h += '</td>'
            h += '</tr>'

            longcomment = ''
            if showmsg:
                longcomment  = '<div class="commit-msg"><br />'
                longcomment += self._esc(commit.commentRestLines().strip(' \n\t'))
                longcomment += '</div><br />'

            html += h.format(id          = commit.id,
                             author      = self._esc(commit.author.name()),
                             date_full   =
                             commit.author.date.format('%Y-%m-%d %H:%M:%S'),
                             date        = commit.author.date.format('%Y-%m-%d'),
                             longcomment = longcomment,
                             tree        = commit.tree)
        html += '</table>'

        return html


    def _fCommitInfoPerson(self, title, person):
        p = self._esc(person.person)
        date = person.date.format('%Y-%m-%d %H:%M:%S')
        date += ' (' + person.date.local_tz + ')'
        html = '''
        <tr>
            <td>{title}</td>
            <td><i>{p}</i></td>
            <td>{date}</td>
        </tr>
        '''.format(title = title, p = p, date = date)
        return html

    def _fCommitInfo(self, commit):
        html = ''
        html += '<table class="commit-info">'

        # author, committer
        html += self._fCommitInfoPerson('author', commit.author)
        html += self._fCommitInfoPerson('committer', commit.committer)

        # commit
        comm = self.anchorCommit(commit.id, commit.id)
        comm += '&nbsp;&nbsp;('
        comm += self.anchor('patch', v = { 'a' : 'patch', 'id' : commit.id }, cls = "menu")
        comm += ')'
        html += '''
        <tr>
            <td>commit</td>
            <td colspan="2">{0}</td>
        </tr>'''.format(comm)

        # tree
        v = { 'a'      : 'tree',
              'id'     : commit.id,
              'treeid' : commit.tree }
        tree = self.anchor(commit.tree, v = v, cls = "")
        tree += '&nbsp;&nbsp;(' + self._fSnapshotLinks(commit.id) + ')'
        html += '''
        <tr>
            <td>tree</td>
            <td colspan="2">{0}</td>
        </tr>'''.format(tree)

        # parents
        for parent in commit.parents:
            par = self.anchorCommit(parent, parent)
            par += '&nbsp;&nbsp;('
            par += self.anchor('diff', v = { 'a' : 'diff', 'id' : parent, 'id2' : commit.id }, cls = "menu")
            par += ')'
            par += '&nbsp;&nbsp;('
            par += self.anchor('patch', v = { 'a' : 'patch', 'id' : parent, 'id2' : commit.id }, cls = "menu")
            par += ')'
            html += '''
            <tr>
                <td>parent</td>
                <td colspan="2">{0}</td>
            </tr>
            '''.format(par)

        html += '</table>'

        # comment
        short = self._esc(commit.commentFirstLine())
        rest  = self._esc(commit.commentRestLines().strip(' \n\t'))
        html += '''<h3 class="commit-info">{short}</h3>
                   <div class="commit-msg">{rest}</div>'''.format(short = short, rest = rest)
        return html

    def _fDiffTree(self, diff_trees):
        html = ''

        if len(diff_trees) == 0:
            return html

        html += '<table class="diff-tree">'
        html += '''
        <tr>
            <td colspan="3" class="diff-tree-num-changes">{0} files changed</td>
        </tr>
        <tr>
            <td colspan="3"><hr /></td>
        </tr>'''.format(len(diff_trees))

        for d in diff_trees:
            path = d.to_file.rsplit('/', 1)
            if len(path) == 2:
                blobpath     = path[0]
                blobfilename = path[1]
            else:
                blobpath = '/'
                blobfilename = d.to_file

            blobv = { 'a'        : 'blob',
                      'id'       : self._id,
                      'blobid'   : d.to_id,
                      'path'     : blobpath,
                      'filename' : blobfilename }

            html += '<tr>'

            anchor = self.anchor(self._esc(d.to_file), v = blobv, cls = "diff-tree-file")
            html += '<td>{0}</td>'.format(anchor)

            if d.status == 'A': # added
                html += '<td class="diff-tree-A">[new file with mode: {0:04o}]</td>'.format(d.to_mode_oct & 0777)

            elif d.status in ['M', 'T']: # modified, or type changed
                mode_change = ''
                if d.from_mode != d.to_mode:
                    mode_change = '[changed'
                    if d.from_file_type != d.to_file_type:
                        mode_change += ' from {0} to {1}'.format(d.from_file_type, d.to_file_type)

                    if (d.from_mode_oct & 0777) != (d.to_mode_oct & 0777):
                        if d.from_mode_oct and d.to_mode_oct:
                            mode_change += ' mode: {0}->{1}'.format(d.from_mode, d.to_mode)
                        elif d.to_mode_oct:
                            mode_change += ' mode: {0}'.format(d.to_mode)
                    mode_change += ']'

                html += '<td class="diff-tree-T">{0}</td>'.format(mode_change)

            elif d.status == 'D': # deleted
                html += '<td class="diff-tree-D">[deleted {0}]</td>'.format(d.from_file_type)

            elif d.status in ['R', 'C']: # renamed or copied
                change = '[moved'
                if d.status == 'C':
                    change = 'copied'
                change += ' from <span class="diff-tree-RC-file">{0}</span> with {1} similarity]'
                change = change.format(self._esc(d.from_file), d.similarity)
                html += '<td class="diff-tree-RC">{0}</td>'.format(change)

            menu = '<a href="#{0}" class="menu">diff</a>'.format(d.from_id + d.to_id)
            menu += '&nbsp;|&nbsp;'
            menu += self.anchor('blob', v = blobv, cls = "menu")

            html += '<td class="diff-tree-menu">{0}</td>'.format(menu)
            html += '</tr>'

        html += '</table>'

        html += '<br />'

        html += self._fDiffTreePatch(diff_trees)

        return html

    def _fDiffTreePatch(self, diff_trees):
        html = ''

        for d in diff_trees:
            html += self._fPatch(d, d.patch)
        return html

    def _fPatch(self, d, patch):
        pat_head  = re.compile(r'^diff --git (a/.*) (b/.*)$')
        pat_index = re.compile(r'^index ([^\.]*)..([^ ]*)(.*)$')
        pat_from_file = re.compile(r'^---')
        pat_chunk = re.compile(r'^(@@.*@@)(.*)$')

        lines = patch.split('\n')

        html = ''
        html += '<div class="patch">'

        cur = 0
        length = len(lines)

        # header line
        m = pat_head.match(lines[cur])
        if m:
            path = d.from_file.rsplit('/', 1)
            if len(path) == 2:
                blobpath     = path[0]
                blobfilename = path[1]
            else:
                blobpath = '/'
                blobfilename = d.to_file
            blobv1 = { 'a'        : 'blob',
                       'id'       : self._id,
                       'blobid'   : d.from_id,
                       'path'     : blobpath,
                       'filename' : blobfilename }

            path = d.to_file.rsplit('/', 1)
            if len(path) == 2:
                blobpath     = path[0]
                blobfilename = path[1]
            else:
                blobpath = '/'
                blobfilename = d.to_file
            blobv2 = { 'a'        : 'blob',
                       'id'       : self._id,
                       'blobid'   : d.to_id,
                       'path'     : blobpath,
                       'filename' : blobfilename }

            a = m.group(1)
            b = m.group(2)
            html += '<a name="{0}"></a>'.format(d.from_id + d.to_id)
            html += '<div class="patch-header">'
            html += 'diff --git '
            html += self.anchor(a, v = blobv1, cls = '')
            html += '&nbsp;'
            html += self.anchor(b, v = blobv2, cls = '')
            html += '</div>'
            cur += 1

        html += '<div class="patch-index">'
        while cur < length and not pat_index.match(lines[cur]):
            if len(lines[cur]) > 0:
                html += lines[cur] + '<br />'
            cur += 1
        if cur < length:
            html += lines[cur]
        html += '</div>'
        cur += 1

        if cur < length:
            html += '<div class="patch-from-file">' + self._esc(lines[cur]) + '</div>'
            cur += 1
        if cur < length:
            html += '<div class="patch-to-file">' + self._esc(lines[cur]) + '</div>'
            cur += 1

        for line in lines[cur:]:
            m = pat_chunk.match(line)
            if m:
                html += '<div class="patch-chunk">'
                html += '<span class="patch-chunk-range">' + m.group(1) + '</span>'
                html += str(m.group(2))
                html += '</div>'
                continue

            if len(line) > 0 and line[0] == '-':
                html += '<div class="patch-rm">' + self._esc(line) + '</div>'
            elif len(line) > 0 and line[0] == '+':
                html += '<div class="patch-add">' + self._esc(line) + '</div>'
            else:
                html += '<div class="patch-line">' + self._esc(line) + '</div>'

        html += '</div>'

        return html


    def tpl(self, content):
        header = ''
        if self._projects:
            header += '<a href="{0}">projects</a>'.format(self._projects)
            header += '&nbsp;/&nbsp;'

        header += '<span class="project">{project_name}</span>'.format(project_name = self._project_name)

        sections = ['summary', 'log', 'refs', 'commit', 'diff', 'tree']
        menu = ''
        for sec in sections:
            cls = ''
            if sec == self._section:
                cls = 'sel'

            v = { 'a' : sec }
            if sec not in ['summary', 'refs', 'log']:
                v['id'] = self._id
            menu += self.anchor(sec, v = v, cls = cls)
        menu = '<table><tr><td>' + menu + '</td></tr></table>'

        errors = ''
        if len(self._errors) > 0:
            for e in self._errors:
                errors += '<div class="error">'
                errors += e
                errors += '</div>'

        html = '''
<html>
    <head>
        <style type="text/css">
        {css}
        </style>

        <title>pitweb - {project_name}</title>
    </head>

    <body>
        {errors}
        <div class="header">{header}</div>
        <div class="menu">{menu}</div>

        <div class="content">
            {content}
        </div>
    </body>
</html>
'''.format(css = self.css(), errors = errors,
           project_name = self._project_name,
           header = header, menu = menu, content = content)
        return html


    def css(self):
        h = '''
html * { font-family: sans; font-size: 13px; }
body { padding: 5px; }

hr { margin: 0px; border-width: 0px; border-top: 1px solid #999;}

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

div.header { padding: 7px; margin-bottom: 20px; font-size: 20px; background-color: #edece6; }
div.header * { font-size: 18px; }

div.menu table { width: 100%; border-bottom: 3px solid #c8c8c8; }
div.menu table tr:hover { background-color: white; }
div.menu a { padding-top: 3px; padding-bottom: 3px; padding-left: 5px; padding-right: 5px; margin-right: 10px;
             display: block-inline; background-color: #edece6; color: black; }
div.menu a:hover { background-color: #c8c8c8; text-decoration: none; }
div.menu a.sel { background-color: #c8c8c8; }

div.content { margin: 15px; }

div.commit-msg { font-family: monospace; white-space: pre; }

div.log_nav { margin: 10px; }
div.log_nav span.sep { margin-left: 5px; margin-right: 5px; }
div.log_nav span { color: #555555; }
table.log tr.log_header { font-weight: bold; font-size: 15px; }

table.refs a.head { font-weight: bold; color: #469446; }
table.refs a.ref_tag { font-weight: bold; color: #918f00; }
table.refs a.ref_remote { font-weight: bold; color: #4747ba; }

table.diff-tree tr td { font-family: monospace; font-size: 12px; }
table.diff-tree tr td * { font-family: monospace; font-size: 12px; }
td.diff-tree-num-changes { font-family: sans !important; font-style: italic; font-size: 13px !important; }
td.diff-tree-A { color: green; }
td.diff-tree-D { color: #C00000; }
td.diff-tree-RC { color: #777; }
span.diff-tree-RC-file { color: black; }
td.diff-tree-menu { font-family: sans !important; }
td.diff-tree-menu * { font-family: sans !important; }
a.diff-tree-file { color: black; }

div.patch { width: 100%; margin-bottom: 10px; }
div.patch * { font-family: monospace; white-space: pre; font-size: 12px; }
div.patch-header { background-color: #DDD; border-top: 1px solid #AAA; border-bottom: 1px solid #AAA;
                   font-weight: bold; padding: 3px; }
div.patch-index { background-color: #EEE; padding: 3px; color: #666; }
div.patch-index a { color: #666; }
div.patch-from-file { color: #A00; }
div.patch-to-file { color: #007000; }
div.patch-chunk { background-color: #fff7ff; border-top: 1px dotted #FFE0FF; margin-top: 2px; margin-bottom: 2px; }
span.patch-chunk-range { background-color: #ffe0ff; display: block-inline; color: #909; }
div.patch-rm { color: #A00; }
div.patch-add { color: #007000; }

table.tree tr.header * { font-family: sans; }
table.tree * { font-family: monospace; }
table.tree a.blob { color: black; }

div.blob * { font-family: monospace; }
div.blob { border-top: 1px solid black; }
div.blob-line * { white-space: pre; }
span.blob-linenum { color: #999; display: block-inline; border-right: 1px solid black; }

div.error { color: #A00; font-size: 12px; font-weight: bold; margin-bottom: 10px; }
        '''
        return h

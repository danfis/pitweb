from mod_python import apache, util
import string
import git
import re
import math
import mimetypes

###
# Sections:
#   - summary (like gitweb)
#   - log (like cgit)
#   - commit
#   - commitdiff
#   - tree
#   - refs (cgit)
#   
#   - snapshot
#   - tag
#   - patch

class ProjectBase(object):
    """ HTML interface for project specified by its directory. """

    def __init__(self, dir, req):
        self._git = git.Git(dir)
        self._req = req

        self._project_name = 'Project'

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

        self._commits_per_page = 50

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

    def setProjectName(self, name):
        self._project_name = name
    def setCommitsPerPage(self, p):
        self._commits_per_page = p

    def dbg(self, *args):
        s = string.join(map(lambda x: str(x), args), ' ')
        self._req.write(s)

    def esc(self, s):
        """ Replaces special characters in s by HTML escape sequences """
        s = s.replace('<', '&lt;')
        s = s.replace('>', '&gt;')
        s = s.replace('\n', '<br />')
        return s

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

        return apache.OK

    def write(self, s):
        self._req.write(s)

    def setContentType(self, type):
        self._req.content_type = type
    def setFilename(self, filename):
        self._req.headers_out['Content-disposition'] = ' attachment; filename="{0}"'.format(filename)



class Project(ProjectBase):
    def __init__(self, dir, req):
        super(Project, self).__init__(dir, req)

        self._tags, self._heads, self._remotes = self._git.refs()


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
        html += self.logTable(commits, longcomment = True, id = id, showmsg = showmsg, page = page)
        html += nav

        self.write(self.tpl(html))


    def refs(self):
        tags, heads, remotes = self._git.refs()

        html = ''

        # heads
        if len(heads) > 0:
            html += self.headsTable(heads)
            html += '<br />'

        # tags
        if len(tags) > 0:
            html += self.tagsTable(tags)
            html += '<br />'

        # remotes
        if len(remotes) > 0:
            html += self.remotesTable(remotes)
            html += '<br />'

        self.write(self.tpl(html))

    def summary(self):
        tags, heads, remotes = self._git.refs()
        commits = self._git.revList('HEAD', max_count = 15)
        commits = self._git.commitsSetRefs(commits, tags, heads, remotes)

        html = ''

        if len(heads) > 0:
            html += self.headsTable(heads)
            html += '<br />'

        if len(tags) > 0:
            html += self.tagsTable(tags, 10)
            html += '<br />'

        html += self.logTable(commits)

        self.write(self.tpl(html))


    def commit(self, id):
        commit = self._git.commit(id)
        parent = None
        if len(commit.parents) == 1:
            parent = commit.parents[0]
        diff_trees = self._git.diffTree(id, parent, patch = True)

        html = ''
        if commit:
            html += self.commitInfo(commit)
            html += '<br />'
            html += self.diffTreeTable(diff_trees)

        self.write(self.tpl(html))

    def patch(self, id, id2):
        patch = self._git.formatPatch(id, id2)
        self.setContentType('text/plain')
        self.write(patch)

    def diff(self, id, id2):
        diff_trees = self._git.diffTree(id, id2, patch = True)

        html = ''
        html += self.diffTreeTable(diff_trees)

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

        html += self.formatTreePath(path, treeid)
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

        html += self.formatTreePath(path, treeid, filename, blobid)
        html += '<br />'
        html += self.formatBlob(blob)

        self.write(self.tpl(html))


    def blobRaw(self, blobid, filename):
        blob = self._git.blob(blobid)
        type = mimetypes.guess_type(filename)
        mime_type = type[0]
        if not mime_type:
            mime_type = 'application/octet-stream'

        self.setContentType(mime_type)
        self.setFilename(filename)
        self.write(blob.data)


    def formatTreePath(self, path, treeid, blobname = None, blobid = None):
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

    def formatBlob(self, blob):
        html = ''

        lines = blob.data.split('\n')
        if len(lines[-1]) == 0:
            lines = lines[:-1]
        digits = int(math.ceil(math.log(len(lines), 10)))

        linepat = '<div class="blob-line">'
        linepat += '<span class="blob-linenum"> {{0: >{0}d}} </span>'
        linepat += '<span class="blob-line"> {{1}}</span>'
        linepat += '</div>'
        linepat = linepat.format(digits)

        html += '<div class="blob">'
        for i in range(0, len(lines)):
            line = lines[i]
            html += linepat.format(i + 1, self.esc(line))
        html += '</div>'

        return html



    def headsTable(self, heads):
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

            line = self.esc(comm.commentFirstLine())
            line = line.replace('{', '{{').replace('}', '}}')
            v = { 'a'  : 'log',
                  'id' : comm.id }
            commanchor = self.anchor(line, v = v, cls = 'comment')

            v = { 'a' : 'log',
                  'id' : h.id }
            nameanchor = self.anchor(self.esc(h.name), v = v, cls = 'head')

            html += '<tr>'
            html += '<td>' + nameanchor + '</td>'
            html += '<td>' + commanchor + '</td>'
            html += '<td><i>' + comm.author.name() + '</i></td>'
            html += '<td>' + comm.author.date.format('%Y-%m-%d') + '</td>'
            html += '<td>' + '</td>'
            html += '</tr>'

        html += '</table>'
        return html

    def tagsTable(self, tags, max = None):
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
            nameanchor = self.anchor(self.esc(t.name), v = v, cls = 'ref_tag')

            html += '<tr>'
            html += '<td>' + nameanchor + '</td>'
            html += '<td>' + self.esc(t.msg) + '</td>'
            html += '<td><i>' + self.esc(t.tagger.name()) + '</i></td>'
            html += '<td>' + t.tagger.date.format('%Y-%m-%d') + '</td>'
            html += '<td>' + '</td>'
            html += '</tr>'

        if len(tags) > max:
            html += '<tr><td colspan="6">'
            html += self.anchor('[ ... ]', v = { 'a' : 'refs' }, cls = 'ref_tag')
            html += '</td></tr>'
        html += '</table>'
        html += '<br />'
        return html

    def remotesTable(self, remotes):
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

            line = self.esc(comm.commentFirstLine())
            line = line.replace('{', '{{').replace('}', '}}')

            v = { 'a'  : 'log',
                  'id' : comm.id }
            commanchor = self.anchor(line, v = v, cls = 'comment')

            v = { 'a' : 'log',
                  'id' : r.id }
            nameanchor = self.anchor(self.esc(r.name), v = v, cls = 'ref_remote')

            html += '<tr>'
            html += '<td>' + nameanchor + '</td>'
            html += '<td>' + commanchor + '</td>'
            html += '<td><i>' + self.esc(comm.author.name()) + '</i></td>'
            html += '<td>' + comm.author.date.format('%Y-%m-%d') + '</td>'
            html += '<td>' + '</td>'
            html += '</tr>'

        html += '</table>'
        return html

    def logTable(self, commits, id = 'HEAD', longcomment = False, showmsg = False, page = 1):
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
            <td>{date}</td>
            <td><i>{author}</i></td>
            <td>'''

            line = self.esc(commit.commentFirstLine())
            line = line.replace('{', '{{')
            line = line.replace('}', '}}')

            h += self.anchorCommit(line, commit.id, cls = 'comment')

            for b in commit.heads:
                h += self.anchorLog(self.esc(b.name), b.id, showmsg, 1, cls = "branch")

            for t in commit.tags:
                h += self.anchorLog(self.esc(t.name), t.id, showmsg, 1, cls = "tag")

            for r in commit.remotes:
                h += self.anchorLog('remotes/' + self.esc(r.name), r.id, showmsg, 1, cls = "remote")

            h += '{longcomment}</td>'
            h += '<td>'
            h += self.anchor('commit', v = { 'a' : 'commit', 'id' : commit.id }, cls = 'menu') 
            h += '&nbsp;|&nbsp;'
            h += self.anchor('diff', v = { 'a' : 'diff', 'id' : commit.id }, cls = 'menu')
            h += '&nbsp;|&nbsp;'
            v = { 'a'      : 'tree',
                  'id'     : commit.id,
                  'treeid' : commit.tree }
            h += self.anchor('tree', v = v, cls = 'menu')
            #h += '&nbsp;|&nbsp;'
            #h += self.anchor('snapshot', v = {}, cls = 'menu')
            h += '</td>'
            h += '</tr>'

            longcomment = ''
            if showmsg:
                longcomment  = '<div class="commit-msg"><br />'
                longcomment += self.esc(commit.commentRestLines().strip(' \n\t'))
                longcomment += '</div><br />'

            html += h.format(id          = commit.id,
                             author      = self.esc(commit.author.name()),
                             date        = commit.author.date.format('%Y-%m-%d'),
                             longcomment = longcomment,
                             tree        = commit.tree)
        html += '</table>'

        return html


    def commitInfoPerson(self, title, person):
        p = self.esc(person.person)
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

    def commitInfo(self, commit):
        html = ''
        html += '<table class="commit-info">'

        # author, committer
        html += self.commitInfoPerson('author', commit.author)
        html += self.commitInfoPerson('committer', commit.committer)

        # commit
        comm = self.anchorCommit(commit.id, commit.id)
        comm += '&nbsp;&nbsp;('
        comm += self.anchor('patch', v = { 'a' : 'patch', 'id' : commit.id }, cls = "")
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
        html += '''
        <tr>
            <td>tree</td>
            <td colspan="2">{0}</td>
        </tr>'''.format(tree)

        # parents
        for parent in commit.parents:
            par = self.anchorCommit(parent, parent)
            par += '&nbsp;&nbsp;('
            par += self.anchor('diff', v = { 'a' : 'diff', 'id' : parent, 'id2' : commit.id }, cls = "")
            par += ')'
            par += '&nbsp;&nbsp;('
            par += self.anchor('patch', v = { 'a' : 'patch', 'id' : parent, 'id2' : commit.id }, cls = "")
            par += ')'
            html += '''
            <tr>
                <td>parent</td>
                <td colspan="2">{0}</td>
            </tr>
            '''.format(par)

        html += '</table>'

        # comment
        short = self.esc(commit.commentFirstLine())
        rest  = self.esc(commit.commentRestLines().strip(' \n\t'))
        html += '''<h3 class="commit-info">{short}</h3>
                   <div class="commit-msg">{rest}</div>'''.format(short = short, rest = rest)
        return html

    def diffTreeTable(self, diff_trees):
        html = ''
        html += '<table class="diff-tree">'
        html += '''
        <tr>
            <td colspan="3" class="diff-tree-num-changes">{0} files changed</td>
        </tr>
        <tr>
            <td colspan="3"><hr /></td>
        </tr>'''.format(len(diff_trees))

        for d in diff_trees:
            html += '<tr>'

            anchor = self.anchor(self.esc(d.to_file), v = { 'a' : 'blob', 'id' : d.to_id }, cls = "diff-tree-file")
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
                change = change.format(self.esc(d.from_file), d.similarity)
                html += '<td class="diff-tree-RC">{0}</td>'.format(change)

            menu = '<a href="#{0}" class="menu">diff</a>'.format(d.from_id + d.to_id)
            menu += '&nbsp;|&nbsp;'
            menu += self.anchor('blob', v = { 'a' : 'blob', 'id' : d.to_id }, cls = "menu")

            html += '<td class="diff-tree-menu">{0}</td>'.format(menu)
            html += '</tr>'

        html += '</table>'

        html += '<br />'

        html += self.diffTreePatch(diff_trees)

        return html

    def diffTreePatch(self, diff_trees):
        html = ''

        for d in diff_trees:
            html += self._formatPatch(d, d.patch)
        return html

    def _formatPatch(self, d, patch):
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
            a = m.group(1)
            b = m.group(2)
            html += '<a name="{0}"></a>'.format(d.from_id + d.to_id)
            html += '<div class="patch-header">'
            html += 'diff --git '
            html += self.anchor(a, v = { 'a' : 'tree', 'f' : a[2:], 'id' : d.from_id }, cls = '')
            html += '&nbsp;'
            html += self.anchor(b, v = { 'a' : 'tree', 'f' : b[2:], 'id' : d.to_id }, cls = '')
            html += '</div>'
            cur += 1

        html += '<div class="patch-index">'
        while cur < length and not pat_index.match(lines[cur]):
            if len(lines[cur]) > 0:
                html += lines[cur] + '<br />'
            cur += 1
        if cur < length:
            m = pat_index.match(lines[cur])
            a = m.group(1)
            b = m.group(2)
            html += 'index '
            html += self.anchor(a, v = { 'a' : 'tree', 'f' : a, 'id' : d.from_id }, cls = '')
            html += '..'
            html += self.anchor(b, v = { 'a' : 'tree', 'f' : b, 'id' : d.to_id }, cls = '')
            html += str(m.group(3))
        html += '</div>'
        cur += 1

        if cur < length:
            html += '<div class="patch-from-file">' + lines[cur] + '</div>'
            cur += 1
        if cur < length:
            html += '<div class="patch-to-file">' + lines[cur] + '</div>'
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
                html += '<div class="patch-rm">' + line + '</div>'
            elif len(line) > 0 and line[0] == '+':
                html += '<div class="patch-add">' + line + '</div>'
            else:
                html += '<div class="patch-line">' + line + '</div>'

        html += '</div>'

        return html

    def tpl(self, content):
        header = '<span class="project">{project_name}</span>'.format(project_name = self._project_name)

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

        html = '''
<html>
    <head>
        <link rel="stylesheet" type="text/css" href="/css/pitweb.css"/>

        <title>Pitweb - {project_name}</title>
    </head>

    <body>
        <div class="header">{header}</div>
        <div class="menu">{menu}</div>

        <div class="content">
            {content}
        </div>
    </body>
</html>
'''.format(project_name = self._project_name, header = header, menu = menu, content = content)
        return html


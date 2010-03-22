from mod_python import apache, util
import string
import git

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
        self._a       = args.get('a', 'log')
        self._id      = args.get('id', 'HEAD')
        self._id2     = args.get('id2', None)
        self._showmsg = args.get('showmsg', '0')
        if self._showmsg == '0':
            self._showmsg = False
        else:
            self._showmsg = True

        self._page    = int(args.get('page', '1'))

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
        if self._a == 'log':
            self._section = 'log'
            self.log(id = self._id, showmsg = self._showmsg, page = self._page)
        elif self._a == 'refs':
            self._section = 'refs'
            self.refs()
        elif self._a == 'summary':
            self._section = 'summary'
            self.summary()
        elif self._a == 'commit':
            self._section = 'commit'
            self.commit(id = self._id)
        elif self._a == 'patch':
            self.patch(id = self._id, id2 = self._id2)

        return apache.OK

    def write(self, s):
        self._req.write(s)

    def setContentType(self, type):
        self._req.content_type = type



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

        html = ''
        if commit:
            html += self.commitInfo(commit)
            html += '<br />'
            html += self.diffTreeTable(commit)

        self.write(self.tpl(html))

    def patch(self, id, id2):
        patch = self._git.formatPatch(id, id2)
        self.setContentType('text/plain')
        self.write(patch)



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

            h += '''
            {longcomment}
            </td>
            <td><a href="?a=commit;id={id}">commit</a></td>
            <td><a href="?a=diff;id={id}">diff</a></td>
            <td><a href="?a=tree;id={tree};parent={id}">tree</a></td>
            <td><a href="?a=snapshot;id={id}">snapshot</a></td>
        </tr>
        '''

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
        tree = self.anchor(commit.tree, v = { 'a' : 'tree', 'id' : commit.tree }, cls = "")
        html += '''
        <tr>
            <td>tree</td>
            <td colspan="2">{0}</td>
        </tr>'''.format(tree)

        # parents
        for parent in commit.parents:
            par = self.anchorCommit(parent, parent)
            par += '&nbsp;&nbsp;('
            par += self.anchor('diff', v = { 'a' : 'diff', 'id' : parent }, cls = "")
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

    def diffTreeTable(self, commit):
        diff_trees = self._git.diffTree(commit)

        html = ''
        html += '<table class="diff-tree">'
        html += '''
        <tr>
            <td colspan="3" class="diff-tree-num-changes">{0} files changed</td>
        </tr>'''.format(len(diff_trees))

        for d in diff_trees:
            html += '<tr>'

            anchor = self.anchor(self.esc(d.to_file), v = { 'a' : 'blob', 'id' : d.to_id }, cls = "diff-tree-file")
            html += '<td>{0}</td>'.format(anchor)

            if d.status == 'A': # added
                html += '<td class="diff-tree-A">[new file with mode: {0:04o}]</td>'.format(d.to_mode_oct & 0777)

                menu = self.anchor('blob', v = { 'a' : 'blob', 'id' : d.to_id }, cls = "")

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

                menu = self.anchor('diff', v = { 'a' : 'diff', 'id' : d.to_id }, cls = "")
                menu += '&nbsp;|&nbsp;'
                menu += self.anchor('blob', v = { 'a' : 'blob', 'id' : d.to_id }, cls = "")

            elif d.status == 'D': # deleted
                html += '<td class="diff-tree-D">[deleted {0}]</td>'.format(d.from_file_type)

                menu = self.anchor('blob', v = { 'a' : 'blob', 'id' : d.to_id }, cls = "")

            elif d.status in ['R', 'C']: # renamed or copied
                change = '[moved'
                if d.status == 'C':
                    change = 'copied'
                change += ' from <span class="diff-tree-RC-file">{0}</span> with {1} similarity]'
                change = change.format(self.esc(d.from_file), d.similarity)
                html += '<td class="diff-tree-RC">{0}</td>'.format(change)

                menu = self.anchor('diff', v = { 'a' : 'diff', 'id' : d.to_id }, cls = "")
                menu += '&nbsp;|&nbsp;'
                menu += self.anchor('blob', v = { 'a' : 'blob', 'id' : d.to_id }, cls = "")

            html += '<td class="diff-tree-menu">{0}</td>'.format(menu)
            html += '</tr>'

        html += '</table>'

        return html

    def tpl(self, content):
        header = '<span class="project">{project_name}</span>'.format(project_name = self._project_name)

        sections = ['summary', 'log', 'refs', 'commit', 'diff', 'tree']
        menu = ''
        for sec in sections:
            menu += '<a href="?a={0}"'.format(sec)
            if sec == self._section:
                menu += ' class="sel"'
            menu += '>{0}</a>'.format(sec)
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


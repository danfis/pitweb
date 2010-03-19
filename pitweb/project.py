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

    def run(self):
        if self._a == 'log':
            self._section = 'log'
            self.log(id = self._id, showmsg = self._showmsg, page = self._page)
        elif self._a == 'summary':
            pass

        return apache.OK

    def write(self, s):
        self._req.write(s)


    def summary(self):
        """ Returns Summary page """
        return ''

    def log(self, id = 'HEAD', showmsg = False, page = 1):
        """ Returns Log page """ 
        return ''

    def commit(self, id = 'HEAD'):
        """ Returns Commit page """
        return ''

    def commitdiff(self, id = 'HEAD', id2 = None, raw = False):
        return ''

    def tree(self, id = 'HEAD', parent = 'HEAD'):
        return ''

    def refs(self):
        return ''


    def snapshot(self, id = 'HEAD'):
        return ''

    def tag(self, id):
        return ''

    def patch(self, id = 'HEAD'):
        return ''


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


    def log(self, id = 'HEAD', showmsg = False, page = 1):
        max_count = self._commits_per_page * page;
        commits = self._git.revList(id, max_count = max_count)
        commits = commits[self._commits_per_page * (page - 1):]

        commits = self._git.commitsSetRefs(commits, self._tags, self._heads, self._remotes)

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


        # Log list
        html += '''
<table class="log">
        <tr class="log_header">
            <td>Age</td>
            <td>Author</td>
            <td>Commit message ({0})</td>
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

            line = commit.commentFirstLine()
            line = line.replace('{', '{{')
            line = line.replace('}', '}}')

            h += self.anchorLog(line, commit.id, showmsg, page, cls = 'comment')

            for b in commit.heads:
                h += self.anchorLog(b.name, b.id, showmsg, page, cls = "branch")

            for t in commit.tags:
                h += self.anchorLog(t.name, t.id, showmsg, page, cls = "tag")

            for r in commit.remotes:
                h += self.anchorLog('remotes/' + r.name, r.id, showmsg, page, cls = "remote")

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
                longcomment = '<br />' + commit.commentRestLines().replace('\n', '<br />') + '<br />'

            html += h.format(id          = commit.id,
                             author      = commit.author.person,
                             date        = commit.author.date.format('%Y-%m-%d'),
                             longcomment = longcomment,
                             tree        = commit.tree)
        html += '</table>'

        html += nav

        self.write(self.tpl(html))



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

    <bod>
        <div class="header">{header}</div>
        <div class="menu">{menu}</div>

        <div class="content">
            {content}
        </div>
    </body>
</html>
'''.format(project_name = self._project_name, header = header, menu = menu, content = content)
        return html


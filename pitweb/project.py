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


    def log(self, id = 'HEAD', showmsg = False, page = 1):
        max_count = self._commits_per_page * page;
        commits = self._git.revList(id, max_count = max_count)
        commits = commits[self._commits_per_page * (page - 1):]

        tags = self._git.tags()

        cdata = []
        for commit in commits:
            d = { 'id'          : commit.id,
                  'author'      : commit.author.person,
                  'date'        : commit.author.date.format('%Y-%m-%d'),
                  'comment'     : commit.commentFirstLine(),
                  'longcomment' : '',
                  'tree'        : commit.tree,
                  'tags'        : [],
                  'branches'    : [],
                }

            for t in tags:
                if t.objid == commit.id:
                    d['tags'].append({ 'id'   : t.id,
                                       'name' : t.name })

            if showmsg:
                d['longcomment'] = '<br />' + commit.commentRestLines().replace('\n', '<br />') + '<br />'

            cdata.append(d)

        data = { 'id'      : id,
                 'showmsg' : showmsg,
                 'page'    : page,
               }

        self.write(self.tplLog(data, cdata))


    def tpl(self, content):
        header = '<span class="project">{project_name}</span>'.format(project_name = self._project_name)

        sections = ['summary', 'log', 'commit']
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

    def tplLog(self, data, commits):
        html = ''

        if not data['showmsg']:
            expand = '<a href="?a=log;id={id};showmsg=1">Expand</a>'.format(**data)
        else:
            expand = '<a href="?a=log;id={id};showmsg=0">Collapse</a>'.format(**data)

        # Navigation
        nav = ''
        nav += '<div class="log_nav">'
        if data['page'] <= 1:
            nav += '<span>prev</span>'
        else:
            a = '<a href="?a=log;id={id};showmsg={showmsg};page={page}">prev</a>'
            showmsg = '0'
            if data['showmsg']:
                showmsg = '1'
            a = a.format(id = data['id'], showmsg = showmsg, page = data['page'] - 1)
            nav += a

        nav += '<span class="sep">|</span>'

        a = '<a href="?a=log;id={id};showmsg={showmsg};page={page}">next</a>'
        showmsg = '0'
        if data['showmsg']:
            showmsg = '1'
        a = a.format(id = data['id'], showmsg = showmsg, page = data['page'] + 1)
        nav += a
        nav += '</div>'

        html += nav

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

        for d in commits:
            h = '''
        <tr>
            <td>{date}</td>
            <td><i>{author}</i></td>
            <td><a href="?a=commit;id={id}" class="comment">{comment}</a>
            '''

            for t in d['tags']:
                h += '<a href="?a=log;id={id}" class="tag">{name}</a>'.format(**t)

            h += '''
                {longcomment}
            </td>
            <td><a href="?a=commit;id={id}">commit</a></td>
            <td><a href="?a=diff;id={id}">diff</a></td>
            <td><a href="?a=tree;id={tree};parent={id}">tree</a></td>
            <td><a href="?a=snapshot;id={id}">snapshot</a></td>
        </tr>
        '''

            html += h.format(**d)
        html += '</table>'

        html += nav

        return self.tpl(html)

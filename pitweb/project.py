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

    def __init__(self, dir):
        self._git = git.Git(dir)

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
    def __init__(self, dir):
        super(Project, self).__init__(dir)


    def log(self, id = 'HEAD', showmsg = False, page = 1):
        commits = self._git.revList(id, max_count = 50)

        cdata = []
        for commit in commits:
            d = { 'id'       : commit.id,
                  'author'   : commit.author.person,
                  'date'     : commit.author.date.format('%Y-%m-%d'),
                  'comment'  : commit.commentFirstLine(),
                  'tree'     : commit.tree,
                  'tags'     : [],
                  'branches' : [],
                }

            cdata.append(d)

        data = { 'id'      : id,
                 'showmsg' : showmsg,
                 'page'    : page,
               }

        return self.tplLog(data, cdata)


    def tpl(self, content):
        html = '''
<html>
    <head>
        <link rel="stylesheet" type="text/css" href=""/>
    </head>

    <body>
        <div class="header"></div>
        <div class="menu"></div>

        <div class="content">
            {content}
        </div>
    </body>
</html>
'''.format(content = content)
        return html

    def tplLog(self, data, commits):
        if len(data) == 0:
            return ''

        if not data['showmsg']:
            expand = '<a href="?a=log;id={id};showmsg=1">Expand</a>'.format(**data)
        else:
            expand = '<a href="?a=log;id={id};showmsg=0">Collapse</a>'.format(**data)

        html = '''<table class="log">
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
            html += '''
        <tr>
            <td>{date}</td>
            <td>{author}</td>
            <td><a href="?a=commit;id={id}">{comment}</a></td>
            <td><a href="?a=commit;id={id}">commit</a></td>
            <td><a href="?a=diff;id={id}">diff</a></td>
            <td><a href="?a=tree;id={tree};parent={id}">tree</a></td>
            <td><a href="?a=snapshot;id={id}">snapshot</a></td>
        </tr>
'''.format(**d)
        html += '</table>'

        return self.tpl(html)

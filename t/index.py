from mod_python import apache, util
from pitweb.git import *
from pitweb.project import Project


def handler(req):
    path = req.parsed_uri[apache.URI_PATH].split('/')
    path = filter(lambda x: len(x) > 0, path)
    req.content_type = 'text/html'

    if len(path) > 0 and path[0] == 'css':
        f = open('/home/danfis/dev/pitweb/pitweb/pitweb.css', 'r')
        s = f.read()
        f.close()
        req.write(s)
        req.content_type = 'text/css'
        return

    project = Project('/home/danfis/dev/pitweb/t/repo', req)
    return project.run()


def commits(req, git):
    commits = git.revList(max_count = -1)
    for commit in commits:
        req.write('Commit:<br />')
        req.write('&nbsp;&nbsp;id: ' + str(commit.id) + '<br />')
        req.write('&nbsp;&nbsp;tree: ' + str(commit.tree) + '<br />')
        req.write('&nbsp;&nbsp;parents: ' + str(commit.parents) + '<br />')
        if commit.author:
            req.write('&nbsp;&nbsp;author: ' + str(commit.author.person) + ', ' + commit.author.date.str() + '<br />')
        if commit.committer:
            req.write('&nbsp;&nbsp;committer: ' + str(commit.committer.person) + ', ' + commit.committer.date.str() + '<br />')
        req.write('&nbsp;&nbsp;comment:<pre>' + str(commit.comment) + '</pre><br />')

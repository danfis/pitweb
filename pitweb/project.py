from git import GitComm
from objs import *

class Project(object):
    def __init__(self, dir):
        self.git = GitComm(dir)

    def commit(self, id):
        commit = Commit(id)
        lines = self.git.revList(id, parents = True, header = True, max_count = 1)
        for l in lines: print l,

        commit.parse(lines)
        return commit

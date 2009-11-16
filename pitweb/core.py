from subprocess import Popen, PIPE, STDOUT

GIT = '/usr/bin/git'

class Git(object):
    def __init__(self, dir):
        self._dir = dir

    def _git(self, *args):
        comm = [GIT, '--git-dir={0}'.format(self._dir)]
        comm.extend(args)

        pipe = Popen(comm, stdout = PIPE, stderr = STDOUT)
        out = pipe.stdout.read()

        return out


if __name__ == '__main__':
    git = Git('../.git')
    print git._git('rev-list')

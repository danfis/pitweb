from subprocess import Popen, PIPE, STDOUT

#Interrogation commands
#
#       git-diff-files(1)
#           Compares files in the working tree and the index.
#
#       git-diff-index(1)
#           Compares content and mode of blobs between the index and repository.
#
#       git-diff-tree(1)
#           Compares the content and mode of blobs found via two tree objects.
#
#       git-for-each-ref(1)
#           Output information on each ref.
#
#       git-ls-files(1)
#           Show information about files in the index and the working tree.
#
#       git-ls-remote(1)
#           List references in a remote repository.
#
#       git-ls-tree(1)
#           List the contents of a tree object.
#
#       git-merge-base(1)
#           Find as good common ancestors as possible for a merge.
#
#       git-name-rev(1)
#           Find symbolic names for given revs.
#
#       git-pack-redundant(1)
#           Find redundant pack files.
#
#
#       git-show-index(1)
#           Show packed archive index.
#
#       git-show-ref(1)
#           List references in a local repository.
#
#       git-tar-tree(1)
#           (deprecated) Create a tar archive of the files in the named tree object.
#
#       git-unpack-file(1)
#           Creates a temporary file with a blob's contents.
#
#       git-var(1)
#           Show a git logical variable.
#
#       git-verify-pack(1)
#           Validate packed git archive files.
#
#       In general, the interrogate commands do not touch the files in the working tree.
#

class GitComm(object):
    """ This class is 1:1 interface to git commands. Meaning of most
        parameters of most methods should be obvious after reading man pages
        of corresponding git commands.

        Each method returns whole output of corresponding git command as
        list of lines without any modifications (no parsing is performed).

        Meaning of this class is as thin layer between git commands and
        python which is easier to use. All commands are run in other
        process using subprocess module and connected to currect process
        using pipe - subsequently, whole output is read and returned.

        The only argument of constructor is pathname to directory where git
        repository is located (see doc of git --git-dir).
    """

    def __init__(self, dir, git = None):
        self._dir = dir
        self._gitbin = '/usr/bin/git'

        if git is not None:
            self._gitbin = GIT

    def _git(self, args):
        comm = [self._gitbin, '--git-dir={0}'.format(self._dir)]
        comm.extend(args)

        pipe = Popen(comm, stdout = PIPE, stderr = STDOUT)
        out = pipe.stdout.readlines()
        pipe.stdout.close()

        return out

    def revList(self, obj = 'HEAD', parents = False, header = False,
                      max_count = -1):
        """ git-rev-list(1)
                Lists commit objects in reverse chronological order.
        """

        comm = ['rev-list']

        if parents:
            comm.append('--parents')
        if header:
            comm.append('--header')
        if max_count > 0:
            comm.append('--max-count={0}'.format(max_count))

        comm.append(obj)
        return self._git(comm)


    def catFile(self, obj = 'HEAD', type = False, size = False,
                      pretty = False):
        """ git-cat-file(1)
                Provide content or type and size information for repository objects.
        """

        comm = ['cat-file']

        if type:
            comm.append('-t')
        if size:
            comm.append('-s')
        if pretty:
            comm.append('-p')

        comm.append(obj)
        return self._git(comm)


    def lsTree(self, obj = 'HEAD', recursive = False, long = False,
                     full_tree = False):
        comm = ['ls-tree']

        if recursive:
            comm.append('-r')
        if long:
            comm.append('--long')
        if full_tree:
            comm.append('--full-tree')

        comm.append(obj)
        return self._git(comm)

if __name__ == '__main__':
    git = GitComm('../.git')

    print git.catFile(size = True)
    print git.revList(parents = True, header = True, max_count = 1)

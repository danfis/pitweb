import re
import datetime
from subprocess import Popen, PIPE, STDOUT
import stat

basic_patterns = {
    'id' : r'[0-9a-fA-F]{40}',
    'epoch' : r'[0-9]+',
    'tz'    : r'\+[0-9]+',
}

patterns = {
    'person'    : re.compile(r'[^ ]* (.*) ({epoch}) ({tz})$'.format(**basic_patterns)),
    'person2'   : re.compile(r'(.*) <(.*)>'),
	'diff-tree' : re.compile(r'^:([0-7]{6}) ([0-7]{6}) ([0-9a-fA-F]{40}) ([0-9a-fA-F]{40}) (.)([0-9]{0,3})\t(.*)$'),
	'diff-tree-patch' : re.compile(r'^diff --git'),
    'rev-list' : {
        'header'   : re.compile(r'^({0})( {0})*'.format(basic_patterns['id'])),
        'tree'     : re.compile(r'^tree ({0})$'.format(basic_patterns['id'])),
        'parent'   : re.compile(r'^parent ({0})$'.format(basic_patterns['id'])),
        'author'   : re.compile(r'^author (.*) ({epoch}) ({tz})$'.format(**basic_patterns)),
        'committer' : re.compile(r'^committer (.*) ({epoch}) ({tz})$'.format(**basic_patterns)),
    },
}

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

    def __init__(self, dir, gitbin = '/usr/bin/git'):
        self._dir = dir
        self._gitbin = gitbin

    def _git(self, args):
        comm = [self._gitbin, '--git-dir={0}'.format(self._dir)]
        comm.extend(args)

        pipe = Popen(comm, stdout = PIPE, stderr = STDOUT)
        #out = pipe.stdout.readlines()
        out = pipe.stdout.read()
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

    def forEachRef(self, format = None, sort = None, pattern = None):
        """ git-for-each-ref(1)
                Output information on each ref.
        """

        comm = ['for-each-ref']

        if format:
            comm.append('--format={0}'.format(format))
        if sort:
            comm.append('--sort={0}'.format(sort))

        if pattern:
            if type(pattern) == list:
                for p in pattern:
                    comm.append(p)
            else:
                comm.append(pattern)

        return self._git(comm)


    def catFile(self, obj = 'HEAD', type = 'commit', size = False,
                      pretty = False):
        """ git-cat-file(1)
                Provide content or type and size information for repository objects.
        """

        comm = ['cat-file']

        comm.append(type)

        #if type:
        #    comm.append('-t')
        if size:
            comm.append('-s')
        if pretty:
            comm.append('-p')

        comm.append(obj)
        return self._git(comm)

    def diffTree(self, obj = 'HEAD', parent = None, patch = False):
        comm = ['diff-tree']

        comm.append('-r')
        comm.append('--no-commit-id')
        comm.append('-M')
        comm.append('--root')
        comm.append('-a')

        if patch:
            comm.append('--patch-with-raw')

        if parent:
            comm.append(parent)
        else:
            comm.append('-c')

        comm.append(obj)
        return self._git(comm)

    def lsTree(self, obj = 'HEAD', recursive = False, long = False,
                     full_tree = False, zeroterm = True):
        comm = ['ls-tree']

        if recursive:
            comm.append('-r')
        if long:
            comm.append('--long')
        if full_tree:
            comm.append('--full-tree')
        if zeroterm:
            comm.append('-z')

        comm.append(obj)
        return self._git(comm)

    def formatPatch(self, id, id2):
        comm = ['format-patch']

        comm.append('-n')
        comm.append('--root')
        comm.append('--stdout')
        comm.append('--encoding=utf8')

        if id2 is None:
            comm.append('-1')
            comm.append(id)
        else:
            comm.append(id + '..' + id2)

        return self._git(comm)


class GitDate(object):
    def __init__(self, epoch, tz):
        self.gmt      = None
        self.local    = None
        self.local_tz = None

        self._parseEpochTz(epoch, tz)

    def format(self, format):
        return self.local.strftime(format)

    def __str__(self):
        date = ''
        if self.local:
            date += self.local.strftime('%Y-%m-%d %H:%M:%S')
        if self.local_tz:
            date += ' ' + self.local_tz

        return '<GitDate {0}>'.format(date)
    def str(self):
        date = ''
        if self.local:
            date += self.local.strftime('%Y-%m-%d %H:%M:%S')
        if self.local_tz:
            date += ' ' + self.local_tz

        return date

    def _parseEpochTz(self, epoch, tz):
        epoch = int(epoch)

        # prepare gmt epoch
        h = int(tz[1:3])
        m = int(tz[4:])
        if tz[0] == '+':
            gmtepoch = epoch - ((h + m/60) * 3600)
        else:
            gmtepoch = epoch + ((h + m/60) * 3600)

        date = datetime.datetime.fromtimestamp(epoch)
        gmtdate = datetime.datetime.fromtimestamp(gmtepoch)

        self.gmt      = gmtdate
        self.local    = date
        self.local_tz = tz

class GitPerson(object):
    def __init__(self, person, date):
        self.person = person
        self.date   = date

    def __str__(self):
        return '<GitPerson person={0}, date={1}>'.format(self.person, str(self.date))

    def name(self):
        global patterns
        m = patterns['person2'].match(self.person)
        if not m:
            return self.person
        return m.group(1)

class GitObj(object):
    def __init__(self, git, id = None):
        self.git = git
        self.id  = id

    def __str__(self):
        return '<{0} id={1}>'.format(self.__class__.__name__, self.id)

    def modeIsGitlink(self, mode_oct):
        return stat.S_IFMT(mode_oct) == 0160000

    def modeStr(self, mode_oct):
        if self.modeIsGitlink(mode_oct):
            return 'm---------'
        elif stat.S_ISDIR(mode_oct):
            return 'drwxr-xr-x'
        elif stat.S_ISREG(mode_oct):
            # git cares only about the executable bit
            if mode_oct & stat.S_IXUSR:
                return '-rwxr-xr-x'
            else:
                return '-rw-r--r--'
        elif stat.S_ISLNK(mode_oct):
            return 'lrwxrwxrwx'
        else:
            return '----------'

class GitCommit(GitObj):
    def __init__(self, git, id, tree, parents, author, committer, comment):
        super(GitCommit, self).__init__(git, id)

        self.tree      = tree
        self.parents   = parents
        self.author    = author
        self.committer = committer
        self.comment   = comment

        self.tags    = []
        self.heads   = []
        self.remotes = []

    def commentFirstLine(self):
        lines = self.comment.split('\n', 1)
        return lines[0]

    def commentRestLines(self):
        lines = self.comment.split('\n', 1)
        if len(lines) == 1:
            return ''

        return lines[1]

class GitTag(GitObj):
    def __init__(self, git, id, objid = None, name = '', msg = '', tagger = None):
        super(GitTag, self).__init__(git, id)

        self.objid = objid
        self.name  = name
        self.msg   = msg
        self.tagger = tagger

class GitHead(GitObj):
    def __init__(self, git, id, name = ''):
        super(GitHead, self).__init__(git, id)

        self.name  = name

    def commit(self):
        c = self.git.revList(self.id, max_count = 1)
        return c[0]

class GitDiffTree(GitObj):
    def __init__(self, git, from_mode, to_mode, from_id, to_id, status,
                            similarity, from_file, to_file, patch = ''):
        self.from_mode = from_mode
        self.to_mode   = to_mode
        self.from_id   = from_id
        self.to_id     = to_id
        self.status    = status
        self.similarity = similarity
        self.from_file = from_file
        self.to_file   = to_file
        self.patch     = patch

        self.from_mode_oct = int(self.from_mode, 8)
        self.to_mode_oct   = int(self.to_mode, 8)
        self.from_file_type = self.fileType(self.from_mode_oct)
        self.to_file_type   = self.fileType(self.to_mode_oct)

        if len(self.similarity) > 0:
            self.similarity = '{0}%'.format(int(self.similarity))

    def fileType(self, mode):
        if mode == 0:
            return ''

        # TODO S_ISGITLINK
        if stat.S_ISDIR(mode):
            return 'directory'
        elif stat.S_ISREG(mode):
            return 'file'
        elif stat.S_ISLNK(mode):
            return 'symlink'
        else:
            return 'unknown'

class GitTree(GitObj):
    def __init__(self, git, id, name, mode, size):
        super(GitTree, self).__init__(git, id)

        self.name = name
        self.mode = mode
        self.size = size

        self.mode_oct = int(mode, 8)

class GitBlob(GitObj):
    def __init__(self, git, id, name = '', mode = '', size = '', data = ''):
        super(GitBlob, self).__init__(git, id)

        self.name = name
        self.mode = mode
        self.size = size
        self.data = data

        self.mode_oct = -1
        if len(self.mode) > 0:
            self.mode_oct = int(mode, 8)



class Git(object):
    def __init__(self, dir, gitbin = '/usr/bin/git'):
        global patterns

        self._git = GitComm(dir, gitbin)
        self._patterns = patterns

    def revList(self, obj = 'HEAD', max_count = -1):
        # get raw data
        res = self._git.revList(obj, parents = True, header = True,
                                     max_count = max_count)

        # split into hunks (each corresponding with one commit)
        commits_str = res.split('\x00')

        # create GitCommit object from each string hunk
        commits = []
        for commit_str in commits_str:
            if len(commit_str) > 1:
                commits.append(self._parseCommit(commit_str))

        return commits

    def commit(self, id = 'HEAD'):
        c = self.revList(id, max_count = 1)
        if len(c) == 0:
            return None
        return c[0]

    def refs(self):
        format  = '%(objectname) %(objecttype) %(refname)'

        tags    = []
        heads   = []
        remotes = []

        # tags
        res = self._git.forEachRef(format = format, sort = '-*authordate', pattern = 'refs/tags')
        lines = res.split('\n')
        for line in lines:
            d = line.split(' ')
            if len(d) != 3:
                continue

            s = self._git.catFile(d[0], type = 'tag')
            tags.append(self._parseTag(d[0], s))

        # heads, remotes
        res = self._git.forEachRef(format = format,
                                   sort = '-committerdate', 
                                   pattern = ['refs/heads', 'refs/remotes'])
        lines = res.split('\n')
        for line in lines:
            d = line.split(' ')
            if len(d) != 3:
                continue

            if d[2][:11] == 'refs/heads/':
                id = d[0]
                name = d[2][11:]
                o = GitHead(self, id, name = name)
                heads.append(o)
            elif d[2][:13] == 'refs/remotes/':
                id = d[0]
                name = d[2][13:]
                o = GitHead(self, id, name = name)
                remotes.append(o)

        return (tags, heads, remotes, )


    def commitsSetRefs(self, commits, tags, heads, remotes):
        for c in commits:
            for t in tags:
                if t.objid == c.id:
                    c.tags.append(t)

            for h in heads:
                if h.id == c.id:
                    c.heads.append(h)

            for r in remotes:
                if r.id == c.id:
                    c.remotes.append(r)

        return commits


    def diffTree(self, id, parent, patch = False):
        s = self._git.diffTree(id, parent = parent, patch = patch)

        diff_trees = []

        lines = s.split('\n')
        patch_lines = []
        for i in range(0, len(lines)):
            line = lines[i]

            if len(line) == 0:
                patch_lines = lines[i+1:]
                break

            o = self._parseDiffTree(line)
            if o:
                diff_trees.append(o)

        if len(patch_lines) > 0:
            self._parseDiffTreePatch(diff_trees, patch_lines)

        return diff_trees

    def formatPatch(self, id, id2):
        return self._git.formatPatch(id, id2)

    def tree(self, id):
        s = self._git.lsTree(id, long = True, zeroterm = True)

        objs = []

        lines = s.split('\x00')
        for line in lines:
            if len(line) > 0:
                objs.append(self._parseTree(line))

        return objs

    def blob(self, id):
        s = self._git.catFile(id, 'blob')
        obj = GitBlob(self, id, data = s)
        return obj

    def _parseTree(self, line):
        p = line.split()

        if p[1] == 'tree':
            obj = GitTree(self, id = p[2], mode = p[0], size = p[3], name = p[4])
        else:
            obj = GitBlob(self, id = p[2], mode = p[0], size = p[3], name = p[4])

        return obj

    def _parseDiffTree(self, line):
        global patterns

        diff_tree = None
        match = patterns['diff-tree'].match(line)
        if match:
            status = match.group(5)
            if status in ['R', 'C']:
                from_file, to_file = match.group(7).split('\t', 1)
            else:
                from_file = to_file = match.group(7)

            diff_tree = GitDiffTree(self, from_mode  = match.group(1),
                                          to_mode    = match.group(2),
                                          from_id    = match.group(3),
                                          to_id      = match.group(4),
                                          status     = status,
                                          similarity = match.group(6),
                                          from_file  = from_file,
                                          to_file    = to_file)

        return diff_tree

    def _parseDiffTreePatch(self, diff_trees, lines):
        global patterns

        cur = 0
        patch = ''
        for line in lines:
            match = patterns['diff-tree-patch'].match(line)
            if match and len(patch) > 0:
                diff_trees[cur].patch = patch
                cur += 1
                patch = ''

            patch += line + '\n'

        if len(patch) > 0:
            diff_trees[cur].patch = patch

    def _parsePerson(self, line):
        match = self._patterns['person'].match(line)
        date   = GitDate(epoch = match.group(2), tz = match.group(3))
        person = GitPerson(person = match.group(1), date = date)
        return person

    def _parseIdParents(self, line):
        ids = line.split(' ')
        id      = ids[0]
        parents = []
        if len(ids) > 1:
            parents = ids[1:]
        return (id, parents, )

    def _parseCommit(self, s):
        lines = s.split('\n')

        id, parents = self._parseIdParents(lines.pop(0))
        tree        = None
        author      = None
        committer   = None
        comment     = ''
        for line in lines:
            if line[:4] == 'tree':
                tree = line[5:]
            if line[:6] == 'parent' and line[7:] not in parents:
                parents.append(line[7:])
            if line[:6] == 'author':
                author = self._parsePerson(line)
            if line[:9] == 'committer':
                committer = self._parsePerson(line)

            if line[:4] == '    ':
                comment += line[4:] + '\n'

        commit = GitCommit(self, id = id, tree = tree, parents = parents,
                                 author = author, committer = committer,
                                 comment = comment)
        return commit

    def _parseTag(self, id, s):
        lines = s.split('\n')

        readmsg = False

        objid = ''
        name  = ''
        msg   = ''

        for line in lines:
            if readmsg:
                msg += line
            elif line[:6] == 'object':
                objid = line[7:]
            elif line[:4] == 'tag ':
                name = line[4:]
            elif line[:6] == 'tagger':
                tagger = self._parsePerson(line)
            elif len(line) == 0:
                readmsg = True
                
        tag = GitTag(self, id = id, objid = objid, name = name, msg = msg, tagger = tagger)
        return tag

if __name__ == '__main__':
    git = GitComm('../.git')

    print git.catFile(size = True)
    print git.revList(parents = True, header = True, max_count = 1)

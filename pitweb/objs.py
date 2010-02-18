"""
    Class for each object which can be located in git repository.
    sources:
        http://eagain.net/articles/git-for-computer-scientists/
        http://www.kernel.org/pub/software/scm/git/docs/user-manual.html#the-object-database
"""

import re
import datetime



class Date(object):
    def __init__(self, gmt, local, tz):
        self.gmt = gmt
        self.local = local
        self.local_tz = tz

basic_patterns = {
    'id' : r'[0-9a-fA-F]{40}',
    'epoch' : r'[0-9]+',
    'tz'    : r'\+[0-9]+',
}

patterns = {
    'rev-list' : {
        'header'   : re.compile(r'^({0})( {0})*'.format(basic_patterns['id'])),
        'tree'     : re.compile(r'^tree ({0})$'.format(basic_patterns['id'])),
        'parent'   : re.compile(r'^parent ({0})$'.format(basic_patterns['id'])),
        'author'   : re.compile(r'^author (.*) ({epoch}) ({tz})$'.format(**basic_patterns)),
        'commiter' : r'', # TODO
    },
}

class Obj(object):
    def __init__(self, project, id = None):
        self._project = project
        self._id = id

    def setId(self, id):
        self._id = id
    def id(self):
        return self._id

    def _load(self):
        pass

    def _set(self, lines):
        pass

    def _get(self, attr):
        if getattr(self, '_' + attr) is None:
            if self._id is not None:
                self._load()
            else:
                return None
        return getattr(self, '_' + attr)


    def _parsePerson(self, name, epoch, tz):
        d = { 'name' : name,
              'date' : self._parseDate(epoch, tz),
            }
        return d
        
    def _parseDate(self, epoch, tz):
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

        return Date(gmtdate, date, tz)


class Blob(Obj):
    def __init__(self, project, id = None):
        super(Blob, self).__init__(project, id = id)

        self._data = None


class TreeEntry(Obj):
    def __init__(self, project, id = None):
        super(TreeEntry, self).__init__(project, id = id)

        self._mode = None
        self._type = None
        self._name = None

class Tree(Obj):
    def __init__(self, project, id = None):
        super(Tree, self).__init__(project, id = id)

        self._entries = None

        if id is not None:
            self._load()

    def _load(self):
        o = self._project.git.lsTree(self._id)
        # TODO

    def entries(self):
        return self._get('entries')


class Commit(Obj):
    def __init__(self, project, id = None):
        super(Commit, self).__init__(project, id = id)

        self._tree = None
        self._parents = None
        self._author = None
        self._commiter = None
        self._comment = None

    def parse(self, lines):
        match = patterns['rev-list']['header'].match(lines[0])
        if not match:
            return

        groups = match.groups()
        print groups
        self.setId(groups[0]) # read id
        self._parents = groups[1:] # read parents

        for line in lines[1:]:
            match = patterns['rev-list']['tree'].match(line)
            if match is not None:
                self._tree = match.group(1)

            match = patterns['rev-list']['author'].match(line)
            if match is not None:
                self._autor = self._parsePerson(*match.groups())
                

class Ref(Obj):
    def __init__(self, project, id = None):
        super(Ref, self).__init__(project, id = id)

class RemoteRef(Obj):
    def __init__(self, project, id = None):
        super(RemoteRef, self).__init__(project, id)

class Tag(Obj):
    def __init__(self, project, id = None):
        super(Tag, self).__init__(project, id = id)

        self._object = None
        self._object_type = None
        self._tagger = None
        self._msg = None


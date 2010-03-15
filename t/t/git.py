import unittest
from pitweb.git import *

#class TestGitComm(unittest.TestCase):
#    def setUp(self):
#        self.git = GitComm("repo")
#
#    def testRevList(self):
#        o = self.git.revList(max_count = 1)
#        self.assertEqual(len(o), 1)
#        self.assertEqual(o[0], '83f9bed114df8ada0fc75c59d6675e8fa0982b3c\n')
#
#        o = self.git.revList('HEAD^^1', max_count = 2)
#        self.assertEqual(len(o), 2)
#        self.assertEqual(o[0], 'e6c68c0e082b5af36e208bed84523330706bcfd7\n')
#        self.assertEqual(o[1], '5e257f30811ad10d37197de18f2cd131d5ca95ee\n')
#
#        o = self.git.revList('v0.1', parents = True, max_count = 1)
#        self.assertEqual(len(o), 1)
#        self.assertEqual(o[0], '142e1d538ec32ce33f4e492490e63f9cdb13264f af511766a241ff9c82c34c23b499c26222739951\n')
#
#        o = self.git.revList('8f968274', header = True, parents = True, max_count = 1)
#        c = ['8f9682743028cd64d7e478c5349173f7e7473ae7 071162c1dc253532261f29f9891b2167d6dda23b\n',
#             'tree 81534f7d5155ffccac7906ae729340b847245136\n',
#             'parent 071162c1dc253532261f29f9891b2167d6dda23b\n',
#             'author Daniel Fiser <danfis@danfis.cz> 1189674362 +0200\n',
#             'committer Daniel Fiser <danfis@danfis.cz> 1189674362 +0200\n',
#             '\n',
#             '    Hunk class, VectorPointerIterator template\n',
#             '    \n',
#             '    Created new class called Hunk with testsuite.\n',
#             '    Created new template VectorPointerIterator for iterators over vectors of\n',
#             '    pointers to some type. This dereferenced iterator returns copy of\n',
#             '    containing type not pointer to type.\n',
#             '\x00']
#        for line in o:
#            self.assertTrue(line in c)
#
#
#    def testCatFile(self):
#        o = self.git.catFile('v0.1', type = True)
#        self.assertEqual(len(o), 1)
#        self.assertEqual(o[0], 'tag\n')
#
#        o = self.git.catFile('8f968274', pretty = True)
#        c = ['tree 81534f7d5155ffccac7906ae729340b847245136\n',
#             'parent 071162c1dc253532261f29f9891b2167d6dda23b\n',
#             'author Daniel Fiser <danfis@danfis.cz> 1189674362 +0200\n',
#             'committer Daniel Fiser <danfis@danfis.cz> 1189674362 +0200\n',
#             '\n',
#             'Hunk class, VectorPointerIterator template\n',
#             '\n',
#             'Created new class called Hunk with testsuite.\n',
#             'Created new template VectorPointerIterator for iterators over vectors of\n',
#             'pointers to some type. This dereferenced iterator returns copy of\n',
#             'containing type not pointer to type.\n']
#        for l in o:
#            self.assertTrue(l in c)
#
#    def testLsTree(self):
#        o = self.git.lsTree()
#        #for l in o: print l,
#        # TODO


class TestGit(unittest.TestCase):
    def setUp(self):
        self.git = Git('repo')

    def testRevList(self):
        commits = self.git.revList(max_count = 1)
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].id, '83f9bed114df8ada0fc75c59d6675e8fa0982b3c')


        commits = self.git.revList(max_count = 2)
        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0].id, '83f9bed114df8ada0fc75c59d6675e8fa0982b3c')
        self.assertEqual(commits[0].parents[0], '99631cfe0f3fb1df97bfcd496c135e147e607ce5')
        self.assertEqual(commits[1].parents[0], 'e6c68c0e082b5af36e208bed84523330706bcfd7')

        #for commit in commits:
        #    print commit.id
        #    print commit.parents
        #    print commit.comment
        #    print commit.author

    def testTags(self):
        tags = self.git.tags()

        self.assertEqual(tags[0].id, 'f592a41ff8b1dbb76f6b185ebc291605eae1e66d')
        self.assertEqual(tags[0].objid, '83f9bed114df8ada0fc75c59d6675e8fa0982b3c')
        self.assertEqual(tags[0].name, 'v1.2')

        self.assertEqual(tags[2].id, 'b1429eb9183615662b345e5858409859d426b898')
        self.assertEqual(tags[2].objid, '308518fb9bbeb36151ed04d352aa96d514df8826')
        self.assertEqual(tags[2].name, 'v1.0')

    def testHeads(self):
        heads = self.git.heads()
        self.assertEqual(heads[0].id, '83f9bed114df8ada0fc75c59d6675e8fa0982b3c')
        self.assertEqual(heads[0].name, 'master')

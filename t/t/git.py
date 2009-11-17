import unittest
from pitweb.git import *

class TestGitComm(unittest.TestCase):
    def setUp(self):
        self.git = GitComm("repo")

    def testRevList(self):
        o = self.git.revList(max_count = 1)
        self.assertEqual(len(o), 1)
        self.assertEqual(o[0], '83f9bed114df8ada0fc75c59d6675e8fa0982b3c\n')

        o = self.git.revList('HEAD^^1', max_count = 2)
        self.assertEqual(len(o), 2)
        self.assertEqual(o[0], 'e6c68c0e082b5af36e208bed84523330706bcfd7\n')
        self.assertEqual(o[1], '5e257f30811ad10d37197de18f2cd131d5ca95ee\n')

        o = self.git.revList('v0.1', parents = True, max_count = 1)
        self.assertEqual(len(o), 1)
        self.assertEqual(o[0], '142e1d538ec32ce33f4e492490e63f9cdb13264f af511766a241ff9c82c34c23b499c26222739951\n')

        o = self.git.revList('8f968274', header = True, parents = True, max_count = 1)
        c = ['8f9682743028cd64d7e478c5349173f7e7473ae7 071162c1dc253532261f29f9891b2167d6dda23b\n',
             'tree 81534f7d5155ffccac7906ae729340b847245136\n',
             'parent 071162c1dc253532261f29f9891b2167d6dda23b\n',
             'author Daniel Fiser <danfis@danfis.cz> 1189674362 +0200\n',
             'committer Daniel Fiser <danfis@danfis.cz> 1189674362 +0200\n',
             '\n',
             '    Hunk class, VectorPointerIterator template\n',
             '    \n',
             '    Created new class called Hunk with testsuite.\n',
             '    Created new template VectorPointerIterator for iterators over vectors of\n',
             '    pointers to some type. This dereferenced iterator returns copy of\n',
             '    containing type not pointer to type.\n',
             '\x00']
        for line in o:
            self.assertTrue(line in c)


    def testCatFile(self):
        o = self.git.catFile('v0.1', type = True)
        self.assertEqual(len(o), 1)
        self.assertEqual(o[0], 'tag\n')

        o = self.git.catFile('8f968274', pretty = True)
        c = ['tree 81534f7d5155ffccac7906ae729340b847245136\n',
             'parent 071162c1dc253532261f29f9891b2167d6dda23b\n',
             'author Daniel Fiser <danfis@danfis.cz> 1189674362 +0200\n',
             'committer Daniel Fiser <danfis@danfis.cz> 1189674362 +0200\n',
             '\n',
             'Hunk class, VectorPointerIterator template\n',
             '\n',
             'Created new class called Hunk with testsuite.\n',
             'Created new template VectorPointerIterator for iterators over vectors of\n',
             'pointers to some type. This dereferenced iterator returns copy of\n',
             'containing type not pointer to type.\n']
        for l in o:
            self.assertTrue(l in c)
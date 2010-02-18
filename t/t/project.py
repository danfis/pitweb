import unittest
from pitweb import *

class TestProjectComm(unittest.TestCase):
    def setUp(self):
        self.project = Project("repo")

    def testCommit(self):
        print self.project.commit('HEAD')

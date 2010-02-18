import string
import unittest

import git, project

def moduleName(m):
    n = m.__name__
    n = string.split(n, '.')
    return n[-1]

modules = [git, project]


__all__ = ['suite']

suite = {}

for m in modules:
    name = moduleName(m)
    suite[name] = unittest.TestSuite()
    s = unittest.TestLoader().loadTestsFromModule(m)
    suite[name].addTest(s)

suite['all'] = unittest.TestSuite()

for m in modules:
    s = unittest.TestLoader().loadTestsFromModule(m)
    suite['all'].addTest(s)


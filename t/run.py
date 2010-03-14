#!/usr/bin/env python

import sys
import unittest
import cProfile

import t

profile_file = '.profile.stat'

suite = unittest.TestSuite()


if len(sys.argv) > 1:
    if not t.suite.has_key(sys.argv[1]):
        print >>sys.stderr, "{0}: No such suite available".format(sys.argv[1])
        sys.exit(-1)

    suite.addTest(t.suite[sys.argv[1]])
else:
    suite.addTest(t.suite['all'])


if __name__ == '__main__':
    cProfile.run('unittest.TextTestRunner(verbosity=2).run(suite)', profile_file)

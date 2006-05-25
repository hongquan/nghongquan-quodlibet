from __future__ import division

import unittest, sys
suites = []
add = registerCase = suites.append
from unittest import TestCase

import test___init__
import test_id3
import test_apev2
import test__vorbis
import test_flac
import test_mp3
import test_oggvorbis
import test_oggflac
import test_ogg
import test_easyid3
import test__util

class Result(unittest.TestResult):

    separator1 = '=' * 70
    separator2 = '-' * 70

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        sys.stdout.write('.')

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        sys.stdout.write('E')

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        sys.stdout.write('F')

    def printErrors(self):
        succ = self.testsRun - (len(self.errors) + len(self.failures))
        v = "%3d" % succ
        count = 50 - self.testsRun
        sys.stdout.write((" " * count) + v + "\n")
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            sys.stdout.write(self.separator1 + "\n")
            sys.stdout.write("%s: %s\n" % (flavour, str(test)))
            sys.stdout.write(self.separator2 + "\n")
            sys.stdout.write("%s\n" % err)

class Runner:
    def run(self, test):
        suite = unittest.makeSuite(test)
        pref = '%s (%d): ' % (test.__name__, len(suite._tests))
        print pref + " " * (25 - len(pref)),
        result = Result()
        suite(result)
        result.printErrors()
        return bool(result.failures + result.errors)

def unit(run = []):
    runner = Runner()
    failures = False
    for test in suites:
        if not run or test.__name__ in run:
            failures |= runner.run(test)
    return failures

if __name__ == "__main__":
    raise SystemExit(unit(sys.argv[1:]))

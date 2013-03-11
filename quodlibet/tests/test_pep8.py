# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import subprocess
import unittest

from tests import TestCase, add

from quodlibet.util import iscommand


class TPEP8(TestCase):
    def test_utils(self):
        from quodlibet import util
        path = util.__path__[0]
        subprocess.check_call(["pep8", path])

    def test_library(self):
        from quodlibet import library
        path = library.__path__[0]
        subprocess.check_call(["pep8", path])

    def test_parse(self):
        from quodlibet import parse
        path = parse.__path__[0]
        subprocess.check_call(["pep8", path])

    def test_browsers(self):
        from quodlibet import browsers
        path = browsers.__path__[0]
        subprocess.check_call(["pep8", path])


if iscommand("pep8"):
    add(TPEP8)
else:
    print_w("pep8 not found")

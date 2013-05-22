#!/usr/bin/env python

0<>0 # Python 3.x not supported. Use 2.6+ instead.

import glob
import os
import shutil
import sys

# disable translations
os.environ["QUODLIBET_NO_TRANS"] = ""

from distutils.core import setup, Command
from distutils.dep_util import newer
from distutils.command.build_scripts import build_scripts as distutils_build_scripts
from distutils.spawn import find_executable

from gdist import GDistribution
from gdist.clean import clean as gdist_clean

PACKAGES = ("browsers devices formats library parse plugins qltk "
            "util player").split()

# TODO: link this better to the app definitions
MIN_PYTHON_VER = (2,6)
MIN_PYTHON_VER_STR = ".".join(map(str,MIN_PYTHON_VER))

class clean(gdist_clean):
    def run(self):
        gdist_clean.run(self)

        if not self.all:
            return

        def should_remove(filename):
            if (filename.lower()[-4:] in [".pyc", ".pyo"] or
                filename.endswith("~") or
                (filename.startswith("#") and filename.endswith("#"))):
                return True
            else:
                return False
        for pathname, dirs, files in os.walk(os.path.dirname(__file__)):
            for filename in filter(should_remove, files):
                try: os.unlink(os.path.join(pathname, filename))
                except EnvironmentError, err:
                    print str(err)

        for base in ["coverage", "build", "dist"]:
            path = os.path.join(os.path.dirname(__file__), base)
            if os.path.isdir(path):
                shutil.rmtree(path)

class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
        ("suite=", None, "test suite (folder) to run (default 'tests')"),
        ("strict", None, "make glib warnings / errors fatal"),
        ]
    use_colors = sys.stderr.isatty() and os.name != "nt"

    def initialize_options(self):
        self.to_run = []
        self.suite = "tests"
        self.strict = False

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")
        self.strict = bool(self.strict)

    @classmethod
    def _red(cls, text):
        from quodlibet.util.dprint import Colorise
        return Colorise.red(text) if cls.use_colors else text

    def run(self):
        mods = sys.modules.keys()
        if "gi" in mods:
            raise SystemExit("E: setup.py shouldn't depend on gi")

        tests = __import__("tests")
        subdir = (self.suite != "tests" and self.suite) or None
        failures, errors = tests.unit(self.to_run, subdir=subdir,
                                      strict=self.strict)
        if failures or errors:
            raise SystemExit(self._red("%d test failure(s) and "
                                       "%d test error(s), as detailed above."
                             % (failures, errors)))

class build_scripts(distutils_build_scripts):
    description = "copy scripts to build directory"

    def run(self):
        self.mkpath(self.build_dir)
        for script in self.scripts:
            newpath = os.path.join(self.build_dir, os.path.basename(script))
            if newpath.lower().endswith(".py"):
                newpath = newpath[:-3]
            if newer(script, newpath) or self.force:
                self.copy_file(script, newpath)

class coverage_cmd(Command):
    description = "generate test coverage data"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
    ]

    def initialize_options(self):
        self.to_run = []

    def finalize_options(self):
        pass

    def run(self):
        # Wipe existing modules, to make sure coverage data is properly
        # generated for them.
        for key in sys.modules.keys():
            if key.startswith('quodlibet'):
                del(sys.modules[key])

        import trace
        tracer = trace.Trace(
            count=True, trace=False,
            ignoredirs=[sys.prefix, sys.exec_prefix])
        def run_tests():
            cmd = self.reinitialize_command("test")
            cmd.to_run = self.to_run[:]
            cmd.ensure_finalized()
            cmd.run()
        tracer.runfunc(run_tests)
        results = tracer.results()

        coverage = os.path.join(os.path.dirname(__file__), "coverage")
        results.write_results(show_missing=True, coverdir=coverage)

        map(os.unlink, glob.glob(os.path.join(coverage, "[!q]*.cover")))
        try: os.unlink(os.path.join(coverage, "..setup.cover"))
        except OSError: pass

        # compute coverage
        stats = []
        cov_files = []
        for filename in glob.glob(os.path.join(coverage, "*.cover")):
            cov_files.append(filename)
            lines = file(filename, "rU").readlines()
            lines = filter(None, map(str.strip, lines))
            total_lines = len(lines)
            if not total_lines:
                continue
            bad_lines = len([l for l in lines if l.startswith(">>>>>>")])
            percent = 100.0 * (total_lines - bad_lines) / float(total_lines)
            stats.append((percent, filename, total_lines, bad_lines))
        stats.sort(reverse=True)
        print "#" * 80
        print "COVERAGE"
        print "#" * 80
        total_sum = 0
        bad_sum = 0
        for s in stats:
            p, f, t, b = s
            total_sum += t
            bad_sum += b
            print "%6.2f%% %s" % (p, os.path.basename(f))
        print "-" * 80
        print "Coverage data written to", coverage, "(%d/%d, %0.2f%%)" % (
            total_sum - bad_sum, total_sum,
            100.0 * (total_sum - bad_sum) / float(total_sum))
        print "#" * 80


def recursive_include(dir, pre, ext):
    all = []
    old_dir = os.getcwd()
    os.chdir(dir)
    for path, dirs, files in os.walk(pre):
        for file in files:
            if file.split('.')[-1] in ext:
                all.append(os.path.join(path, file))
    os.chdir(old_dir)
    return all

def recursive_include_py2exe(dir, pre, ext):
    all = []
    dir = os.path.join(dir, pre)
    for path, dirs, files in os.walk(dir):
        all_path = []
        for file in files:
            if file.split('.')[-1] in ext:
                all_path.append(os.path.join(path, file))
        if all_path: all.append((path, all_path))
    return all

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from quodlibet import const
    cmd_classes = {'clean': clean, "test": test_cmd,
                   "coverage": coverage_cmd, "build_scripts": build_scripts}
    setup_kwargs = {
        'distclass': GDistribution,
        'cmdclass': cmd_classes,
        'name': "quodlibet",
        'version': const.VERSION,
        'url': "http://code.google.com/p/quodlibet/",
        'description': "a music library, tagger, and player",
        'author': "Joe Wreschnig, Michael Urman, & others",
        'author_email': "quod-libet-development@googlegroups.com",
        'maintainer': "Steven Robertson and Christoph Reiter",
        'license': "GNU GPL v2",
        'packages': ["quodlibet"] + map("quodlibet.".__add__, PACKAGES),
        'package_data': {"quodlibet": recursive_include("quodlibet", "images",
            ("svg", "png", "cache", "theme"))},
        'scripts': ["quodlibet.py", "exfalso.py", "operon.py"],
        'po_directory': "po",
        'po_package': "quodlibet",
        'shortcuts': ["data/quodlibet.desktop", "data/exfalso.desktop"],
        'man_pages': ["man/quodlibet.1", "man/exfalso.1", "man/operon.1"],
        }
    if os.name == 'nt':
        # (probably) necessary to get the right DLLs pulled in by py2exe
        import pygst
        pygst.require('0.10')
        from os.path import join

        # taken from http://www.py2exe.org/index.cgi/win32com.shell
        # ModuleFinder can't handle runtime changes to __path__, but win32com uses them
        try:
            # py2exe 0.6.4 introduced a replacement modulefinder.
            # This means we have to add package paths there, not to the built-in
            # one.  If this new modulefinder gets integrated into Python, then
            # we might be able to revert this some day.
            # if this doesn't work, try import modulefinder
            try:
                import py2exe.mf as modulefinder
            except ImportError:
                import modulefinder
            import win32com
            for p in win32com.__path__[1:]:
                modulefinder.AddPackagePath("win32com", p)
            for extra in ["win32com.shell"]: #,"win32com.mapi"
                __import__(extra)
                m = sys.modules[extra]
                for p in m.__path__[1:]:
                    modulefinder.AddPackagePath(extra, p)
        except ImportError:
            # no build path setup, no worries.
            pass

        data_files = [('', ['COPYING'])] +  recursive_include_py2exe(
            "quodlibet", "images", ("svg", "png", "cache", "theme"))

        for type in ["playorder", "songsmenu", "editing", "events", "gstreamer"]:
            data_files.append((join('quodlibet', 'plugins', type),
                glob.glob(join('..', 'plugins', type, '*.py'))))

        setup_kwargs.update({
            'data_files': data_files,
            'windows': [
                {
                    "script": "quodlibet.py",
                    "icon_resources": [(0,
                       join('..', 'win_installer', 'quodlibet.ico'))]
                },
                # workaround icon not working under Vista/7
                # exe resource identifiers get incremented and start at 0.
                # and 0 doesn't seem to be valid.
                {
                    "script": "quodlibet.py",
                    "icon_resources": [(0,
                       join('..', 'win_installer', 'quodlibet.ico'))]
                },
                {
                    "script": "exfalso.py",
                    "icon_resources": [(0,
                        join('..', 'win_installer', 'exfalso.ico'))]
                }
            ],
            'options': {
                'py2exe': {
                    'packages': ('encodings, feedparser, quodlibet, '
                                 'HTMLParser, gtk, glib, gobject, '
                                 'musicbrainz2, shelve, json, pyHook'),
                    'includes': ('cairo, pango, pangocairo, atk, gio, '
                                 'pygst, gst, quodlibet.player.gstbe, '
                                 'CDDB'),
                    'excludes': ('ssl_', 'doctest', 'pdb', 'unittest',
                                 'difflib', 'inspect'),
                    'skip_archive': True,
                    'dist_dir': 'dist\\bin'
                }
            }
        })
    setup(**setup_kwargs)


# -*- coding: utf-8 -*-
# Constants used in various parts of QL, mostly strings.

import sys
import os
import locale

if os.name == "nt":
    from win32com.shell import shellcon, shell


class Version(tuple):
    """Represent the version of a dependency as a tuple"""

    def __new__(cls, *args):
        # Support tuple or varargs instantiation
        value = args[0] if len(args) == 1 else args
        return tuple.__new__(Version, value)

    def human_version(self):
        return ".".join(map(str, self))

    def __str__(self):
        return self.human_version()


class MinVersions(object):
    """Dependency requirements for Quod Libet / Ex Falso"""
    PYTHON = Version(2, 6)
    MUTAGEN = Version(1, 14)

VERSION_TUPLE = Version(3, 0, -1)
VERSION = str(VERSION_TUPLE)

PROCESS_TITLE_QL = "quodlibet"
PROCESS_TITLE_EF = "exfalso"

# expanduser doesn't work with unicode on win...
if os.name == "nt":
    # the last 0 means SHGFP_TYPE_CURRENT
    HOME = shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, 0, 0)
else:
    HOME = os.path.expanduser("~")

if 'QUODLIBET_USERDIR' in os.environ:
    USERDIR = os.environ['QUODLIBET_USERDIR']
else:
    if os.name == "nt":
        USERDIR = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        USERDIR = os.path.join(USERDIR, "Quod Libet")
    else:
        USERDIR = os.path.join(HOME, ".quodlibet")

CONTROL = os.path.join(USERDIR, "control")
CONFIG = os.path.join(USERDIR, "config")
CURRENT = os.path.join(USERDIR, "current")
LIBRARY = os.path.join(USERDIR, "songs")
LOGDIR = os.path.join(USERDIR, "logs")

# Don't bother saving the library more often than this
LIBRARY_SAVE_PERIOD_SECONDS = 15 * 60

# entry point for the user guide / wiki
BRANCH_NAME = "default"
DOCS_BASE_URL = "https://quodlibet.readthedocs.org/en/%s"
DOCS_BASE_URL %= BRANCH_NAME if BRANCH_NAME != "default" else "latest"
ONLINE_HELP = DOCS_BASE_URL + "/guide/index.html"
SEARCH_HELP = DOCS_BASE_URL + "/guide/searching.html"

# about dialog, --version etc.
WEBSITE = "http://code.google.com/p/quodlibet"
COPYRIGHT = """\
Copyright © 2004-2013 Joe Wreschnig, Michael Urman, Iñigo Serna,
Steven Robertson, Christoph Reiter, Nick Boultbee, ..."""

# Email used as default for reading/saving per-user data in tags, etc.
EMAIL = os.environ.get("EMAIL", "quodlibet@lists.sacredchao.net")

# Displayed as registered / help email address
SUPPORT_EMAIL = "quod-libet-development@googlegroups.com"

BASEDIR = os.path.dirname(os.path.realpath(__file__))
IMAGEDIR = os.path.join(BASEDIR, "images")

AUTHORS = sorted("""\
Alexandre Passos
Alexey Bobyakov
Alex Geoffrey Smith
Anders Carlsson
Andreas Bombe
Anton Shestakov
Ari Pollak
Aymeric Mansoux
Bastian Kleineidam
Bastien Gorissen
Ben Zeigler
Carlo Teubner
Christine Spang
Christoph Reiter
David Kågedal
David Schneider
Decklin Foster
Eduardo Gonzalez
Erich Schubert
Federico Pelloni
Felix Krull
Florian Demmer
Guillaume Chazarain
Hans Scholze
Iñigo Serna
Jacob Lee
Jan Arne Petersen
Javier Kohen
Joe Higton
Joe Wreschnig
Johan Hovold
Johannes Marbach
Johannes Rohrer
Joschka Fischer
Josh Lee
Joshua Kwan
Lalo Martins
Lee Willis
Lukáš Lalinský
Markus Koller
Martijn Pieters
Martin Bergström
Michaël Ball
Michael Urman
Mickael Royer
Nicholas J. Michalek
Nick Boultbee
Niklas Janlert
Nikolai Prokoschenko
Philipp Müller
Philipp Weis
Remi Vanicat
Robert Muth
Sebastian Thürrschmidt
Simonas Kazlauskas
Steven Robertson
Tobias Wolf
Tomasz Miasko
Tomasz Torcz
Tshepang Lekhonkhobe
Türerkan İnce
Vasiliy Faronov
Zack Weinberg
""".strip().split("\n"))

TRANSLATORS = sorted("""
Alexandre Passos (pt)
Andreas Bertheussen (nb)
Anton Shestakov (ru)
Bastian Kleineidam (de)
Bastien Gorissen (fr)
Byung-Hee HWANG (ko)
ChangBom Yoon (ko)
Daniel Nyberg (sv)
Dimitris Papageorgiou (el)
Djavan Fagundes (pt)
Einārs Sprūģis (lv)
Eirik Haatveit (nb)
Emfox Zhou (zh_CN)
Erik Christiansson (sv)
Fabien Devaux (fr)
Filippo Pappalardo (it)
Guillaume Ayoub (fr)
Hans van Dok (nl)
Honza Hejzl (cs_CZ)
Hsin-lin Cheng (zh_TW)
Jari Rahkonen (fi)
Javier Kohen (es)
Joe Wreschnig (en_CA)
Johám-Luís Miguéns Vila (es, gl, gl_ES, eu, pt)
Jonas Slivka (lt)
Joshua Kwan (fr)
Luca Baraldi (it)
Lukáš Lalinský (sk)
Mathieu Morey (fr)
Michal Nowikowski (pl)
Mugurel Tudor (ro)
Mykola Lynnyk (uk)
Naglis Jonaitis (lt)
Nick Boultbee (fr, en_GB)
Olivier Gambier (fr)
Piarres Beobide (eu)
Piotr Drąg (pl)
Roee Haimovich (he)
Rüdiger Arp (de)
SZERVÁC Attila (hu)
Tomasz Torcz (pl)
Türerkan İnce (tr)
Witold Kieraś (pl)
Yasushi Iwata (ja)
Δημήτρης Παπαγεωργίου (el)
Андрей Федосеев (ru)
Микола 'Cthulhu' Линник (uk)
Николай Прокошенко (ru)
Ростислав "zbrox" Райков (bg)
Сергей Федосеев (ru)
""".strip().splitlines())

ARTISTS = sorted("""\
Tobias
Jakub Steiner
Fabien Devaux
""".strip().split("\n"))

# Default songlist column headers
DEFAULT_COLUMNS = "~#track ~people ~title~version ~album~discsubtitle " \
                  "~#length".split()

TBP = os.path.join(USERDIR, "lists", "tagpatterns")
TBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
<artist> - <album>/<tracknumber>. <title>
<artist>/<album>/<tracknumber> - <title>"""

NBP = os.path.join(USERDIR, "lists", "renamepatterns")
NBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber|<tracknumber>. ><title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
/path/<artist> - <album>/<tracknumber>. <title>
/path/<artist>/<album>/<tracknumber> - <title>"""

DEBUG = ("--debug" in sys.argv or "QUODLIBET_DEBUG" in os.environ)

MENU = """<ui>
  <menubar name='Menu'>
    <menu action='Music'>
      <menuitem action='AddFolders'/>
      <menuitem action='AddFiles'/>
      <menuitem action='AddLocation'/>
      <separator/>
      <menu action='BrowseLibrary'>
      %(browsers)s
      </menu>
      <separator/>
      <menuitem action='Preferences'/>
      <menuitem action='Plugins'/>
      <separator/>
      <menuitem action='RefreshLibrary'/>
      <menuitem action='ReloadLibrary'/>
      <separator/>
      <menuitem action='Quit'/>
    </menu>
    <menu action='Filters'>
      <menuitem action='FilterGenre'/>
      <menuitem action='FilterArtist'/>
      <menuitem action='FilterAlbum'/>
      <separator/>
      <menuitem action='RandomGenre'/>
      <menuitem action='RandomArtist'/>
      <menuitem action='RandomAlbum'/>
      <separator/>
      <menuitem action='All'/>
      <menuitem action='PlayedRecently'/>
      <menuitem action='AddedRecently'/>
      <menuitem action='TopRated'/>
    </menu>
    <menu action='Control'>
      <menuitem action='Previous'/>
      <menuitem action='PlayPause'/>
      <menuitem action='Next'/>
      <menuitem action='StopAfter'/>
      <separator/>
      <menuitem action='AddBookmark'/>
      <menuitem action='EditBookmarks'/>
      <separator/>
      <menuitem action='EditTags'/>
      <menuitem action='Information'/>
      <separator/>
      <menuitem action='Jump'/>
    </menu>
    <menu action='View'>
      <menuitem action='SongList'/>
      <menuitem action='Queue'/>
      <separator/>
      %(views)s
    </menu>
    <menu action='Help'>
      <menuitem action='OnlineHelp'/>
      <menuitem action='SearchHelp'/>
      <menuitem action='About'/>
      %(debug)s
    </menu>
  </menubar>
</ui>"""

try:
    ENCODING = locale.getpreferredencoding()
except locale.Error:
    ENCODING = "utf-8"
else:
    # python on macports can return a bugs result (empty string)
    try:
        u"".encode(ENCODING)
    except LookupError:
        ENCODING = "utf-8"

# http://developer.gnome.org/doc/API/2.0/glib/glib-running.html
if "G_FILENAME_ENCODING" in os.environ:
    FSCODING = os.environ["G_FILENAME_ENCODING"].split(",")[0]
    if FSCODING == "@locale":
        FSCODING = ENCODING
elif "G_BROKEN_FILENAMES" in os.environ:
    FSCODING = ENCODING
else:
    FSCODING = "utf-8"

del(os)
del(locale)

"""
Provide tools for ClarityNow Custom Context Menus

Name:        ccmtools.py
Description: Provide tools for ClarityNow Custom Context Menus
Author:      Doug Schafer
Copyright:   Copyright (C) 2020 Dell Inc. or its subsidiaries
Version:     1.8
Date:        June 6, 2015

"""

from __future__ import print_function # use Python 3 printing
# Changelog
#   v1.0 2014-05-29 initial version D.S.
#   v1.1 2014-06-03 add config file parsing
#   v1.2 2014-06-25 many corrections, Unicode, sent to SPE/David Deelo before renaming
#   v1.3 2014-06-27 several Unicode corrections
#   v1.4 2014-07-24 added syslog facility support
#   v1.5 2014-09-17 backwards compatibility with Python 2.6
#   v1.6 2015-02-26 tab correction, replace commas with HTML encoding (&#44;), improved facility
#   v1.7 2015-04-02 corrected error in one-to-many comment for ServerMap, added Unicode fix for mountFP in ServerMap
#   v1.8 2015-06-03 adapt ServerMap to accept str or unicode

VERSION = 1.8
NAME = "ccmtools.py"

import ConfigParser
import cgi
import codecs
import os.path
from StringIO import StringIO
import sys
import syslog

CNUSER = "root"
CNPASS = ""
CREDENTIALS_FILE = "credentials.txt"
CONFIG_FOLDER = "/usr/local/claritynow/etc"
GENERAL_FILE = "cn-scripts.cfg"
CLIENTMAP = '/usr/local/claritynow/etc/clientmap.cfg'
KNEE_BYTE = 1000000 # beyond this many bytes the html form slows down nonlinearly
KNEE_LINE = 50000 # beyond this many lines the html form slows down nonlinearly
NV = "{NAME} v{VERSION}".format(**locals())

# Unwrap code from Andrew "kondor" Sichevoi
def unquote(s):
        QUOTE_SYMBOLS = ('"', "'")
        for quote in QUOTE_SYMBOLS:
            if s.startswith(quote) and s.endswith(quote):
                return s.strip(quote)
        return s

class SafeConfigParserDestupidified (ConfigParser.SafeConfigParser):
    """
    Extend SafeConfigParser to remove header requirement
    """

    def readAddSect (self, filenames):
        """Read a list of files, adding initial section header"""

        for filename in filenames:
            try:
                self.readfp(
                    StringIO(u'[pseudosection]\n{0}'.format(open(filename).read())) )
                    # do not include the filename attribute, as that breaks ConfigParser
            except IOError as e:
                if not e.errno == 2: # missing files are OK
                    raise
                #else:
                #    print (filename, 'not found')

class CcmConfig:
    """
    Read in Clarity CCM script configuration

    Ident is the name of the logged CN operation, such as cn_logger
    """

    def __init__ (self, scriptFilePath, ident):
        self.cfg = SafeConfigParserDestupidified()
        self.cfg.add_section(u'pseudosection')
        self.cfg.set(u'pseudosection', u'cnuser', CNUSER)
        self.cfg.set(u'pseudosection', u'cnpass', CNPASS)
        self.cfg.add_section(ident)
        self.cfg.readAddSect([
            os.path.join(CONFIG_FOLDER, CREDENTIALS_FILE), # generic
            os.path.join(scriptFilePath, CREDENTIALS_FILE),
            os.path.join(CONFIG_FOLDER, GENERAL_FILE),
            os.path.join(CONFIG_FOLDER, u'%s.cfg' % ident)  # specific
            ])
        self.ident = ident

    def getCredentials (self):
        """Read credentials from config files"""
        username = unquote(self.cfg.get(u'pseudosection', u'cnuser'))
        password = unquote(self.cfg.get(u'pseudosection', u'cnpass'))
        return username, password

    def get (self, option):
        """Get from default section"""
        try:
            return unquote(self.cfg.get(u'pseudosection', option))
        except ConfigParser.NoOptionError:
            return None

    def getFromIdent (self, option):
        """Get from ident (app) section"""
        try:
            return unquote(self.cfg.get(self.ident, option))
        except ConfigParser.NoOptionError:
            return None

    def dump(self):
        for section in self.cfg.sections():
            print (section)
            for option in self.cfg.options(section):
                print ('  ', option, '=', self.cfg.get(section, option))

class CcmForm:
    """Manage ClarityNow interactive forms"""

    def __init__ (self, api, guitoken, screenX=1024, screenY=768):
        self.api = api
        self.vertPix = screenY
        # Correct for dual monitor as one virtual monitor
        if screenX > 2*screenY:
            self.horizPix = screenX/2
        else:
            self.horizPix = screenX
        self.guitoken = guitoken

class TextView:
    """Manage view of a specific file"""

    def __init__ (self, form, textFilePath):
        self.form = form
        self.textFilePath = textFilePath
        self.lastLine = 0 # last line read of file
        self.lastByte = 0 # file position of last byte read
        self.pageList = [0] # starting lines for prior pages

    def dialog (self, resumeLine=0):
        """Show portion of text file to user"""
        formX = min (self.form.horizPix-80, 1600)
        formY = min (self.form.vertPix-80, 1200)
        if resumeLine > self.pageList[-1]:
            self.pageList.append(resumeLine)
        longest = 0 # longest text line
        infoLines = 1 # count of non-file lines
        fileLine = 0 # current file position (line)
        fileByte = 0
        displayLines = 0 # count of displayed lines
        displayBytes = 0
        fileListing = u'<pre>'
        fileBegin = (resumeLine == 0)
        try:
            with open(self.textFilePath) as f:
                fsize = os.fstat(f.fileno()).st_size
                seekLine = False
                if resumeLine != 0:
                    if self.lastLine == resumeLine:
                        f.seek(self.lastByte)
                        fileLine = self.lastLine
                        fileByte = self.lastByte
                    else:
                        seekLine = True
                for line in f:
                    linelen = len(line)
                    fileLine += 1
                    fileByte += linelen
                    if seekLine and fileLine < resumeLine:
                        continue
                    fileListing += cgi.escape(line.decode('UTF-8'))
                    longest = max(linelen,longest)
                    displayLines += 1
                    displayBytes += linelen
                    if displayBytes >= KNEE_BYTE or displayLines >= KNEE_LINE:
                        break
                fileEnd = True
                for line in f: # if read works, not at end
                    fileEnd = False
                    break
        except IOError: # don't error if no file yet
            fileListing += 'file could not be read'
            fsize = 0
            fileEnd = True
        fileListing += '</pre>'

        self.lastLine = fileLine
        self.lastByte = fileByte
        if fsize > 0:
            firstPercent = (fileByte - displayBytes) * 100 / fsize # file position of first displayed byte
            lastPercent = fileByte  * 100 / fsize # file position of next displayed byte
        else:
            firstPercent = lastPercent = 0
        if lastPercent == 100 and not fileEnd:
            lastPercent = 99

        # Creat navigation bar
        # Prev | Line 1 to 50000 | Next | Close
        #         0% to 35%
        longest = max(45, longest) # nav bar appx width in <pre> chars
        form  = u'<form action="submit_action" method="get">'
        form  += '<table><tr>'
        form  += '<td width="80">'
        if not fileBegin:
            form += '<input type="submit" value="Prev" name="result" />'
        form += ('<td width="160"><center>' +
                 'Line {firstLine} to {lastLine}<br>' +
                 '{firstPercent}% to {lastPercent}%' +
                 '</center>').format(
                    firstLine=resumeLine+1, lastLine=fileLine,
                    firstPercent=firstPercent, lastPercent=lastPercent)
        form  += '<td width="80">'
        if not fileEnd:
            form += '<input type="submit" value="Next" name="result" />'
        form += '<td width="80"><input type="submit" value="Close" name="result" />'
        form += '</table></form>'

        html = form
        html += '<pre>'
        html += self.textFilePath + '\n'
        longest = max(len(self.textFilePath), longest)
        infoLines += 1
        html += '</pre><hr>'
        html += fileListing
        html += '<hr>'
        html += form

        horizPix = min(90 + 7 * longest, formX)
        vertPix = min(170 + 17 * (displayLines + infoLines), formY) # 17 on Windows, wider than Linux
        try:
            action, query_dict = self.form.api.showHtmlForm(
                self.form.guitoken, horizPix, vertPix, html.encode('UTF-8'))
        except StandardError:
            if 'The html form failed to provide a result' in str(sys.exc_info()[1].args):
                exit() # Block error if the user simply clicked the dialog's close icon
            else:
                print ('StandardError with text: ')
                print (repr(sys.exc_info()[1].args))
                print (sys.exc_info())
                exit(1)

        if action == "submit_action":
            if query_dict['result'] == ['Close']:
                return 'Close'
            if query_dict['result'] == ['Next']:
                return self.lastLine
            if query_dict['result'] == ['Prev']:
                firstLine = fileLine - displayLines
                for line in reversed(self.pageList):
                    if line < firstLine:
                        return line
            else:
                print ("Unexpected form response")
                exit(1)


def simpleLogView (api, guitoken, log, maxX=1600, maxY=1200):
    # provide a paging textView of the logging system's current log file
    # assuming recommended configuration is followed
    form = CcmForm(api, guitoken, screenX=maxX, screenY=maxY)
    textView = TextView(form, log.recommendedLogfile)
    nextLine = textView.dialog()
    while nextLine is not None and nextLine != 'Close':
        nextLine = textView.dialog(resumeLine=nextLine)
    exit()

class CcmLog:
    """Standardize ClarityNow CCM logging"""

    # coreTuple such as ('Bob', '192.168.122.1')
    # messageTuple such as ('"/home/data"', 'deleted')
    # do not include descriptions ('user Bob',...) as it hurts SS import

    def __init__ (self, ident, coreTuple, debug=False, facility=syslog.LOG_USER):
        if debug:
            logUpTo=syslog.LOG_DEBUG
        else:
            logUpTo=syslog.LOG_INFO
        if facility is None:
            facility = syslog.LOG_USER
        elif facility == "local0":
            facility = syslog.LOG_LOCAL0
        elif facility == "local1":
            facility = syslog.LOG_LOCAL1
        elif facility == "local2":
            facility = syslog.LOG_LOCAL2
        elif facility == "local3":
            facility = syslog.LOG_LOCAL3
        elif facility == "local4":
            facility = syslog.LOG_LOCAL4
        elif facility == "local5":
            facility = syslog.LOG_LOCAL5
        elif facility == "local6":
            facility = syslog.LOG_LOCAL6
        elif facility == "local7":
            facility = syslog.LOG_LOCAL7
        syslog.openlog(ident.encode('UTF-8'), syslog.LOG_PID, facility)
        syslog.setlogmask(syslog.LOG_UPTO(logUpTo))
        self.coretextList = [unicode(x).replace(u',', u'&#44;') for x in coreTuple]
        self.recommendedLogfile = u'/var/log/claritynow/{0}.log'.format(ident)

    def log (self, messageTuple, level=syslog.LOG_INFO, stdout=False):
        if level == syslog.LOG_INFO:
            levelName = 'INFO: '
        elif level == syslog.LOG_DEBUG:
            levelName = 'DEBUG: '
        elif level == syslog.LOG_WARNING:
            levelName = 'WARNING: '
        elif level == syslog.LOG_ERR:
            levelName = 'ERROR: '
        else:
            levelName = u'{level}: '.format(level=level)
        messageList =  [unicode(x).replace(u',', u'&#44;') for x in messageTuple]
        foo = levelName + u', '.join(self.coretextList + messageList)
        syslog.syslog(level, foo.encode('UTF-8'))

    def info (self, messageTuple, stdout=False):
        self.log(messageTuple, level=syslog.LOG_INFO, stdout=stdout)

    def debug (self, messageTuple, stdout=True):
        self.log(messageTuple, level=syslog.LOG_DEBUG, stdout=stdout)

    def error (self, messageTuple, stdout=True):
        self.log(messageTuple, level=syslog.LOG_ERR, stdout=stdout)

    def warning (self, messageTuple, stdout=True):
        self.log(messageTuple, level=syslog.LOG_WARNING, stdout=stdout)

    def close (self):
        syslog.closelog()

class ServerMap:
    """Translate paths using ClarityNow's volume configuration"""

    """ Note! physical to virtual could be set up many-to-one!""" #####################
    # Consider instead validating %ppath vs %vpath, creating map with that
    # Linux servers only. Examples:
    #     virtual         physical
    #     root            /
    #     test1           /mnt/test
    #     test2           /mnt/test/
    def __init__ (self,api):
        self.serverMapNM = []
        self.serverMapMN = []
        for vol in api.getVolumes():
            if vol.mount.endswith('/'):
                mount = vol.mount
            else:
                mount = vol.mount + '/'
            name = u'/' + vol.name + '/'
            self.serverMapNM.append((name, mount))
            self.serverMapMN.append((mount, name))
        self.serverMapNM.sort(key = lambda nm: len(nm[0]), reverse=True)
        self.serverMapMN.sort(key = lambda mn: len(mn[0]), reverse=True)

    def getPfilepath (self, nameFP): #nameFP should be unicode
        if type(nameFP) is not unicode:
            nameFP = unicode(nameFP, encoding="UTF-8")
        # print (nameFP,self.serverMapNM)
        for n,m in self.serverMapNM:
            # print (n,m)
            if nameFP.startswith(n):
                return m + nameFP[len(n):]
        raise LookupError('Cannot convert path.')
    def getVfilepath (self, mountFP):
        if type(mountFP) is not unicode:
            mountFP = unicode(mountFP, encoding="UTF-8")
        for m,n in self.serverMapMN:
            if mountFP.startswith(m):
                return n + mountFP[len(m):]
        raise LookupError('Cannot convert path.')

class ClientMap:
    """Translate paths using ClarityNow's client map config file"""

    """Clientmap file may have various maps, but only Linux lookups supported"""
    def __init__ (self,mapname):
        self.groups = {}
        group = None
        with codecs.open(CLIENTMAP, 'r', encoding='UTF-8') as mf:
            mapfile = mf.readlines()
        try:
            for line in mapfile:
                line = line.strip()
                if line.lower().startswith('group'):
                    group = line.split()[1]
                    self.groups[group]=[]
                elif line.startswith('/'):
                    bits = line.split(':',1)
                    self.groups[group].append((
                        bits[0].strip().rstrip('/') + '/',
                        bits[1].strip().rstrip('/') + '/'))
        except:
            print (u"Invalid client map file {0}".format(CLIENTMAP))
            raise
        if not mapname in self.groups:
            raise LookupError(u'group {0} not in {1}'.format(mapname, CLIENTMAP))
        self.mapNM = []
        self.mapMN = []
        for name, mount in self.groups[mapname]:
            self.mapNM.append((name, mount))
            self.mapMN.append((mount, name))
        self.mapNM.sort(key = lambda nm: len(nm[0]), reverse=True)
        self.mapMN.sort(key = lambda mn: len(mn[0]), reverse=True)

    def getPfilepath (self, nameFP):
        """Look up client physical path given virtual path"""
        for n,m in self.mapNM:
            if nameFP.startswith(n):
                return m + nameFP[len(n):]
        raise LookupError('Cannot convert path.')
    def getVfilepath (self, mountFP):
        """Look up virtual path given client physical path"""
        for m,n in self.mapMN:
            if mountFP.startswith(m):
                return n + mountFP[len(m):]
        raise LookupError('Cannot convert path.')

    def dump (self):
        for key in self.groups:
            print (key)
            print (self.groups[key])

def getTopNewInDB (api, vpath):
    """Inspect virtual path, return shortest path with new element"""

    """Use to find best scan target"""
    oldvpath = vpath
    while not vpath == u'/':
        try:
            api.getFolderAttributes(vpath)
        except StandardError as e:
            if not 'path not in db' in e.content:
                raise
            oldvpath = vpath
            vpath = os.path.split(vpath.rstrip('/'))[0]
            continue
        return oldvpath
    return u'/'

def sizeof_fmt_10(num):
    """Return human-readable size, powers of 10"""
    """From Fred Cirera on StackOverflow"""
    for x in ['bytes','kB','MB','GB']:
        if num < 1000.0 and num > -1000.0:
            if x == 'bytes':
                return "%d %s" % (num, x)
            else:
                return "%3.2f %s" % (num, x)
        num /= 1000.0
    return "%3.2f %s" % (num, 'TB')

def sizeof_fmt_2(num):
    """Return human-readable size, powers of 2"""
    """From Fred Cirera on StackOverflow"""
    for x in ['bytes','KiB','MiB','GiB']:
        if num < 1024.0 and num > -1024.0:
            if x == 'bytes':
                return "%d %s" % (num, x)
            else:
                return "%4.2f %s" % (num, x)
        num /= 1024.0
    return "%4.2f %s" % (num, 'TiB')

def getPaths(pfile, version="script"):
    """Get list of selected paths from CN's path file"""
    try:
        f = codecs.open(pfile, 'r', encoding='UTF-8')
        paths = sorted([line.rstrip() for line in f], key=unicode.lower)
    except:
        print(u"\nError: {ver} expected valid path file as argument\n".format(ver=version))
        raise
    return paths

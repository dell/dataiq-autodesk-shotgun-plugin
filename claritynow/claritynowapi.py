import platform
import cgi
import sys
import time
import warnings
import uuid
import os.path

SERVER_VERSION = "2.11.0-9"

python_version = platform.python_version_tuple()
major = int(python_version[0])
minor = int(python_version[1])
if major == 2:
    if minor < 5:
        import simplejson
    else:
        import json as simplejson
    import httplib2v2 as httplib2
    import urlparse
elif major == 3:
    import json as simplejson
    import httplib2v3 as httplib2
    import urllib.parse as urlparse
else:
    raise StandardError ("unsupported Python version")
        
import base64

# strips illegal characters from volume names, scan group names, tag names, category names and user logins
def stripIllegalChars(self, text):
    if text is None:
        return None
    result = ''
    for c in text:
        if c.isalnum() or c == '-' or c == '_' or c == ' ':
            result += c
    return result

class JsonContext:
    def __init__ (self, obj, jsonDict, isEncode):
        self.obj = obj
        self.jsonDict = jsonDict
        self.isEncode = isEncode

    def codeInt (self, name):
        if self.isEncode:
            self.jsonDict[name] = getattr (self.obj, name)
        else:
            setattr (self.obj, name, self.jsonDict.get (name, getattr (self.obj, name)))
            
    def codeLong (self, name):
        if self.isEncode:
            self.jsonDict[name] = getattr (self.obj, name)
        else:
            setattr (self.obj, name, self.jsonDict.get (name, getattr (self.obj, name)))

    def codeDouble (self, name):
        if self.isEncode:
            self.jsonDict[name] = getattr (self.obj, name)
        else:
            setattr (self.obj, name, self.jsonDict.get (name, getattr (self.obj, name)))
            
    def codeString (self, name):
        if self.isEncode:
            self.jsonDict[name] = getattr (self.obj, name)
        else:
            setattr (self.obj, name, self.jsonDict.get (name, getattr (self.obj, name)))

    def codeBool (self, name):
        if self.isEncode:
            self.jsonDict[name] = getattr (self.obj, name)
        else:
            setattr (self.obj, name, self.jsonDict.get (name, getattr (self.obj, name)))

    def codeArrayOfBool (self, name):
        if self.isEncode:
            self.jsonDict[name] = getattr (self.obj, name)
        else:
            setattr (self.obj, name, self.jsonDict.get (name, getattr (self.obj, name)))

    def codeArrayOfLongs (self, name):
        if self.isEncode:
            self.jsonDict[name] = getattr (self.obj, name)
        else:
            setattr (self.obj, name, self.jsonDict.get (name, getattr (self.obj, name)))

    def codeArrayOfStrings (self, name):
        if self.isEncode:
            self.jsonDict[name] = getattr (self.obj, name)
        else:
            setattr (self.obj, name, self.jsonDict.get (name, getattr (self.obj, name)))

    # Java keeps time in 1000ms increments, Python in seconds as a float
    def codeDate (self, name):
        if self.isEncode:
            date = getattr (self.obj, name)
            if date == None:
                self.jsonDict[name] = None
            else:
                if major >= 3:
                    self.jsonDict[name] = int(date*1000.0)
                else:
                    self.jsonDict[name] = long(date*1000.0)
        else:
            if name in self.jsonDict:
                date = self.jsonDict[name]
                if date == None:
                    setattr (self.obj, name, None)
                else:
                    setattr (self.obj, name, date/1000.0)
            else:
                pass

    def codeObject (self, objClass, name):
        if self.isEncode:
            o = getattr (self.obj, name)
            if o == None:
                self.jsonDict[name] = None
            else:
                context = JsonContext (o, {}, True)
                o.jsonCode (context)
                self.jsonDict[name] = context.jsonDict
        else:
            json = self.jsonDict.get (name)
            if json == None:
                setattr (self.obj, name, None)
            else:
                o = objClass()
                context = JsonContext (o, json, False)
                o.jsonCode (context)
                setattr (self.obj, name, o)

    def codePolymorphicObject (self, classes, name):
        if self.isEncode:
            o = getattr (self.obj, name)
            if o == None:
                self.jsonDict[name] = None
            else:
                context = JsonContext (o, {}, True)
                o.jsonCode (context)
                for type,constructor in classes:
                    if isinstance(o, constructor):
                        context.jsonDict['objectType'] = type
                self.jsonDict[name] = context.jsonDict
        else:
            json = self.jsonDict.get (name)
            if json == None:
                setattr (self.obj, name, None)
            else:
                result= []
                objectType = json['objectType']
                for type,constructor in classes:
                    if type == objectType:
                        o = constructor()
                        context = JsonContext (o, json, False)
                        o.jsonCode (context)
                        result.append (o)
                setattr (self.obj, name, result)

    def codeListOfObjects (self, constructor, name):
        if self.isEncode:
            o = getattr (self.obj, name)
            if o == None:
                self.jsonDict[name] = None
            else:
                result = []
                for entry in o:
                    context = JsonContext (entry, {}, True)
                    entry.jsonCode (context)
                    result.append (context.jsonDict)
                self.jsonDict[name] = result
        else:
            json = self.jsonDict.get (name)
            if json == None:
                setattr (self.obj, name, None)
            else:
                result= []
                for entry in json:
                    o = constructor()
                    context = JsonContext (o, entry, False)
                    o.jsonCode (context)
                    result.append (o)
                setattr (self.obj, name, result)
                
    def codeListOfPolymorphicObjects (self, classes, name):
        if self.isEncode:
            o = getattr (self.obj, name)
            if o == None:
                self.jsonDict[name] = None
            else:
                result = []
                for entry in o:
                    context = JsonContext (entry, {}, True)
                    entry.jsonCode (context)
                    for type,constructor in classes:
                        if isinstance(entry, constructor):
                            context.jsonDict['objectType'] = type
                    result.append (context.jsonDict)
                self.jsonDict[name] = result
        else:
            json = self.jsonDict.get (name)
            if json == None:
                setattr (self.obj, name, None)
            else:
                result= []
                for entry in json:
                    objectType = entry['objectType']
                    for type,constructor in classes:
                        if type == objectType:
                            o = constructor()
                            context = JsonContext (o, entry, False)
                            o.jsonCode (context)
                            result.append (o)
                setattr (self.obj, name, result)

class CNObject:
    def __init__ (self):
        self.id = -1
        self.changeCount = -1

    def jsonCode (self, context):
        context.codeInt('id')
        context.codeInt('changeCount')

class ScannableData (CNObject):
    # scan type enum
    SCAN_AT = "SCAN_AT"
    SCAN_INTERVAL = "SCAN_INTERVAL"
    
    def __init__ (self):
        CNObject.__init__ (self)
        self.slowdownPercent = 0
        self.scheduledScanThreads = 1
        self.manualScanThreads = 1

        self.eventTimeMinutes = 0
        self.eventIntervalMinutes = 60
        self.eventType = ScannableData.SCAN_AT
        self.eventDays = [True,True,True,True,True,True,True]

    def jsonCode (self, context):
        CNObject.jsonCode (self, context)
        context.codeInt('slowdownPercent')
        context.codeInt('scheduledScanThreads')
        context.codeInt('manualScanThreads')
        context.codeInt('eventTimeMinutes')
        context.codeInt('eventIntervalMinutes')
        context.codeString('eventType')
        context.codeArrayOfBool('eventDays')

class FileSystemSimConfigData(object):
    # Note: This class should be considered preliminary, subject to
    # change without notice.
    TYPE_ABC_10_10_10_10k = "TYPE_ABC_10_10_10_10k"
    TYPE_ABC_10_10_10_10_1k = "TYPE_ABC_10_10_10_10_1k"
    TYPE_ABC_10_10_10_10_10_100 = "TYPE_ABC_10_10_10_10_10_100"
    TYPE_123_10_10_10_10k = "TYPE_123_10_10_10_10k"
    TYPE_123_10_10_10_10_1k = "TYPE_123_10_10_10_10_1k"
    TYPE_123_10_10_10_10_10_100 = "TYPE_123_10_10_10_10_10_100"
    
    def __init__ (self):
        self.simType = FileSystemSimConfigData.TYPE_123_10_10_10_10k

    def jsonCode (self, context):
        context.codeString('simType')

class FileSystemS3ConfigData(object):
    """
    Example usage:

    api = claritynowapi.ClarityNowConnection ('root','','localhost')

    fs = claritynowapi.VolumeData ('s3vol', '/')
    fs.fileSystemType = claritynowapi.VolumeData.TYPE_S3
    fs.fsS3ConfigData.bucketName = "somes3bucket"
    fs.fsS3ConfigData.region = "us-west-1"
    id = api.addVolume (fs)
    """

    def __init__ (self):
        self.bucketName = ""
        self.region = "" # as retrieved from the getBucketLocation API

    def jsonCode (self, context):
        context.codeString('bucketName')
        context.codeString('region')

class VolumeData (ScannableData):
    # hard link enum
    COUNT_ALL = "COUNT_ALL"
    COUNT_PRO_RATED = "COUNT_PRO_RATED"

    # file system type enum
    TYPE_VFS = "TYPE_VFS"
    TYPE_SIMULATED = "TYPE_SIMULATED"
    TYPE_NFS = "TYPE_NFS"
    TYPE_S3 = "TYPE_S3"
    
    
    def __init__ (self, name=None, mount = ''):
        ScannableData.__init__ (self)
        self.fileSystemType = VolumeData.TYPE_VFS
        self.name = name
        self.mount = mount
        self.subdir = ''
        self.hardLinkHandling = VolumeData.COUNT_ALL
        self.scanExclusionPattern = ''
        self.disableFolderLoopDetection = False
        self.fsSimConfigData = FileSystemSimConfigData()
        self.fsS3ConfigData = FileSystemS3ConfigData()

    def jsonCode (self, context):
        ScannableData.jsonCode (self, context)
        context.codeString('fileSystemType')
        context.codeString('name')
        context.codeString('mount')
        context.codeString('subdir')
        context.codeString('hardLinkHandling')
        context.codeString('scanExclusionPattern')
        context.codeBool('disableFolderLoopDetection')
        context.codeObject(FileSystemSimConfigData, 'fsSimConfigData')
        context.codeObject(FileSystemS3ConfigData, 'fsS3ConfigData')

class ScanGroupData (ScannableData):
    def __init__ (self, name=None):
        ScannableData.__init__ (self)
        self.name = name

    def jsonCode (self, context):
        ScannableData.jsonCode (self, context)
        context.codeString('name')
        
class TagCategoryData (CNObject):
    # hard link enum
    COUNT_ALL = "COUNT_ALL"
    COUNT_PRO_RATED = "COUNT_PRO_RATED"
    
    def __init__ (self, name=None, mandatory = False):
        CNObject.__init__ (self)
        self.name = name
        self.mandatory = mandatory

    def jsonCode (self, context):
        CNObject.jsonCode (self, context)
        context.codeString('name')
        context.codeBool('mandatory')

class TagData (CNObject):
    def __init__ (self, name=None, expiration = None, sizeLimit = None):
        CNObject.__init__ (self)
        self.name = name
        self.expiration = expiration
        self.sizeLimit = sizeLimit

    def jsonCode (self, context):
        CNObject.jsonCode (self, context)
        context.codeString('name')
        context.codeDate('expiration')
        context.codeLong('sizeLimit')

class FolderAttributesData (CNObject):
    def __init__ (self):
        CNObject.__init__ (self)
        self.sizeLimit = None
        self.expiration = None
        self.ignoreErrors = False

    def jsonCode (self, context):
        CNObject.jsonCode (self, context)
        context.codeLong('sizeLimit')
        context.codeDate('expiration')
        context.codeBool('ignoreErrors')

class FileInfo:
    # file type enum
    FILE = "FILE"
    FOLDER = "FOLDER"
    SEQUENCE = "SEQUENCE"
    FILE_IN_SEQUENCE = "FILE_IN_SEQUENCE"
    
    def __init__ (self):
        self.fileType = None
        self.name = None
        self.fileCount = 0
        self.dirCount = 0
        self.ctime = None
        self.mtime = None
        self.atime = None
        self.cumulativeCTime = None
        self.cumulativeMTime = None
        self.cumulativeATime = None
        self.size = 0
        self.lastScanned = None
        self.path = None
        self.errorCountInChildren = 0
        self.uid = None
        self.gid = None

        # only populated for sequences
        self.seqPrefix = None
        self.seqSuffix = None
        self.seqNDigits = 0
        self.seqFrom = 0
        self.seqTo = 0

    def jsonCode (self, context):
        context.codeString('fileType')
        context.codeString('name')
        context.codeLong('fileCount')
        context.codeLong('dirCount')
        context.codeDate('ctime')
        context.codeDate('mtime')
        context.codeDate('atime')
        context.codeDate('cumulativeCTime')
        context.codeDate('cumulativeMTime')
        context.codeDate('cumulativeATime')
        context.codeLong('size')
        context.codeString('path')
        context.codeDate('lastScanned')
        context.codeString('seqPrefix')
        context.codeString('seqSuffix')
        context.codeLong('seqNDigits')
        context.codeLong('seqFrom')
        context.codeLong('seqTo')
        context.codeLong('errorCountInChildren')
        context.codeLong('uid')
        context.codeLong('gid')
        if not context.isEncode:
            # Populate deprecated fields for backward compatibility:
            self.lastModified = self.mtime
            self.cumulativeLastModified = self.cumulativeMTime

class FastStatRequest:
    # ResultType enum
    SUM = "SUM"
    BY_TAGGED_STATE = "BY_TAGGED_STATE"
    BY_EXPIRATION_STATE = "BY_EXPIRATION_STATE"
    BY_LIMIT_STATE = "BY_LIMIT_STATE"
    ALL_PATHS = "ALL_PATHS"
    TAGGED_PATHS = "TAGGED_PATHS"
    UNTAGGED_PATHS = "UNTAGGED_PATHS"
    EXPIRED_PATHS = "EXPIRED_PATHS"
    UNEXPIRED_PATHS = "UNEXPIRED_PATHS"
    ETERNAL_PATHS = "ETERNAL_PATHS"
    OVERAGE_PATHS = "OVERAGE_PATHS"
    RESERVED_PATHS = "RESERVED_PATHS"
    UNLIMITED_PATHS = "UNLIMITED_PATHS"
    USED_PATHS = "USED_PATHS"
    NOT_CATEGORY_PATHS = "NOT_CATEGORY_PATHS"
    BY_VOLUMES = "BY_VOLUMES"
    BY_CATEGORY = "BY_CATEGORY"

    def __init__ (self):
        self.resultType = FastStatRequest.SUM
        self.requests = []
        self.groupByParameter = None
        self.caption = None # populated by server
        self.returnCostPerWeek = False # deprecated, cost always returned

    def jsonCode (self, context):
        if self.returnCostPerWeek:
            raise StandardError ("Obsolete flag FastStatRequest.returnCostPerWeek used. Code must be refactored. See release notes for 2.5.2-1 for details.")
        context.codeString('resultType')
        context.codeListOfObjects (SubRequest, 'requests')
        context.codePolymorphicObject ([(
            "dfx.server.struct.FastStatRequest$GroupByCategory", GroupByCategory)], "groupByParameter")
        context.codeString ("caption")

class GroupByCategory:
    def __init__ (self, categoryId=None):
        self.categoryId = categoryId

    def jsonCode (self, context):
        context.codeInt ('categoryId')

class SubRequest:
    def __init__ (self):
        self.name = ""
        self.filters = []
        self.results = None

    def jsonCode (self, context):
        context.codeString ("name")
        context.codeListOfPolymorphicObjects ([
            ("dfx.server.struct.FastStatRequest$VolumeFilter", VolumeFilter),
            ("dfx.server.struct.FastStatRequest$TagFilter", TagFilter),
            ("dfx.server.struct.FastStatRequest$ExpandableCategoryFilter", ExpandableCategoryFilter),
            ("dfx.server.struct.FastStatRequest$ExpandableVolumesFilter", ExpandableVolumesFilter),
            ], "filters")
        context.codeListOfPolymorphicObjects ([
            ("dfx.server.struct.FastStatRequest$ValueResult", ValueResult),
            ("dfx.server.struct.FastStatRequest$PathResult", PathResult)], "results")

    # convenience functions
    def addVolumeFilter (self, volumeName):
        filter = VolumeFilter()
        filter.volumes = [volumeName]
        self.filters.append (filter)

    def addTagFilter (self, tagId):
        filter = TagFilter ([tagId])
        self.filters.append (filter)
        
class VolumeFilter:
    def __init__ (self):
        self.volumes = []

    def jsonCode (self, context):
        context.codeArrayOfStrings ("volumes")

class TagFilter:
    def __init__ (self, tags=[]):
        self.tags = tags

    def jsonCode (self, context):
        context.codeArrayOfLongs ("tags")

# special filter that is expanded into separate requests
# for each tag in the category
# NOTE: This must be the first filter in the filter list.
class ExpandableCategoryFilter:
    def __init__ (self, categoryId):
        self.categoryId = categoryId

    def jsonCode (self, context):
        context.codeLong ("categoryId")

# special filter that is expanded into separate volumes
# NOTE: This must be the first filter in the filter list.
class ExpandableVolumesFilter:
    def __init__ (self):
        pass

    def jsonCode (self, context):
        pass

class ValueResult:
    def __init__ (self):
        self.name = None
        self.bytes = None
        self.cost = None

    def jsonCode (self, context):
        context.codeString ("name")
        context.codeInt ("bytes")
        context.codeDouble ("cost")
        self.value = self.bytes

class PathResult:
    def __init__ (self):
        self.paths = []

    def jsonCode (self, context):
        context.codeListOfObjects (PathInfo, "paths")

class PathInfo:
    def __init__ (self):
        self.path = None
        self.bytes = None
        self.cost = None

    def jsonCode (self, context):
        context.codeString ("path")
        context.codeInt ("bytes")
        context.codeDouble ("cost")
        self.size = self.bytes
        
        context.codeObject(FileInfo, "info")


# note: ClarityNowConnection objects are not thread-safe. However, multiple
#       instances can safely run in different threads.
class ClarityNowConnection(object):
    def __init__ (self, username, password, hostname, port=443, ignore_server_version=False):
        if major >= 3:
            self.authorization = base64.b64encode ((username+":"+password).encode())
            self.authorization = self.authorization.decode()
        else:
            self.authorization = base64.b64encode (username+":"+password)
        self.pool = httplib2.Http() # urllib3.connection_from_url("https://%s:%d" % (hostname, port))
        self.url_base = "https://%s:%d" % (hostname, port)

        if not ignore_server_version:
            server_version = self.getServerVersion()
            if server_version != SERVER_VERSION:
                raise StandardError(
                   "Server is version %s, but claritynowapi is at %s" % (
                    server_version, SERVER_VERSION))

    def jsonQuery (self, method, address, jsonInput=None):
        content = self.stringQuery(method, address, jsonInput)
        return simplejson.loads (content)

    def stringQuery (self, method, address, textInput):
        args = {'Authorization': 'Basic '+self.authorization}
        content = ""
        try:
            resp,content = self.pool.request(self.url_base+address, headers=args, body=textInput)
            if major >= 3:
                content = content.decode() # this is lame
            status = int(resp['status'])
            if status != 200:
                if status == 500:
                    # attempt to find underlying Java exception in returned html
                    p = content.find('<pre>')
                    if p >= 0:
                        lines = content[p+5:].splitlines()
                        if major >= 3:
                            error = Exception (lines[0])
                        else:
                            error = StandardError (lines[0])
                    else:
                        if major >= 3:
                            error = Exception ("server returned unexpected response %d" % (status))
                        else:
                            error = StandardError ("server returned unexpected response %d" % (status))
                else:
                    if major >= 3:
                        error = Exception ("server returned unexpected response %d" % (status))
                    else:
                        error = StandardError ("server returned unexpected response %d" % (status))
                error.content = content;
                raise error
        except Exception:
            # Tricky Python version compatibility hack. See
            # http://stackoverflow.com/questions/12682558/how-to-write-an-exception-catching-code-works-in-python2-4-to-python3
            t, e = sys.exc_info()[:2]
            
            # customize msg if needed
            willRaise = False
            found = str(e).find('NoneType')
            if found >= 0:
                msg = "Cannot connect to " + self.url_base+address + ". Please check the ClarityNow! server address and port number configuration and its accessibility"
                willRaise = True
            else:
                msg = str(e)
            # will raise as exception or standard depending on python version
            if major >= 3:
                error = Exception (msg)
            else:
                error = StandardError (msg)
            # raise error
            if willRaise or major <3:
                raise error
            else:
                raise
        return content

    def stringQueryWithRespondHeader (self, method, address, textInput):
        args = {'Authorization': 'Basic '+self.authorization}
        content = ""
        try:
            resp,content = self.pool.request(self.url_base+address, headers=args, body=textInput)
            if major >= 3:
                content = content.decode() # this is lame
            status = int(resp['status'])
            if status != 200:
                if status == 500:
                    # attempt to find underlying Java exception in returned html
                    p = content.find('<pre>')
                    if p >= 0:
                        lines = content[p+5:].splitlines()
                        if major >= 3:
                            error = Exception (lines[0])
                        else:
                            error = StandardError (lines[0])
                    else:
                        if major >= 3:
                            error = Exception ("server returned unexpected response %d" % (status))
                        else:
                            error = StandardError ("server returned unexpected response %d" % (status))
                else:
                    if major >= 3:
                        error = Exception ("server returned unexpected response %d" % (status))
                    else:
                        error = StandardError ("server returned unexpected response %d" % (status))
                error.content = content;
                raise error
        except Exception:
            # Tricky Python version compatibility hack. See
            # http://stackoverflow.com/questions/12682558/how-to-write-an-exception-catching-code-works-in-python2-4-to-python3
            t, e = sys.exc_info()[:2]
            
            # customize msg if needed
            willRaise = False
            found = str(e).find('NoneType')
            if found >= 0:
                msg = "Cannot connect to " + self.url_base+address + ". Please check the ClarityNow! server address and port number configuration and its accessibility"
                willRaise = True
            else:
                msg = str(e)
            # will raise as exception or standard depending on python version
            if major >= 3:
                error = Exception (msg)
            else:
                error = StandardError (msg)
            # raise error
            if willRaise or major <3:
                raise error
            else:
                raise
        return content,resp


    def ping (self):
        """ping can be used to benchmark server communication. It
           has no effect."""
        self.jsonQuery ("GET", "/json/ping")

    def getServerVersion (self):
        """retrieves the version of the server."""
        return self.jsonQuery ("GET", "/json/getserverversion")

    def addScanGroup(self, sgData):
        """add a scan group.

           sgData: locally created instance of ScanGroupData
           returns: assigned id of new scan group"""        
        context = JsonContext (sgData, {}, True)
        sgData.jsonCode (context)
        id =  self.jsonQuery ("POST", "/json/addscangroup", simplejson.dumps(context.jsonDict))
        sgData.id = id
        return id

    def editScanGroup(self, sgData):
        """edit a scan group
           sgData: locally created instance of ScanGroupData
           returns: assigned id of new scan group"""
        context = JsonContext (sgData, {}, True)
        sgData.jsonCode (context)
        id =  self.jsonQuery ("POST", "/json/updatescangroup", simplejson.dumps(context.jsonDict))
        sgData.id = id
        return id

    def deleteScanGroup(self, name):
        """delete scan group.

           name: name of the scan group to delete"""
        self.jsonQuery ("GET", "/json/deletescangroup", simplejson.dumps(name))

    def getScanGroups(self):
        """get list of scan groups.

           returns: list of ScanGroupData instances"""        
        result = []
        sgs = self.jsonQuery ("GET", "/json/getscangroups")
        for fs in sgs:
            data = ScanGroupData ()
            context = JsonContext (data, fs, False)
            data.jsonCode (context)
            result.append (data)
        return result

    def getVolumesInScanGroup(self, name):
        """get list of volumes in a scan group.

           returns: list of VolumeData instances"""        
        result = []
        fss = self.jsonQuery ("GET", "/json/getvolumesinscangroup", simplejson.dumps(name))
        for fs in fss:
            data = VolumeData ()
            context = JsonContext (data, fs, False)
            data.jsonCode (context)
            result.append (data)
        return result

    def getVolumes (self):
        """get list of volume configurations.

           returns: list of VolumeData instances"""        
        result = []
        fss = self.jsonQuery ("GET", "/json/getvolumes")
        for fs in fss:
            data = VolumeData ()
            context = JsonContext (data, fs, False)
            data.jsonCode (context)
            result.append (data)
        return result

    def getVolume (self, name):
        """get detail information for a volume configuration by name.

           name: name of the volume to get information for
           returns: instance of VolumeData"""
        result = []
        fs = self.jsonQuery ("GET", "/json/getvolume", simplejson.dumps(name))
        data = VolumeData ()
        context = JsonContext (data, fs, False)
        data.jsonCode (context)
        return data

    def addVolume (self, fsData):
        """add a new volume configuration.

           fsData: locally created instance of VolumeData
           returns: assigned id of new volume"""        
        context = JsonContext (fsData, {}, True)
        fsData.jsonCode (context)
        id =  self.jsonQuery ("POST", "/json/addvolume", simplejson.dumps(context.jsonDict))
        fsData.id = id
        return id

    def addVolumeToScanGroup (self, scanGroupName, fsData):
        """add a new volume configuration.

           fsData: locally created instance of VolumeData
           returns: assigned id of new volume"""        
        context = JsonContext (fsData, {}, True)
        fsData.jsonCode (context)
        id =  self.jsonQuery ("POST", "/json/addvolumetoscangroup", simplejson.dumps([scanGroupName, context.jsonDict]))
        fsData.id = id
        return id

    def deleteVolume (self, id):
        """delete a volume configuration. Note that this does not
           delete the volume or any files on it.

           id: id of the volume to delete"""           
        self.jsonQuery ("POST", "/json/deletevolume", simplejson.dumps(id))

    def changeVolume (self, fsData):
        """change volume configuration.

           fsData: instance of changed VolumeData received from server"""        
        context = JsonContext (fsData, {}, True)
        fsData.jsonCode (context)
        self.jsonQuery ("POST", "/json/changevolume", simplejson.dumps(context.jsonDict))
        fsData.changeCount += 1

    def getTagCategories (self):
        """get list of tag categories.

           returns: list of TagCategoryData instances"""        
        result = []
        categories = self.jsonQuery ("GET", "/json/gettagcategories")
        for cat in categories:
            data = TagCategoryData ()
            context = JsonContext (data, cat, False)
            data.jsonCode (context)
            result.append (data)
        return result

    def getTagCategory (self, categoryName):
        """get category object.

           categoryName: name of the category to get details for
           returns: instance of TagCategoryData"""
        cat = self.jsonQuery ("GET", "/json/gettagcategory", simplejson.dumps(categoryName))
        data = TagCategoryData ()
        context = JsonContext (data, cat, False)
        data.jsonCode (context)
        return data

    def getTags (self, categoryName):
        """get all tags in a category.

           categoryName: name of the category to get tags for
           returns: list of TagData instances"""
        result = []
        tags = self.jsonQuery ("GET", "/json/gettags", simplejson.dumps(categoryName))
        for tag in tags:
            data = TagData ()
            context = JsonContext (data, tag, False)
            data.jsonCode (context)
            result.append (data)
        return result

    def getTag (self, categoryName, tagName):
        """get data for a tag.

           categoryName: name of the category of the tag
           tagName: name of the tag
           returns: TagData instance"""
        result = []
        tag = self.jsonQuery ("GET", "/json/gettag", simplejson.dumps([categoryName, tagName]))
        data = TagData ()
        context = JsonContext (data, tag, False)
        data.jsonCode (context)
        return data

    def addTag (self, categoryName, tagData):
        """add a new tag.

           categoryName: name of the category of the new tag
           tagData: instance of TagData created locally
           returns: assigned id of new tag"""
        context = JsonContext (tagData, {}, True)
        tagData.jsonCode (context)
        id = self.jsonQuery ("POST", "/json/addtag", simplejson.dumps([categoryName, context.jsonDict]))
        tagData.id = id
        return id

    def deleteTag (self, id, force=False):
        """delete a tag.

           id: id of the tag
           force: boolean - set to True to force deletion even if tag
                  is in use"""
        self.jsonQuery ("POST", "/json/deletetag", simplejson.dumps([id,force]))

    def changeTag (self, tagData):
        """change a tag.

           tagData: TagData instance received from server"""
        context = JsonContext (tagData, {}, True)
        tagData.jsonCode (context)
        self.jsonQuery ("POST", "/json/changetag", simplejson.dumps(context.jsonDict))
        tagData.changeCount += 1

    def getImpliedTags (self, categoryName, tagName):
        """Get list of implied tags for a given tag.

           categoryName: name of the category of the parent tag
           tagName: name of the parent tag
           returns: list of TagData instances"""
        result = []
        tags = self.jsonQuery ("GET", "/json/getimpliedtags", simplejson.dumps([categoryName,tagName]))
        for tag in tags:
            data = TagData ()
            context = JsonContext (data, tag, False)
            data.jsonCode (context)
            result.append (data)
        return result

    def addImpliedTag (self, parentCategoryName, parentTagName, impliedTagCategoryName, impliedTagName):
        """add implied tag to a parent tag.

           parentId: id of the parent tag
           impliedTagId: id of the implied tag to add"""
        self.jsonQuery ("POST", "/json/addimpliedtag", simplejson.dumps([
            parentCategoryName, parentTagName, impliedTagCategoryName, impliedTagName]))

    def removeImpliedTag (self, parentId, impliedTagId):
        """remove implied tag from a parent tag.

           parentId: id of the parent tag
           impliedTagId: id of the implied tag to remove"""
        self.jsonQuery ("POST", "/json/removeimpliedtag", simplejson.dumps([
            parentId, impliedTagId]))

    def getFolderAttributes (self, virtualPath):
        """get miscellaneous attributes of a folder.

           virtualPath: path of folder to set atrributes for
           returns: instance of FolderAttributesData"""       
        attributes = self.jsonQuery ("GET", "/json/getfolderattributes", simplejson.dumps(virtualPath))
        data = FolderAttributesData ()
        context = JsonContext (data, attributes, False)
        data.jsonCode (context)
        return data

    def setFolderAttributes (self, virtualPath, attributesData):
        """set miscellaneous attributes of a folder.

           virtualPath: path of folder to set atrributes for
           attributesData: instance of FolderAttributesData"""
        context = JsonContext (attributesData, {}, True)
        attributesData.jsonCode (context)
        self.jsonQuery ("POST", "/json/setfolderattributes", simplejson.dumps([virtualPath, context.jsonDict]))

    def getTagsForFolder (self, virtualPath):
        """get list of tags set for folder.
        
           virtualPath: path of folder for which to retrieve the set tags
           returns: list of tag ids"""
        return self.jsonQuery ("GET", "/json/gettagsforfolder", simplejson.dumps(virtualPath))

    def setTagsForFolder (self, virtualPath, tagIds):
        """set list of tags on folder
        
           virtualPath: path of folder to set tags for
           tagIds: list of tag ids to set for folder"""
        self.jsonQuery ("POST", "/json/settagsforfolder", simplejson.dumps([virtualPath, tagIds]))

    def enumerateFolder (self, virtualPath):
        """enumerateFolder lists the contents of the specified folder. If
           the volume is offline, files will be aggregated into a single
           place-holder entry. Returns list of FileInfo objects.
           
           virtualPath: path to the folder to enumerate"""
        result = []
        infos = self.jsonQuery ("GET", "/json/enumeratefolder", simplejson.dumps(virtualPath))
        for info in infos:
            data = FileInfo ()
            context = JsonContext (data, info, False)
            data.jsonCode (context)
            result.append (data)
        return result

    def enumerateFolderFromDb (self, virtualPath):
        """enumerateFolder lists the contents of the specified folder as
           stored in the db. Returns list of FileInfo objects. Supports
           sequences.
           
           virtualPath: path to the folder to enumerate"""
        result = []
        infos = self.jsonQuery ("GET", "/json/enumeratefolderfromdb", simplejson.dumps(virtualPath))
        for info in infos:
            data = FileInfo ()
            context = JsonContext (data, info, False)
            data.jsonCode (context)
            result.append (data)
        return result

    def getFolderInfo (self, virtualPath):
        """getFolderInfo gets information about a particular folder from the
           in-memory folder tree. Returns a FileInfo object.mro

           virtualPath: path to the folder to query"""
        info = self.jsonQuery ("GET", "/json/getfolderinfo", simplejson.dumps(virtualPath))
        data = FileInfo ()
        context = JsonContext (data, info, False)
        data.jsonCode (context)
        return data
           

    def scan (self, virtualPath):
        """(re)scan a specific folder tree
        
           virtualPath: the virtual path of the tree to be scanned"""
        self.jsonQuery ("POST", "/json/scan", simplejson.dumps(virtualPath))

    def scanSynchronous (self, virtualPath, maxTimeout=60.0):
        """(re)scan a specific folder tree synchronously. This call will
               block until the scan is complete.
        
           virtualPath: the virtual path of the tree to be scanned"""
        token = self.jsonQuery ("POST", "/json/scanwithstatus", simplejson.dumps(virtualPath))
        sleep_s = 0.1
        while True:
            status = self.jsonQuery ("GET", "/json/getasyncstatus", simplejson.dumps(token))
            done, error = status
            if done:
                if error:
                    raise StandardError(error);
                break
            time.sleep(sleep_s)
            sleep_s *= 2
            if sleep_s > maxTimeout:
                sleep_s = maxTimeout

    def report (self, request):
        """run report
        
           request: an instance of FastStatRequest"""
        context = JsonContext (request, {}, True)
        request.jsonCode (context)
        result = self.jsonQuery ("POST", "/json/report", simplejson.dumps(context.jsonDict))
        data = FastStatRequest ()
        context = JsonContext (data, result, False)
        data.jsonCode (context)
        return data

    def bulkTagUpdate (self, tagsToAdd=[], tagsToUpdate=[], tagsToDelete=[]):
        """bulkTagUpdate can be used to create, update and delete multiple tags
           in a single transaction. This is orders of magnitude faster than
           doing this with the single tag apis. Note that CN! server does
           not impose any restrictions on the number of requests. It is up to
           the caller to keep the size of the request and the amount of time
           it will block all other activities on the server reasonable for the
           given environment. For example, it might likely be entirely reasonable
           to engage the database lock for multiple minutes at 3am in the morning.
           Not so much during the day.
    
           tagsToAdd is a list of tuples, each tuple consisting of [categoryName, TagData]
           tagsToUpdate is a list of TagData
           tagsToDelete is a list of tag ids"""
        toAdd = []
        for categoryName, tagData in tagsToAdd:
            context = JsonContext (tagData, {}, True)
            tagData.jsonCode (context)
            toAdd.append ([categoryName, context.jsonDict])
        toUpdate = []
        for tagData in tagsToUpdate:
            context = JsonContext (tagData, {}, True)
            tagData.jsonCode (context)
            toUpdate.append (context.jsonDict)
        self.jsonQuery ("POST", "/json/bulktagupdate", simplejson.dumps([toAdd, toUpdate, tagsToDelete]))

    def bulkGetImpliedTags (self, tags=[]):
        """bulkGetImpliedTags can be used to get the implied tags for a list of tags
           in a single transaction. The argument is a list of category/tags strings,
           the result is a list of lists of category/tag strings."""
        return self.jsonQuery ("POST", "/json/bulkgetimpliedtags", simplejson.dumps(tags))

    def addTagCategory (self, categoryData):
        """add new tag category.
        
           categoryData: TagCategoryData object created locally"""
        context = JsonContext (categoryData, {}, True)
        categoryData.jsonCode (context)
        id = self.jsonQuery ("POST", "/json/addcategory", simplejson.dumps(context.jsonDict))
        categoryData.id = id
        return id

    def deleteTagCategory (self, id, force=False):
        """delete tag category.
        
           id: id of tag category to delete
           force: boolean, set to True to forcibly delete any tags in the category"""
        self.jsonQuery ("POST", "/json/deletecategory", simplejson.dumps([id,force]))

    def changeTagCategory (self, categoryData):
        """change tag category.
        
           categoryData: TagCategoryData object received from server"""
        context = JsonContext (categoryData, {}, True)
        categoryData.jsonCode (context)
        self.jsonQuery ("POST", "/json/changecategory", simplejson.dumps(context.jsonDict))
        categoryData.changeCount += 1

    def bulkImpliedTagUpdate (self, tagsToAdd=[], tagsToDelete=[]):
        """bulkImpliedTagUpdate can be used to add and remove implied tags in one
           json transaction.
        
           tagsToAdd is a list of tuples, each tuple consisting of
              - a category/tag identifier string (the parent)
              - a list of category/tag identifier strings (the children to add)
           tagsToDelete is a list of tuples, each tuple consisting of
              - a category/tag identifier string (the parent)
              - a list of category/tag identifier strings (the children to remove)"""
        self.jsonQuery ("POST", "/json/bulkimpliedtagupdate", simplejson.dumps([tagsToAdd, tagsToDelete]))

    def prepareForAutomatedTest (self):
        """prepare the CN server for automated testing:
             - discards current db
             - clears folder tree
           Note: must be logged in as root"""
        self.jsonQuery ("POST", "/json/prepareforautomatedtest", "0")

    def bulkSetTagsForFolder (self, updates=[]):
        """set tags on multiple folders in one go
           updates contains a list of tuples consisting of
              the virtual path of the folder
              a list containing category/tags strings to set
           note: tags are created if they don't exist, categories aren't"""
        self.jsonQuery("POST", "/json/bulksettagsforfolder", simplejson.dumps(updates))

    def showHtmlForm (self, guitoken, x, y, html):
        """show an html form in the CN GUI

           arguments:
              guitoken - the token passed by the %guitoken variable in a
                      custom context menu script
              x - width of window in pixels
              y - height of window in pixels
              html - the html form to be shown

           result: A tuple consisting of
              the content of the action attribute (useful when there are multiple form tags)
              a dictionary containing the resulting 'query' as key/value pairs
                 key: the name
                 value: a list of values, typically one

           notes:
              - Java's HTML control supports HTML 3 only(!)
              - The width of the <select> control doesn't appear to be adjustable
        """
           
        result = self.stringQuery("POST", "/misc/showhtmlform?guitoken=%s&x=%d&y=%d" % (guitoken,x,y), html)
        pos = result.find ('?')
        if pos == -1:
            raise Exception("unexpected html form response format: "+result)
        action = result[:pos]
        
        return action,cgi.parse_qs(result[pos+1:])

    def searchForPaths (self, searchPattern, maxResults, restartContext=None):
        """ search in in-memory folder tree and return paths that match. See
            apitest.py for sample usage.

            arguments:
                searchPattern - search pattern as used in the GUI
                maxResults - maximum number of results to rerturn in this call,
                             must not specify more than 1000
                restartContext - opaque context used for repeated calls to this
                             function

            return values:
                paths - the list of paths that match the pattern
                restartContext - None if all results have been returned or
                             an opaque context used to call this function
                             again for more results.
        """
        # warnings.warn("searchforPaths is deprecated, please use searchForPathsGeneratorV2", UserWarning)
        paths,restartContext = self.jsonQuery("POST", "/json/searchforpaths", simplejson.dumps([searchPattern,maxResults,restartContext]))
        return paths, restartContext

    def searchForFileInfos (self, searchPattern, maxResults, restartContext=None):
        """ search in in-memory folder tree and return file infos for paths that match. See
            apitest.py for sample usage.

            arguments:
                searchPattern - search pattern as used in the GUI
                maxResults - maximum number of results to rerturn in this call,
                             must not specify more than 1000
                restartContext - opaque context used for repeated calls to this
                             function

            return values:
                infos - the list of file infos for paths that match the pattern
                restartContext - None if all results have been returned or
                             an opaque context used to call this function
                             again for more results.
        """
        # warnings.warn("searchforFileInfos is deprecated, please use searchForFileInfosGeneratorV2", UserWarning)
        infos,restartContext = self.jsonQuery("POST", "/json/searchforfileinfo", simplejson.dumps([searchPattern,maxResults,restartContext]))
        results = []
        for info in infos:
            data = FileInfo ()
            context = JsonContext (data, info, False)
            data.jsonCode (context)
            results.append (data)
        return results, restartContext

    def searchForPathsGenerator (self, searchPattern):
        """ search in in-memory folder tree and return a generator for
            iterating over the results. See apitest.py for sample usage.

            arguments:
                searchPattern - search pattern as used in the GUI

            return values:
                a generator that returns a path structure for
                each invocation. Best used with a for loop.
        """
        warnings.warn("searchforPathsGenerator is deprecated, please use searchForPathsGeneratorV2", UserWarning)
        restartContext = None
        while 1:
            infos,restartContext =self.searchForPaths (searchPattern, 1000, restartContext)
            for info in infos:
                yield info
            if not restartContext:
                break;


    def searchForFileInfosGenerator (self, searchPattern):
        """ search in in-memory folder tree and return a generator for
            iterating over the results. See apitest.py for sample usage.

            arguments:
                searchPattern - search pattern as used in the GUI

            return values:
                a generator that returns a FileInfo structure for
                each invocation. Best used with a for loop.
        """
        warnings.warn("searchforFileInfosGenerator is deprecated, please use searchForFileInfosGenneratorV2", UserWarning)
        restartContext = None
        while 1:
            infos,restartContext = self.searchForFileInfos (searchPattern, 1000, restartContext)
            for info in infos:
                yield info
            if not restartContext:
                break;

    def searchForPathsGeneratorV2 (self, pattern, searchRoot="/", tempLocation=None):
        """ start search and return a generator for
            iterating over the results. See apitest.py for sample usage.

            arguments:
                pattern - search pattern as used in the GUI
                searchRoot - root path of search
                tempLocation - (optional) directory (has to be empty if provided) for temp files used
                               for sorting and deduplication if such behavior is desired
                               (should be used only in the case of AFI index)

            return values:
                a generator that returns a path for
                each invocation. Best used with a for loop.

            Note: The searchRoot is only implemented for AFI.
        """
        unique_filename = None
        if tempLocation is not None:
            if os.listdir(tempLocation):
                raise ValueError('Temp location is not empty')

            unique_filename = os.path.join(tempLocation, str(uuid.uuid4()))

        context = SearchContext(self, pattern, tempLocation, unique_filename, searchRoot)
        try:
            if tempLocation is None:
                while 1:
                    paths, done = context.getPaths(1000)
                    for path in paths:
                        yield path
                    if done:
                        break
            else:
                context.getPathsUnique(1000)
                with open (unique_filename, 'rb') as f:
                    while 1:
                        path = context.readPathFromFileFunction(f)
                        if path is None:
                            break
                        else:
                            yield path

                os.remove(unique_filename)
        finally:
            context.close()

    def searchForFileInfosGeneratorV2 (self, pattern, searchRoot="/", tempLocation=None):
        """ start search and return a generator for
            iterating over the results. See apitest.py for sample usage.

            arguments:
                pattern - search pattern as used in the GUI
                searchRoot - root path of search
                tempLocation - (optional) directory (has to be empty if provided) for temp files used
                               for sorting and deduplication if such behavior is desired,
                               path field of the FileInfo is used as the sorting key
                               (should be used only in the case of AFI index)

            return values:
                a generator that returns a FileInfo for
                each invocation. Best used with a for loop.

            Note: The searchRoot is only implemented for AFI.
        """
        unique_filename = None
        if tempLocation is not None:
            if os.listdir(tempLocation):
                raise ValueError('Temp location is not empty')

            unique_filename = os.path.join(tempLocation, str(uuid.uuid4()))

        context = SearchContext(self, pattern, tempLocation, unique_filename, searchRoot)
        try:
            if tempLocation is None:
                while 1:
                    infos, done = context.getFileInfos(1000)
                    for info in infos:
                        yield info
                    if done:
                        break
            else:
                context.getFileInfosUnique(1000)
                with open (unique_filename, 'rb') as f:
                    while 1:
                        info = context.readFileInfoFromFileFunction(f)
                        if info is None:
                            break
                        else:
                            fInfo = FileInfo ()
                            jsonContext = JsonContext (fInfo, info, False)
                            fInfo.jsonCode(jsonContext)
                            yield fInfo

                os.remove(unique_filename)

        finally:
            context.close()

    def bulkGetTagsForFolder (self, virtualPathList):
        """ get list of tags set for a set of folders.
        
            virtualPath: list of paths of folders for which to retrieve the set tags
            returns: list of list of cat/tag strings"""
        return self.jsonQuery ("GET", "/json/bulkgettagsforfolder", simplejson.dumps(virtualPathList))
        
    def getLdapGroupMapping (self):
        """Get mapping of CN groups to ldap groups. Returns list of lists, each containing
           CN name and list of ldap groups mapped to it."""
        return self.jsonQuery ("GET", "/json/getldapgroupmapping", "")

    def setLdapGroupMapping (self, mapping):
        """Set mapping of CN groups to ldap groups. Requires list of lists, each containing
           CN name and list of ldap groups mapped to it."""
        self.jsonQuery ("POST", "/json/setldapgroupmapping", simplejson.dumps(mapping))
        

    def saveAs (self, guitoken, contentToSave, clientDefaultLocationFullName, filterDescription="", filters=""):
        """ open a saveAs dialog froms gui at the default location as "clientDefaultLocationFullName"
        with suffix list description as "filterDescription" and suffix list as "filters"
        for users to save the content as "contenttoSave" to a localtion as users' choice
            arguments:
                contentToSave - the content to save
        clientDefaultLocationFullName - default location for saveAs dialog
        filterDescription (optional, but required if filters used)- description for suffix list, no spaces
        filters (optional)- list of extensions for filter, separated by commas, no spaces

            return values:
                selectedFilePath - the path selected by users to save to
                selectedFileName - the filename selected by users to save to
        """
        description = "MySaveAsDescription" # no use for now

        # we need to encode this string as hex to fool http
        clientDefaultLocationFullName = clientDefaultLocationFullName.encode('utf-8').encode('hex');

        # send http request to CN server
        body,header = self.stringQueryWithRespondHeader("POST", "/misc/saveas?guitoken=%s&description=%s&file_name=%s&filter=<%s-%s>" % (guitoken,description,clientDefaultLocationFullName,filterDescription,filters), contentToSave)

        # selected file path/name are inside http response header
        if header.has_key("file-path"):
            selectedFilePath = header["file-path"]
        else:
            selectedFileath = ""

        if header.has_key("file-name"):
            selectedFileName = header["file-name"]
        else:
            selectedFileName = ""

        # log for debug
        # print "selectedFilePath to save = ",selectedFilePath
        # print "selectedFileName to save = ",selectedFileName

        return selectedFilePath,selectedFileName

    def reparentFileSystems (self, newParent, fileSystemNames, indexHint):
        """ Move list of file systems to new parent. Either to a scan group
            or to the top level. Can also be used to reorder volumes within
            a scan group.

            arguments:
                newParent - name of new parent scan group or None
                fileSystemNames - list of volume names to move
                indexHint - zero based offset insertion should start at

            return values:
                None
        """
        self.jsonQuery ("POST", "/json/reparentfilesystems", simplejson.dumps([newParent, fileSystemNames, indexHint]))


    def refreshInstallableCCMs(self):
        """ Force refresh of installable CCM scripts.
        """
        self.jsonQuery("POST", "/json/refreshinstallableccms")

class SearchContext:
    """ Create a search job.

        arguments:
            api: a reference to an initialized API object
            pattern: the search pattern
            searchRoot: the path to start the search from (optional)

        Note: A searchRoot other than "/" is not supported when
              all-file indexing (AFI) is not enabled.

        Note: It is safer to use the search generators that wrap this class
              as the generators have safeguards in place to call close() in
              case of errors. The generators also require less code.
    """
    def __init__(self, api, pattern, tempLocation, uniqueFilename, searchRoot="/"):
        self.api = api
        self.tempLocation = tempLocation
        self.uniqueFilename = uniqueFilename
        self.firstCall = True
        if tempLocation is not None:
            self.uniquefy = True
            self.auxFile = os.path.join(tempLocation, str(uuid.uuid4()))

        self.jobId = self.api.jsonQuery("POST", "/json/startsearch",
            simplejson.dumps([searchRoot, pattern]))

    """ Get search results as a list of paths.

        arguments:
            maxCount: maximum number of results to return in this call

        result:
            list of paths
            boolean indicating whether search is complete
    """
    def getPaths(self, maxCount=1000):
        return self.api.jsonQuery("GET", "/json/getpathsearchresults",
            simplejson.dumps([self.jobId, maxCount]))

    def __pathKeyFunction(self, path):
        return path.lower(), path

    def __writePathToFileFunction(self, f, path):
        f.write((path + '\n').encode('utf-8'))

    def readPathFromFileFunction(self, f):
        line = f.readline().decode('utf-8')
        return line.replace('\n', '') if line != '' else None

    def __fileInfosKeyFunction(self, a):
        return a['path'].lower(), a['path']

    def __writeFileInfoToFileFunction(self, f, info):
        f.write((simplejson.dumps(info) + '\n').encode('utf-8'))

    def readFileInfoFromFileFunction(self, f):
        line = f.readline().decode('utf-8')
        return simplejson.loads(line.replace('\n', '')) if line != '' else None

    def __sortAndUniqiefy(self, objects, keyFunction, writeToFileFunction, readFromFileFunction):
        objects.sort(key=keyFunction)
        previous_object = None

        if (self.firstCall):
            with open(self.uniqueFilename, 'wb+') as f:
                for object in objects:
                    if previous_object is None or (keyFunction(previous_object) != keyFunction(object)):
                        writeToFileFunction(f, object)
                        previous_object = object
            self.firstCall = False
        else:
           with open(self.auxFile, 'wb+') as faux:
                with open(self.uniqueFilename, 'rb') as fr:
                    referenceExhausted = False
                    keepReference = False
                    for object in objects:
                        getNextObject = False
                        if previous_object is not None and (keyFunction(previous_object) == keyFunction(object)):
                            continue
                        if referenceExhausted:  # means we ran out of old objects, no need to compare anymore
                            writeToFileFunction(faux, object)
                        else:
                            while not getNextObject:
                                if keepReference:
                                    keepReference = False
                                else:
                                    referenceObject = readFromFileFunction(fr)

                                if referenceObject is None:
                                    # we ran out reference objects, write current new object,
                                    # rest of new objects are written outside of this while loop
                                    referenceExhausted = True
                                    writeToFileFunction(faux, object)
                                    break

                                if keyFunction(referenceObject) < keyFunction(object):
                                    writeToFileFunction(faux, referenceObject)
                                elif keyFunction(referenceObject) > keyFunction(object):
                                    writeToFileFunction(faux, object)
                                    getNextObject = True
                                    keepReference = True
                                else:
                                    writeToFileFunction(faux, referenceObject)
                                    getNextObject = True

                        previous_object = object

                    if not referenceExhausted:  # means we ran out of the new objects but not old ones
                        if keepReference:   # means we have a reference object left dangling from previous for loop
                            writeToFileFunction(faux, referenceObject)

                        # tricky: this does not use custom write function since unread reference objects
                        # are lines in reference file in the format which is already desired, so these lines
                        # just need to be transferred into auxiliary file
                        for lines in fr:
                            faux.writelines(lines)

           os.remove(self.uniqueFilename)
           os.rename(self.auxFile, self.uniqueFilename)

    """ Get search results as a list of unique and sorted paths.
        List is complete and written to the file with unique name

        arguments:
            maxCount: maximum number of results to return from server in one iteration

        result:
            none
    """
    def getPathsUnique(self, maxCount=1000):
        self.firstCall = True
        while 1:
            paths, done = self.api.jsonQuery("GET", "/json/getpathsearchresults",
                simplejson.dumps([self.jobId, maxCount]))
            self.__sortAndUniqiefy(paths, self.__pathKeyFunction,
                                   self.__writePathToFileFunction, self.readPathFromFileFunction)
            if done:
                break

    """ Get search results as a list of FileInfo structures

        arguments:
            maxCount: maximum number of results to return in this call

        result:
            list of FileInfo structures
            boolean indicating whether search is complete
    """
    def getFileInfos(self, maxCount=1000):
        structures, done = self.api.jsonQuery("GET", "/json/getfileinfosearchresults",
            simplejson.dumps([self.jobId, maxCount]))
        infos = []
        for info in structures:
            data = FileInfo ()
            context = JsonContext (data, info, False)
            data.jsonCode (context)
            infos.append (data)
        return infos, done

    def getFileInfosUnique(self, maxCount=1000):
        self.firstCall = True
        while 1:
            structures, done = self.api.jsonQuery("GET", "/json/getfileinfosearchresults",
                simplejson.dumps([self.jobId, maxCount]))
            self.__sortAndUniqiefy(structures, self.__fileInfosKeyFunction,
                                   self.__writeFileInfoToFileFunction, self.readFileInfoFromFileFunction)

            if done:
                break

        # infos = []
        # for info in structures:
        #     data = FileInfo ()
        #     context = JsonContext (data, info, False)
        #     data.jsonCode (context)
        #     infos.append (data)
        # return infos, done

    """ Close search.

        Note: It is critically important to call this method to release
              search resources on the server.
    """
    def close(self):
        self.api.jsonQuery("GET", "/json/closesearch",
            simplejson.dumps(self.jobId))

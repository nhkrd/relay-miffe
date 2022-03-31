from socketserver import ThreadingTCPServer
from socketserver import ThreadingMixIn
from http.server import BaseHTTPRequestHandler
import time
import datetime
import json
import codecs
import http.client
import xml.etree.ElementTree as ET
from xml.dom import minidom
import configparser

ET.register_namespace('', 'urn:mpeg:dash:schema:mpd:2011')

inifile = configparser.ConfigParser()
inifile.read('settings.ini')

q_emsg = []
q_emsg_segment = []
q_mpd = []
q_mpd_segment = []
q_chunk = {}
LogFlag = True

class HandleRequests(ThreadingMixIn, BaseHTTPRequestHandler):

    protocol_version = "HTTP/1.1"


#
# writeLog
#
    def writeLog(self,loginfo):
        if LogFlag:
            self.doWrite = False
            if 0 <= loginfo.find('/video/'):
                self.doWrite = True
            if 0 <= loginfo.find('/audio/'):
                self.doWrite = True
            if 0 <= loginfo.find('init'):
                self.doWrite = True
            if 0 <= loginfo.find('chunk'):
                self.doWrite = True
            if 0 <= loginfo.find('emsg'):
                self.doWrite = True
            if self.doWrite:
                flog.write(str(int(time.time()*1000)) + ',' + loginfo + '\n')
                flog.flush()


#
# readBody
#
    def readBody(self,size):
        self.bodySize = (-1)
        self.bodyData = bytearray()
        if 0 < size:
            self.bodyData = self.rfile.read( size )
        else:
            self._size = self.rfile.readline()
            self.bodyEnd = (0 == self._size.find(b'\r\n'))
            if not self.bodyEnd:
                self.bodySize = int(self._size, 16)
                if 0 < self.bodySize:
                    self.bodyData = self.rfile.read( self.bodySize )
        return self.bodySize, self.bodyData


#
# readFile
#
    def readFile(self,fpath):
        wholedata = ""
        with open(fpath) as f:
            wholedata = f.read()
        return wholedata


#
# putQueueEMSG
#
    def putQueueEMSG(self, data):
        print( "emsg ===> ", data )
        if data['control']['method'] == 'C':
            tnow = datetime.datetime.now()
            tend = datetime.datetime.now() + datetime.timedelta(milliseconds = int(data['control']['c_duration']))
            print( datetime.datetime.now(), tend )
            data['control']['c_duration'] = tend
            q_emsg_segment.append(data)
        else:
            q_emsg.append(data)


#
# putQueueMPD
#
    def putQueueMPD(self, data):
        print( "mpd ===> ", data )
        if data['control']['method'] == 'C':
            tend = datetime.datetime.now() + datetime.timedelta(milliseconds = int(data['control']['c_duration']))
            print( datetime.datetime.now(), tend )
            data['control']['c_duration'] = tend
            q_mpd_segment.append(data)
        else:
            q_mpd.append(data)


#
# putQueue
#
    def putQueue(self, data):
        global LogFlag
        self.dEmsg = json.loads(data)

        ### for Stat
        if "urn:scte:scte35:2013:stat" == self.dEmsg['emsg']['scheme_id_uri']:
            msgstr = ''.join([chr(x) for x in self.dEmsg['emsg']['message_data']])
            if 0 <= msgstr.find('S'):
                LogFlag = True

            self.writeLog( 'emsg received ' + msgstr )

            if 0 <= msgstr.find('E'):
                LogFlag = False

            msgstr = ''.join([msgstr, ',', str(int(time.time()*1000))])
            msgbyte = [ord(x) for x in codecs.iterencode(msgstr, 'utf-8')]
            self.dEmsg['emsg']['message_data'] = msgbyte

        if self.dEmsg['control']['target'] == "emsg":
            self.putQueueEMSG(self.dEmsg)
        elif self.dEmsg['control']['target'] == "mpd":
            self.putQueueMPD(self.dEmsg)
        else:
            print( "Error" )

        self.writeLog( 'emsg received ' + str(len(q_emsg)) )


#
# createEMSG Version0
#
    def createEmsgBox_v0(self, msg):
        self.mp4box = ''
        self.mp4boxElem = []

        print( "createEmsgBox_v0", msg )

        msgstr = ''.join([chr(x) for x in msg['ev_message_data']])
        msgstr = ''.join([msgstr, ',', str(int(time.time()*1000))])
        msg['message_data'] = [ord(x) for x in codecs.iterencode(msgstr, 'utf-8')]
        self.boxlen = 4*3 + len(msg['scheme_id_uri']) + len(msg['value']) + 2 + 4*4 + len(msg['ev_message_data']);
        print( "v0 boxlen: ", self.boxlen )

        self.mp4boxElem.append( self.boxlen.to_bytes(4,'big') )
        self.mp4boxElem.append( b'emsg' )
        self.mp4boxElem.append( msg['ev_version'].to_bytes(1,'big') )
        self.mp4boxElem.append( msg['ev_flags'].to_bytes(3,'big') )
        ### Version=0
        self.mp4boxElem.append( msg['scheme_id_uri'].encode() )
        self.mp4boxElem.append( int('0').to_bytes(1,'big') )
        self.mp4boxElem.append( msg['value'].encode() )
        self.mp4boxElem.append( int('0').to_bytes(1,'big') )

        self.mp4boxElem.append( int(msg['timescale']).to_bytes(4,'big') )
        self.mp4boxElem.append( int(msg['ev_presentation_time']).to_bytes(4,'big') )
        self.mp4boxElem.append( int(msg['ev_duration']).to_bytes(4,'big') )
        self.mp4boxElem.append( msg['ev_id'].to_bytes(4,'big') )

        for i in range(0, len(msg['ev_message_data'])):
            self.mp4boxElem.append( msg['ev_message_data'][i].to_bytes(1,'big') )

        self.mp4box = b''.join(self.mp4boxElem)
        return self.mp4box


#
# createEMSG Version1
#
    def createEmsgBox_v1(self, msg):
        self.mp4box = ''
        self.mp4boxElem = []

        print( "createEmsgBox_v1", msg )

        msgstr = ''.join([chr(x) for x in msg['ev_message_data']])
        msgstr = ''.join([msgstr, ',', str(int(time.time()*1000))])
        msg['message_data'] = [ord(x) for x in codecs.iterencode(msgstr, 'utf-8')]
        self.boxlen = 4*3 + 4*3 + 8*1 + len(msg['scheme_id_uri']) + len(msg['value']) + 2 + len(msg['ev_message_data']) ;
        print( "v1 boxlen: ", self.boxlen )

        self.mp4boxElem.append( self.boxlen.to_bytes(4,'big') )
        self.mp4boxElem.append( b'emsg' )
        self.mp4boxElem.append( msg['ev_version'].to_bytes(1,'big') )
        self.mp4boxElem.append( msg['ev_flags'].to_bytes(3,'big') )
        ### Version=1
        self.mp4boxElem.append( int(msg['timescale']).to_bytes(4,'big') )
        self.mp4boxElem.append( int(msg['ev_presentation_time']).to_bytes(8,'big') )
        self.mp4boxElem.append( int(msg['ev_duration']).to_bytes(4,'big') )
        self.mp4boxElem.append( msg['ev_id'].to_bytes(4,'big') )

        self.mp4boxElem.append( msg['scheme_id_uri'].encode() )
        self.mp4boxElem.append( int('0').to_bytes(1,'big') )
        self.mp4boxElem.append( msg['value'].encode() )
        self.mp4boxElem.append( int('0').to_bytes(1,'big') )

        for i in range(0, len(msg['ev_message_data'])):
            self.mp4boxElem.append( msg['ev_message_data'][i].to_bytes(1,'big') )

        self.mp4box = b''.join(self.mp4boxElem)
        return self.mp4box


#
# createEMSG
#
    def createEMSG(self, msg):
        if msg['ev_version'] == 0: 
            return self.createEmsgBox_v0(msg)
        else:
            return self.createEmsgBox_v1(msg)


#
# copyXML
#
    def copyXML(self, toRoot, nodefrom):
        nodeTo = None
        for child in nodefrom:
            nodeTo = ET.SubElement(toRoot, child.tag)
            for kk, vv in child.attrib.items():
                nodeTo.set(kk, vv)
            if not (child.text is None):
                nodeTo.text = child.text
            self.copyXML(nodeTo, child)
        return nodeTo


#
# _set_headers
#
    def _set_headers(self):
        self.send_response(200)
        self.end_headers()


#
# parseURLParams
#
    def parseURLParams(self, param):
        params = {}
        queryparams = param.split("?")[1]
        urlparams = queryparams.split("&")
        for i in range(0, len(urlparams)):
            element = urlparams[i].split("=")
            params[ element[0] ] = element[1] 
        return params


#
# httpConn
#
    def httpConn(self, targetpath, headers):
        self.elements = targetpath.split("/")
        self.hostport = self.elements[2].split(":")
        self.filepath = '/'.join(self.elements[3:])
        self.filepath = "/" + self.filepath

        if 1 == len(self.hostport):
            self.hostport.append(80)

        self.conn = ''
        if self.elements[0] == 'http:':
            self.conn = http.client.HTTPConnection(self.hostport[0], self.hostport[1])
        elif  self.elements[0] == 'https:':
            self.conn = http.client.HTTPSConnection(self.hostport[0], self.hostport[1])
        self.conn.putrequest("PUT", self.filepath)

        self.conn.putheader("Accept", "*/*")
        self.conn.putheader("User-Agent", "Videon EdgeCaster4K 0.3")
        self.conn.putheader("cache-control", "max-age=6")
        self.conn.putheader("x-amz-allow-stream", "true")
        self.conn.putheader("x-amz-upload-availability", "STREAMING")
        self.conn.putheader("Transfer-Encoding", "chunked")
        self.conn.putheader("Expect", "100-continue")
        self.conn.endheaders()
        return self.conn


#
# httpPutTarget
#
    def httpPutTarget(self, targetpath, _headers, putdata, contFlag):
        self.url = targetpath
        self.headers = _headers
        self.chunked = putdata
        self.dataEMSG = None
        self.doEMSGInsert = False
        self.dataEMSGMPD = None
        self.doEMSGMPDInsert = False

        if not (self.url in q_chunk):
            self.elements = targetpath.split("/")
            self.hostport = self.elements[2].split(":")
            self.filepath = '/'.join(self.elements[3:])
            q_chunk[self.url] = {"dataRemain":False, "dataRemainLen":0, "name":"", "insertEMSG":False}
            q_chunk[self.url]["conn"] = self.httpConn(targetpath, self.headers)

        self.targetdata = putdata

        ### for MPD
        if 0 <= targetpath.find('mpd') :
            self.senddata = self.targetdata
            self.sendlen = format(len(self.senddata), 'x')

            if 0 < len(self.senddata):
                self.dataEMSGMPD = None
                self.doEMSGMPDInsert = False
                if 0 < len(q_mpd):
                    self.dataEMSGMPD = q_mpd.pop(0)
                    self.doEMSGMPDInsert = True
                    print( 'dataMPD Insert ---------------------------------------------------------', self.url )
                else:
                    if (not q_chunk[self.url]["insertEMSG"]) and (0 < len(q_mpd_segment)):
                        self.dataEMSGMPD = q_mpd_segment.pop(0)
                        tnow = datetime.datetime.now()
                        if tnow <= self.dataEMSGMPD['control']['c_duration']:
                            q_mpd_segment.insert(0, self.dataEMSGMPD)
                            self.doEMSGMPDInsert = True
                            print( 'dataMPD Insert ---------------------------------------------------------', self.url )
                        else:
                            print( 'dataMPD Expire ---------------------------------------------------------', self.url )

                if not self.doEMSGMPDInsert:
                    self.putbody = b''.join([self.sendlen.encode('utf-8'), b'\r\n', self.senddata, b'\r\n'])
                    if self.url in q_chunk:
                        q_chunk[self.url]["conn"].send(self.putbody)
                else:
                    if self.dataEMSGMPD['control']['method'] == 'C':
                        q_chunk[self.url]["insertEMSG"] = True
                    self.treeroot = ET.fromstring(self.senddata.decode(encoding='utf-8'))

                    ### add xmlns xlink
                    self.treeroot.set( 'xmlns:xlink', 'http://www.w3.org/1999/xlink' )
                    self.treeperiod = self.treeroot.find('{urn:mpeg:dash:schema:mpd:2011}Period')
                    new_root = ET.Element(self.treeroot.tag)

                    for k, v in self.treeroot.attrib.items():
                        new_root.set(k, v)
                    self.copyXML(new_root, self.treeroot)
                    self.newperiod = new_root.find('{urn:mpeg:dash:schema:mpd:2011}Period')
                    node3 = ET.SubElement(self.newperiod, 'EventStream')

                    print( 'schemeIdUri ', self.dataEMSGMPD['emsg']['scheme_id_uri'] )
                    print( 'value ', str( self.dataEMSGMPD['emsg']['value'] ) )

                    node3.set('schemeIdUri', str(self.dataEMSGMPD['emsg']['scheme_id_uri']))
                    node3.set('value', str( self.dataEMSGMPD['emsg']['value'] ))
                    node3.set('timescale', str( self.dataEMSGMPD['emsg']['timescale'] ))
                    node3.set('xlink:href', str( self.dataEMSGMPD['emsg']['href'] ))
                    node3.set('xlink:actuate', str( self.dataEMSGMPD['emsg']['actuate'] ))

                    print( "event size: ", len( self.dataEMSGMPD['emsg']['event'] ) )
                    for ev in self.dataEMSGMPD['emsg']['event']:
                        node4 = ET.SubElement(node3, 'Event')
                        node4.set('presentationTime', str( ev['ev_presentation_time'] ))
                        node4.set('duration', str( ev['ev_duration'] ))
                        node4.set('id', str( ev['ev_id'] ))
                        node4.text = str( ev['ev_message_data'] )

                    new_tree = ET.ElementTree(new_root)
                
                    tmp0 = ET.tostring(new_root, encoding='utf-8', method="xml", short_empty_elements=False).decode(encoding='utf-8')
                    reparsed = minidom.parseString(tmp0)
                    tmp1 = reparsed.toprettyxml( encoding='utf-8' )
                    print( tmp1 )
                    self.tmp1len = format(len(tmp1), 'x')
                    print( datetime.datetime.now(), self.url, self.tmp1len )
                    self.puttmpbody = b''.join([self.tmp1len.encode('utf-8'), b'\r\n', tmp1, b'\r\n'])
                    if self.url in q_chunk:
                        q_chunk[self.url]["conn"].send(self.puttmpbody)

        ### for other
        elif targetpath.find('m4s') < 0:
            self.senddata = self.targetdata
            self.sendlen = format(len(self.senddata), 'x')
            if 0 < len(self.senddata):
                self.putbody = b''.join([self.sendlen.encode('utf-8'), b'\r\n', self.senddata, b'\r\n'])
                q_chunk[self.url]["conn"].send(self.putbody)

        ### for Segment
        else:
    #         if 0 < len(q_emsg):
    #             self.dataEMSGcheck = q_emsg.pop(0)
    #             self.doEMSGInsert = True
    #         else:
    #             if (not q_chunk[self.url]["insertEMSG"]) and (0 < len(q_emsg_segment)):
    #                 self.dataEMSGcheck = q_emsg_segment.pop(0)
    # #                    if dataEMSGcheck['control']['method'] == 'C':
    #                 tnow = datetime.datetime.now()
    # #                    print( 'check ', tnow, dataEMSGcheck['control']['c_duration'] )
    #                 if tnow <= self.dataEMSGcheck['control']['c_duration']:
    #                     q_emsg_segment.insert(0, self.dataEMSGcheck)
    #                     self.doEMSGInsert = True
    #                     print( 'dataEMSGcheck Insert 0---------------------------------------------------------', self.url )
    #                 else:
    #                     print( 'dataEMSGcheck Expire 0---------------------------------------------------------', self.url )
    #             else:
    #                     q_emsg.append(dataEMSGcheck)
    #                     q_emsg.insert(0, dataEMSGcheck)

            self.didx = 0
            self.dlen = 0
            if q_chunk[self.url]["dataRemain"] == True:
                self.remainDataLen = q_chunk[self.url]["dataRemainLen"] - len(self.targetdata)
                if self.remainDataLen <= 0:
                    q_chunk[self.url]["dataRemain"] = False
                    self.didx = q_chunk[self.url]["dataRemainLen"]
                    self.dlen = self.didx
                else:
                    q_chunk[self.url]["dataRemainLen"] = q_chunk[self.url]["dataRemainLen"] - len(self.targetdata)
            if q_chunk[self.url]["dataRemain"] == False:
                self.boxname = ""
                while self.dlen < len(self.targetdata):
                    self.sendOK = False

                    self.boxlenstr = self.targetdata[self.didx:self.didx+4]
                    self.boxlen3 = int.from_bytes(self.targetdata[self.didx:self.didx+1], byteorder='big', signed=False)
                    self.boxlen2 = int.from_bytes(self.targetdata[self.didx+1:self.didx+2], byteorder='big', signed=False)
                    self.boxlen1 = int.from_bytes(self.targetdata[self.didx+2:self.didx+3], byteorder='big', signed=False)
                    self.boxlen0 = int.from_bytes(self.targetdata[self.didx+3:self.didx+4], byteorder='big', signed=False)
                    self.boxlen = ((self.boxlen3*256 + self.boxlen2)*256 + self.boxlen1)*256 + self.boxlen0
                    self.boxname = self.targetdata[self.didx+4:self.didx+8]

                    if (self.boxname == b'styp') or (self.boxname == b'moof'):
                        self.writeLog(targetpath + "," + str(self.boxname) + "," + str(len(self.targetdata)) + "," + str(self.boxlen) )

                    if (self.boxname == b'moof'):
                        self.dataEMSG = None
                        self.doEMSGInsert = False
                        if 0 < len(q_emsg):
                            self.dataEMSG = q_emsg.pop(0)
                            self.doEMSGInsert = True
                        else:
                            if (not q_chunk[self.url]["insertEMSG"]) and (0 < len(q_emsg_segment)):
                                self.dataEMSG = q_emsg_segment.pop(0)
                                tnow = datetime.datetime.now()
                                if tnow <= self.dataEMSG['control']['c_duration']:
                                    q_emsg_segment.insert(0, self.dataEMSG)
                                    self.doEMSGInsert = True
                                    print( 'dataEMSG Insert ---------------------------------------------------------', self.url )
                                else:
                                    print( 'dataEMSG Expire ---------------------------------------------------------', self.url )

                        if self.doEMSGInsert:
                            print( '*** q_emsg: ', self.url, self.dataEMSG )
                            self.emsgbox = self.createEMSG(self.dataEMSG['emsg'])
                            # Insert
                            self.targetdata1 = self.targetdata[0:self.didx]
                            self.targetdata2 = self.targetdata[self.didx:]
                            self.targetdata = b''.join([self.targetdata1, self.emsgbox, self.targetdata2])
                            self.writeLog( 'emsg insert before ' + targetpath + ',' + str(self.boxname) )

                            if self.dataEMSG['control']['method'] == 'C':
                                q_chunk[self.url]["insertEMSG"] = True
                            continue

                    self.dlen = self.dlen + self.boxlen

                    if self.dlen <= len(self.targetdata):
                        self.sendOK = True
                        self.didx = self.dlen
                    else:
                        q_chunk[self.url]["dataRemain"] = True
                        q_chunk[self.url]["name"] = self.boxname
                        self.remainA = self.dlen - len(self.targetdata)
                        self.remainB = self.boxlen - (len(self.targetdata) - self.didx)
                        q_chunk[self.url]["dataRemainLen"] = self.remainA
                        break #exit while

            self.senddata = self.targetdata
            self.sendlen = format(len(self.senddata), 'x')
            if 0 < len(self.senddata):
                self.putbody = b''.join([self.sendlen.encode('utf-8'), b'\r\n', self.senddata, b'\r\n'])
                q_chunk[self.url]["conn"].send(self.putbody)

        if not contFlag:
            print( datetime.datetime.now(), 'Put End', self.url )
            self.sendlen = format(0, 'x')
            self.putendbody = b''.join([self.sendlen.encode('utf-8'), b'\r\n', b'\r\n'])
            q_chunk[self.url]["conn"].send(self.putendbody)
            q_chunk[self.url]["conn"].getresponse()
            q_chunk[self.url]["conn"].close()
            del q_chunk[self.url]


#
# httpDeleteTarget
#
    def httpDeleteTarget(self, targetpath, headers):
        self.elements = targetpath.split("/")
        self.hostport = self.elements[2].split(":")
        self.filepath = '/'.join(self.elements[3:])
        self.filepath = "/" + self.filepath
        if 1 == len(self.hostport):
            self.hostport.append(80)
        self.conn = ''
        if self.elements[0] == 'http:':
            self.conn = http.client.HTTPConnection(self.hostport[0], self.hostport[1])
        elif  self.elements[0] == 'https:':
            self.conn = http.client.HTTPSConnection(self.hostport[0], self.hostport[1])
        self.conn.putrequest("DELETE", self.filepath)
        self.conn.putheader("Accept", "*/*")
        self.conn.endheaders()


#
# do_GET
#
    def do_GET(self):
        self.paths = self.path.split("/")
        self.fpath = "/".join(self.paths[1:])

        if self.fpath == 'status':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write( ('Hello relay-miffe, version:' + relay_miffe_version).encode('utf-8') )

        elif 0 <= self.fpath.find('gettime'):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(str(int(time.time()*1000)).encode('utf-8'))
        elif 0 <= self.fpath.find('.html'):
            fdata = self.readFile(self.fpath)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(fdata.encode('utf-8'))
        elif 0 <= self.fpath.find('.js'):
            fdata = self.readFile(self.fpath)
            self.send_response(200)
            self.send_header("Content-type", "application/javascript")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(fdata.encode('utf-8'))
        elif 0 <= self.fpath.find('.css'):
            fdata = self.readFile(self.fpath)
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(fdata.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


#
# do_POST
#
    def do_POST(self):
        self.paths = self.path.split("/")
        self.fpath = "/".join(self.paths[1:])
        if self.fpath == 'mte':
            self.send_response(200)
            self.send_header("Connection", "close")
            self.end_headers()
            content_len = int(self.headers.get('content-length'))
            self.post_body = self.rfile.read(content_len)
            self.putQueue(self.post_body)
        else:
            self.send_response(404)
            self.end_headers()


#
# do_PUT
#
    def do_PUT(self):
        self._set_headers()
        dt_now = datetime.datetime.now()
        print( datetime.datetime.now(), 'Put Start', self.path )
        self.qparams = self.parseURLParams(self.path)
        self.fpath = self.qparams['url']
        self.writeLog( self.fpath + ' START' )

        if not (self.fpath in q_chunk):
            self.dummyData = b''
            self.httpPutTarget(self.fpath, self.headers, self.dummyData, True)
            self.chunk_no = 0
            self.post_body = self.readBody(-1)
            self.readbytes = self.post_body[0]

            while 0 != self.readbytes :
                if 0 < self.readbytes:
                    self.httpPutTarget(self.fpath, self.headers, self.post_body[1], True)
                self.post_body = self.readBody(-1)
                self.readbytes = self.post_body[0]
            self.httpPutTarget(self.fpath, self.headers, b'', False)
            self.writeLog( self.fpath + ' END'  )

        else:
            print( 'cancel --------------------------------------------- ', self.fpath )


#
# do_DELETE
#
    def do_DELETE(self):
        print( datetime.datetime.now(), '*** DELETE *** ', self.path )
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header("Connection", "close")
        self.end_headers()
        self.qparams = self.parseURLParams(self.path)
        self.fpath = self.qparams['url']
        self.httpDeleteTarget(self.fpath, self.headers)


#
# logMessage
#
    def log_message(self, format, *args):
        return


host = inifile.get('DEFAULT', 'host')
port = int( inifile.get('DEFAULT', 'port') )
relay_miffe_version = inifile.get('DEFAULT', 'version')

flog = open('input.log', 'a')

address = (host, port)
print( 'start relaymiffe port: ', port )
print( 'relay_miffe_version: ', relay_miffe_version )

ThreadingTCPServer.allow_reuse_address = True
with ThreadingTCPServer(address, HandleRequests) as server:
    server.serve_forever()

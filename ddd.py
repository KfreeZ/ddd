#!/usr/bin/env python  
import picamera
import string, threading, time, datetime
import serial
import crc16
import struct
import binascii
import logging
import json
import requests
from Queue import Queue
import urllib2
import os
import bitstring

DEVICEID = 1
DEBUGMODE = True
SVRIP = '121.41.49.137'
MAX_PIC_ONCARD = 100

class T_SnapShot(threading.Thread):
    def initCam(self):
        self.camera = picamera.PiCamera()
        self.camera.resolution = (640, 480)
        self.camera.start_preview()

    def __init__(self):
        threading.Thread.__init__(self)
        threading.Thread.setName(self, "SnapShot Thread")
        self.initCam()

    def run(self):
        global permissionToSnapshot

        # make a FIFO queue to hold the pics, is queue is full, delete old one before snapshot new one
        picQ = Queue(MAX_PIC_ONCARD)

        while (1):
            permissionToSnapshot.wait()
            picfolderLocation = '/home/pi/ddd/data/%s' % datetime.date.today()
            if os.path.isdir(picfolderLocation):
                pass
            else:
                os.mkdir(picfolderLocation)

            timeString = time.strftime('%Y-%m-%dH%HM%MS%S',time.localtime(time.time()))

            if(DEBUGMODE == True):
                threadname = threading.currentThread().getName()
                logString = "%s: start snapshot at %s" % (threadname, timeString)
                print logString
                logging.info(logString)

            picName = '%s/%s.jpg' % (picfolderLocation, timeString)
            self.camera.capture(picName)

	    # keep the pic under maximum number
	    picQ.put(picName)
	    if (picQ.full()):
	        os.remove(picQ.get())
            
            time.sleep(1)
            fileQ.put(picName)

class T_Uploader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        threading.Thread.setName(self, "Upload Thread")

    def run(self):
        sequenceNo = 1
        while(1):
            pic = fileQ.get()
            # wait 2s for the snapshot thread to create pic
            time.sleep(2)
            try :
                folderLocation = '/home/pi/ddd/data/%s' % datetime.date.today()
                if os.path.isdir(folderLocation):
                    pass
                else:
                    os.mkdir(folderLocation)

                fileLocation = '%s/upload.log' % folderLocation
                uploadLogFile = open(fileLocation, 'a', 0)

                url = 'http://%s:3000/image/create' % SVRIP

                logString = "MSg %d: upload %s to server %s\n" % (sequenceNo, pic, url)
                uploadLogFile.write(logString)

                if(DEBUGMODE == True):
                    print logString                    

                createTime = pic[29:48]
		createTime = createTime.replace('H', ' ')
	        createTime = createTime.replace('M', ':')
                createTime = createTime.replace('S', ':')                
                snapShot = {'upload': ('pic', open(pic, 'rb'), 'image/jpeg')}
                record = {
                    'create_time' : createTime,
                    'device_id' : DEVICEID,
                    'cards' : '00000005f',
                    'school_id' : 1
                    }
                r = requests.post(url, files=snapShot, data= record)
                logString = "MSg %d: result %s\n" % (sequenceNo, r)
                uploadLogFile.write(logString)

                if(DEBUGMODE == True):
                    print logString   

            except Exception, e:
                uploadLogFile.write(str(e))
                uploadLogFile.write('\n')

                if(DEBUGMODE == True):
                    print str(e)   

            sequenceNo += 1

class T_Serial(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        threading.Thread.setName(self, "Serial Thread")
        self._cdMngr = CardManager()

    def run(self):
        self._cdMngr.initCardRcvr(DEVICEID)
        #wait 10s for ddd to get initialized
        time.sleep(10)
        self._cdMngr.setCardRcvrTime()
        self._cdMngr.queryCards(DEVICEID)

class T_NetWork(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        threading.Thread.setName(self, "NetWork Thread")

    def run(self):
        serialNo = 1
        url = "http://%s:3000/mmt/create" % SVRIP
        while(1):
            bullet = jsonQ.get()
            folderLocation = '/home/pi/ddd/data/%s' % datetime.date.today()
            if os.path.isdir(folderLocation):
                pass
            else:
                os.mkdir(folderLocation)

            try :
                fileLocation = '%s/cardRegistry.log' % folderLocation
                cardRegistryFile = open(fileLocation, 'a', 0)

                logString = "Msg %d: %s is ready to send to %s\n" % (serialNo, bullet, url)
                cardRegistryFile.write (logString)

                if(DEBUGMODE == True):
                        print logString  

                r = requests.post(url, data=bullet)
                logString = "Msg %d response: %s\n" % (serialNo, r.content)
                cardRegistryFile.write(logString)

                if(DEBUGMODE == True):
                    print logString  

            except Exception, e:
                cardRegistryFile.write(str(e))
                cardRegistryFile.write('\n')

                if(DEBUGMODE == True):
                    print str(e) 

            serialNo += 1

        
class CmdGenerator:
    # cmd = head + rcvrAddr + cmdLen + cmd + crc + tail
    VARIABLEBYTE = 0x00
    #                               ---head---  ---addr----   -len- -cmd- ---crc pt1--- ---crc pt2--- -tail
    template_ResetRcvr = bytearray([0x7E, 0x3E, VARIABLEBYTE, 0x02, 0x01, VARIABLEBYTE, VARIABLEBYTE, 0x3C])
    #                             ---head---  -id- -len- -cmd-  ---yr pt1---  ---yr pt2---  ----month---  ----date----  ----hour----  ----min-----  ----sec----- ---crc pt1--- ---crc pt2--- -tail
    template_SetTime = bytearray([0x7E, 0x3E, 0xFF, 0x09, 0x10, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, 0x3C])
    #                               ---head---  -----id-----  -len- -cmd- --prev addr-- ---prev sn---  ----rsrv----  ---crc pt1--- ---crc pt2-- -tail
    template_QueryCards = bytearray([0x7E, 0x3E, VARIABLEBYTE, 0x05, 0x00, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, 0x3C])

    def calcCrc(self, bytearray):
        retArray = [0, 0]
        crcValue = crc16.crc16xmodem(buffer(bytearray))
        crcByteArray = struct.unpack("2B", struct.pack("H", crcValue))
        return crcByteArray

    def getTimebyteArray(self):
        now = time.localtime(time.time())
        yearArray = struct.unpack("2B", struct.pack("H", now.tm_year))
        timeByteArray = bytearray(7)
        timeByteArray[0] = yearArray[1]
        timeByteArray[1] = yearArray[0]
        timeByteArray[2] = now.tm_mon
        timeByteArray[3] = now.tm_mday
        timeByteArray[4] = now.tm_hour
        timeByteArray[5] = now.tm_min
        timeByteArray[6] = now.tm_sec
        return timeByteArray

    def gnrtRstCmd(self, devId):
        resetCmd = CmdGenerator.template_ResetRcvr  
        resetCmd[2] = devId
        rstCmdBody = bytearray([resetCmd[2], resetCmd[3], resetCmd[4]])
        crcArray = self.calcCrc(rstCmdBody)
        # attention: reverse the sequence
        resetCmd[5] = crcArray[1]
        resetCmd[6] = crcArray[0]
        return resetCmd

    def gnrtQueryCmd(self, devId, prevAddr, prevSn):
        queryCmd = CmdGenerator.template_QueryCards  
        queryCmd[2] = devId
        queryCmd[5] = prevAddr
        queryCmd[6] = prevSn
        qryCmdBody = bytearray([queryCmd[2],
                                queryCmd[3],
                                queryCmd[4],
                                queryCmd[5],
                                queryCmd[6],
                                queryCmd[7]])
        crcArray = self.calcCrc(qryCmdBody)
        # attention: reverse the sequence
        queryCmd[8] = crcArray[1]
        queryCmd[9] = crcArray[0]
        return queryCmd

    def gnrtSetTimeCmd(self):
        setTimeCmd = CmdGenerator.template_SetTime
        timeByteArray = self.getTimebyteArray()
        for x in xrange(0, 7):
            setTimeCmd[5+x] = timeByteArray[x]
        stCmdBody = bytearray([setTimeCmd[2],
                               setTimeCmd[3],
                               setTimeCmd[4],
                               setTimeCmd[5],
                               setTimeCmd[6],
                               setTimeCmd[7],
                               setTimeCmd[8],
                               setTimeCmd[9],
                               setTimeCmd[10],
                               setTimeCmd[11]])
        crcArray = self.calcCrc(stCmdBody)
        # attention: reverse the sequence
        setTimeCmd[12] = crcArray[1]
        setTimeCmd[13] = crcArray[0]
        return setTimeCmd

class MsgParser:
    def getCardCnt(self, byteValue):
        b = bitstring.BitArray(uint=byteValue, length = 8)
        del b[:4]
        return b.uint

    def getCardId(self, cardInfoArray):
        cardIdByteArray = bytearray([cardInfoArray[0],
                                     cardInfoArray[1],
                                     cardInfoArray[2],
                                     cardInfoArray[3],
                                     cardInfoArray[4]])
        bId = bitstring.BitArray(cardIdByteArray)
        del bId[:4]
        return "%s" % bId.uint

    def getTimeStamp(self, cardInfoArray):
        tsByteArray = bytearray([cardInfoArray[5],
                                 cardInfoArray[6],
                                 cardInfoArray[7]])
        bTs = bitstring.BitArray(tsByteArray)
        day = bTs[0:5]
        hour = bTs[5:10]
        minute = bTs[10:16]
        second = bTs[16:22]
        return "%d-%d:%d:%d" % (day.uint, hour.uint, minute.uint, second.uint)

    def getCardInfo(self, buf, x):
        cardInfo = bytearray(8)
        for i in xrange(0, 8):
            cardInfo[i] = buf[7 + 8*x + i]
        return cardInfo

class CardManager():
    mySerial = serial.Serial('/dev/ttyAMA0', 9600, timeout=0)
    cmdGnrtr = CmdGenerator()
    msgParser = MsgParser()

    global prevAddr
    global prevSn
    global permissionToSnapshot

    def setPrevAddr(self, value):
        CardManager.prevAddr = value

    def setPrevSn(self, value):
        CardManager.prevSn = value

    def getPrevAddr(self):
        return CardManager.prevAddr

    def getPrevSn(self):
        return CardManager.prevSn

    def initCardRcvr(self, devId):
        rstCmd = CardManager.cmdGnrtr.gnrtRstCmd(devId)
        CardManager.mySerial.write(rstCmd)

    def setCardRcvrTime(self):
        setTimeCmd = CardManager.cmdGnrtr.gnrtSetTimeCmd()
        CardManager.mySerial.write(setTimeCmd)
        if(DEBUGMODE == True):
            print "set time to card receiver"
            logging.info("set time to card receiver")

    def sendQueryCmd(self, devId, lastAddr, lastSn):
        queryCmd = CardManager.cmdGnrtr.gnrtQueryCmd(devId, lastAddr, lastSn)
        CardManager.mySerial.write(queryCmd)

    def rcvLegalMsg(self, buf):
        if (len(buf) == 0):
            return False

        if(DEBUGMODE == True):
            logStr = binascii.hexlify(buf)
            logging.info(logStr)
            print logStr

        if ((buf[0] == b'\x7E')
            and (buf[1] == b'\x3E')
            and (buf[len(buf)-1] == b'\x3C')
            and (buf[4] == b'\x80')
            and (buf[6] != b'\x00')):
            return True
        else:
            if(DEBUGMODE == True):
                print "revceive illegal message"
                logging.info("revceive illegal message")

            return False

    def sendJson(self, cardNum, cards, timeString):
        global jsonQ
        if (cardNum > 1):
            delimiter = '|'
            cardString = delimiter.join(cards)
        else:
            cardString = cards[0] #use the [0] in case the string is wraped by []
        
        cardJson = {"card": cardString, "pass_time": timeString}
        jsonQ.put(cardJson)



    def saveResults(self, buf):
        cardNum = CardManager.msgParser.getCardCnt(ord(buf[6]))
        self.setPrevAddr(buf[2])
        self.setPrevSn(buf[5])

        # get the system time instead of rcvr time for now
        timeString = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
        cardString = []
        for x in xrange(0, cardNum):
            cardInfoByteArray = CardManager.msgParser.getCardInfo(buf, x)
            cardId = CardManager.msgParser.getCardId(cardInfoByteArray)
            # timeStamp = CardManager.msgParser.getTimeStamp(cardInfoByteArray)
            if(DEBUGMODE == True):
                name = threading.currentThread().getName()
                logStr = "%s: get card %s at %s " % (name, cardId, timeString)
                print logStr
		# print timeStamp
                logging.info(logStr)
            cardString.append(cardId)

        self.sendJson(cardNum, cardString, timeString)



    def startCapture(self):
        # if(DEBUGMODE == True):
            # print ord(self.getPrevAddr())
            # print ord(self.getPrevSn())
            # print "start capture"
        permissionToSnapshot.set()


    def stopCapture(self):
        self.setPrevAddr(0xFF)
        self.setPrevSn(0x00)
        if(DEBUGMODE == True):
            # print "capture siezed"
        permissionToSnapshot.clear()

    def queryCards(self, devId):
        self.setPrevAddr(0xFF)
        self.setPrevSn(0x00)
        timingCnt = 0
        while (1):
            # set card receiver's time every 8 hours
            timingCnt += 1
            if (timingCnt == 60*60*8):
            	self.setCardRcvrTime()
           	timingCnt = 0
         
            self.sendQueryCmd(devId, self.getPrevAddr(), self.getPrevSn())
            time.sleep(1)
            rcvd = CardManager.mySerial.read(150)
            if self.rcvLegalMsg(rcvd):
                self.saveResults(rcvd)
                self.startCapture()
            else:
                self.stopCapture()

if __name__ == '__main__':

    if os.path.isdir('/home/pi/ddd/data'):
        pass
    else:
        os.mkdir('/home/pi/ddd/data')

    LOG_FILE = "/home/pi/ddd/data/debug.log"
    logging.basicConfig(filename=LOG_FILE,level=logging.DEBUG)

    permissionToSnapshot = threading.Event()
    jsonQ = Queue()
    fileQ = Queue()
    threads = []

    # creat snapshot thread
    threads.append(T_SnapShot())
    # creat serial thread
    threads.append(T_Serial())
    # creat network thread
    threads.append(T_NetWork())
    # creat network thread
    threads.append(T_Uploader())

    # start threads
    for t in threads:
        t.setDaemon(True)
        t.start()

    for t in threads:
        t.join()

    print "main thread running"

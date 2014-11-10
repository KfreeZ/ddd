#!/usr/bin/env python  
import picamera
import string, threading, time
import serial
import crc16
import struct

class T_SnapShot(threading.Thread):
    def initCam(self):
        camera = picamera.PiCamera()
        camera.resolution = (2592, 1944)
        camera.start_preview()

    def __init__(self, num):
        threading.Thread.__init__(self)
        self._run_num = num
        self.initCam()

    def run(self):
        global count, mutex
        threadname = threading.currentThread().getName()
        for x in xrange(0, int(self._run_num)):
            mutex.acquire()
            count  = count + 1
            mutex.release()
            timeString = time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime(time.time()))
            # print timeString
            # camera.capture('%s.jpg' % timeString)
            # print time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime(time.time()))
            print threadname, x, count 
            time.sleep(1)



class T_Serial(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        cdMngr = CardManager()
        cdMngr.initCardRcvr(0x1)
        cdMngr.setCardRcvrTime()
        cdMngr.queryCards()

class SerialIO:
    

    def writeSerial(self, content):
        try:
            SerialIO.mySerial.write(content)
            print "write serial"
        except Exception, ex:
            print str(ex)

    def readSerial(self):
        print "read serial"

        
class CmdGenerator:
    # cmd = head + rcvrAddr + cmdLen + cmd + crc + tail
    VARIABLEBYTE = 0x00
    #                               ---head---  ---addr----   -len- -cmd- ---crc pt1--- ---crc pt2--- -tail
    template_ResetRcvr = bytearray([0x7E, 0x3E, VARIABLEBYTE, 0x02, 0x01, VARIABLEBYTE, VARIABLEBYTE, 0x3C])
    #                             ---head---  -id- -len- -cmd-  ---yr pt1---  ---yr pt2---  ----month---  ----date----  ----hour----  ----min-----  ----sec----- ---crc pt1--- ---crc pt2--- -tail
    template_SetTime = bytearray([0x7E, 0x3E, 0xFF, 0x09, 0x10, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, 0x3C])
    #                               ---head---  -----id-----  -len- -cmd- --prev addr-- ---prev sn---  ----rsrv----  ---crc pt1--- ---crc pt2-- -tail
    template_QueryCards = bytearray([0x7E, 0x3E, VARIABLEBYTE, 0x05, 0x01, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, 0x3C])

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
        qryCmdBody = bytearray([queryCmd[2], queryCmd[3], queryCmd[4], queryCmd[5], queryCmd[6], queryCmd[7]])
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
        stCmdBody = bytearray([setTimeCmd[2], setTimeCmd[3], setTimeCmd[4], setTimeCmd[5], setTimeCmd[6], setTimeCmd[7], setTimeCmd[8], setTimeCmd[9], setTimeCmd[10], setTimeCmd[11]])
        crcArray = self.calcCrc(stCmdBody)
        # attention: reverse the sequence
        setTimeCmd[12] = crcArray[1]
        setTimeCmd[13] = crcArray[0]
        return setTimeCmd

class CardManager:
    mySerial = serial.Serial('/dev/ttyAMA0', 9600, timeout=0)
    cmdGnrtr = CmdGenerator()
    DEBUGMODE = True
    global prevAddr
    global prevSn

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

    def sendQueryCmd(self, devId, lastAddr, lastSn):
        queryCmd = CardManager.cmdGnrtr.gnrtQueryCmd(devId, lastAddr, lastSn)
        CardManager.mySerial.write(queryCmd)

    def saveResults(self, buf):
        self.setPrevAddr(0xEE)
        self.setPrevSn(0x22)

    def startCapture(self):
        print self.getPrevAddr()
        print self.getPrevSn()

    def stopCapture(self):
        self.setPrevAddr(0xFF)
        self.setPrevSn(0x00)
        print self.getPrevAddr()
        print self.getPrevSn()

    def queryCards(self):
        # set the id = 1 for demo
        self.setPrevAddr(0xFF)
        self.setPrevSn(0x00)
        while (1):
            self.sendQueryCmd(1, self.getPrevAddr(), self.getPrevSn())
            time.sleep(1)
            rcvd = CardManager.mySerial.read(150)
            if self.saveResults(rcvd):
                self.startCapture()
            else:
                self.stopCapture()





if __name__ == '__main__':
    global count, mutex


    threads = []
    count = 1
    # create lock
    mutex = threading.Lock()

    # creat snap thread
    # threads.append(T_SnapShot(10))
    # creat serial thread
    threads.append(T_Serial())

    # start threads
    for t in threads:
        t.start()
    # wait for exit
    for t in threads:
        t.join()

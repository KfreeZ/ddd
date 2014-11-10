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
    mySerial = None
    def __init__(self):
        try:
            mySerial = serial.Serial('/dev/ttyAMA0', 9600, timeout=0)
            print mySerial.name
        except Exception, ex:
            print str(ex)


    def writeSerial(self, content):
        try:
            mySerial.write(content)
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
        resetCmd = template_ResetRcvr  
        resetCmd[2] = devId
        cmdBody = bytearray(resetCmd[2], resetCmd[3], resetCmd[4])
        crcArray = self.calcCrc(cmdBody)
        # attention: reverse the sequence
        ResetCmd[5] = crcArray[1]
        ResetCmd[6] = crcArray[0]

    def gnrtQueryCmd(self, devId, prevAddr, prevSn):
        queryCmd = template_ResetRcvr  
        queryCmd[2] = devId
        queryCmd[5] = prevAddr
        queryCmd[6] = prevAddr
        cmdBody = bytearray(queryCmd[2], queryCmd[3], queryCmd[4], queryCmd[5], queryCmd[6], queryCmd[7], queryCmd[8], queryCmd[9], queryCmd[10], queryCmd[11])
        crcArray = self.calcCrc(cmdBody)
        # attention: reverse the sequence
        queryCmd[8] = crcArray[1]
        queryCmd[9] = crcArray[0]

    def gnrtSetTimeCmd(self, devId):
        setTimeCmd = template_SetTime
        timeByteArray = self.getTimebyteArray()
        for x in xrange(0, 7):
            setTimeCmd[5+x] = timeByteArray[x]
        cmdBody = bytearray(queryCmd[2], queryCmd[3], queryCmd[4], queryCmd[5], queryCmd[6], queryCmd[7])
        crcArray = self.calcCrc(cmdBody)
        # attention: reverse the sequence
        setTimeCmd[12] = crcArray[1]
        setTimeCmd[13] = crcArray[0]

class CardManager:
    sIO = None
    def __init__(self):
        sIO = SerialIO()
        cmdGnrtr = CmdGenerator();

    def initCardRcvr(self, devId):
        rstCmd = cmdGnrtr.gnrtRstCmd(addr)
        sIO.writeSerial(rstCmd)

    def setCardRcvrTime(self, devId):
        setTimeCmd = cmdGnrtr.gnrtSetTimeCmd(devId)
        sIO.writeSerial(setTimeCmd)

    def readAllCards(self, devId):
        queryCmd = cmdGnrtr.gnrtQueryCmd(devId, 0xFF, 0x00)
        sIO.writeSerial(queryCmd)

    def saveResults(self):
        print "save results"

    def clearOldcardsAndReadNewCards(self):
        print "analyzing..."

    def queryCards(self):
        # set the id = 1 for demo
        self.readAllCards(1)
        while self.alive:
            self.saveResults();
            self.clearOldcardsAndReadNewCards()
            time.sleep(1);




if __name__ == '__main__':
    global count, mutex


    threads = []
    count = 1
    # create lock
    mutex = threading.Lock()

    # creat snap thread
    threads.append(T_SnapShot(10))
    # creat serial thread
    threads.append(T_Serial())

    # start threads
    for t in threads:
        t.start()
    # wait for exit
    for t in threads:
        t.join()

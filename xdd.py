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
    #                             ---head---  -ad- -len- -cmd-  ---yr pt1---  ---yr pt2---  ----month---  ----date----  ----hour----  ----min-----  ----sec----- ---crc pt1--- ---crc pt2--- -tail
    template_SetTime = bytearray([0x7E, 0x3E, 0xFF, 0x09, 0x10, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, VARIABLEBYTE, 0x3C])
    #                               ---head---  -----addr----  -len- -cmd- ---crc pt1--- ---crc pt2-- -tail
    template_QueryCards = bytearray([0x7E, 0x3E, VARIABLEBYTE, 0x05, 0x01, VARIABLEBYTE, VARIABLEBYTE, 0x3C])

    def calcCrc(self, bytearray):
        retArray = [0, 0]
        crcValue = crc16.crc16xmodem(buffer(bytearray))
        crcByteArray = struct.unpack("2b", struct.pack("H", crcValue))
        retArray[0] = crcByteArray[1]
        retArray[1] = crcByteArray[0]
        return retArray

    def gnrtRstCmd(self, devId):
        

class CardManager:
    sIO = None
    def __init__(self):
        sIO = SerialIO()
        cmdGnrtr = CmdGenerator();

    def initCardRcvr(self, addr):
        initCmd = CmdGenerator.template_ResetRcvr
        initCmd[2] = addr
        cmdGnrtr.gnrtRstCmd(initCmd)
        sIO.writeSerial(initCmd)

    def setCardRcvrTime(self):
        print "set time to card receiver"

    def readAllCards(self, rcvrId):
        print "first read from receiver"

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

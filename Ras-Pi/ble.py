import bluepy
import binascii
import time
import threading
HANDLE_DATA = 0x002a
devadr = ''   # ESP32 Address
connected_list = []
rec_time = {}

class MyDelegate(bluepy.btle.DefaultDelegate):
    def __init__(self, params,worker_id):
        bluepy.btle.DefaultDelegate.__init__(self)
        self.worker_id = worker_id

    def handleNotification(self, cHandle, data):
        global exflag
        global rec_time
        if cHandle == 0x002a:
            b="0x002a"
            #do something
        c_data = binascii.b2a_hex(data)
        print( "[worker%s] %s: %s" % (self.worker_id,b, c_data) )
        rec_time[self.worker_id] = time.time()

def worker(adr,worker_id):
    global devadr
    global rec_time
    global connected_list
    try:
        print( "worker%s: connecting" % (worker_id) )
        peri = bluepy.btle.Peripheral()
        peri.connect(adr, bluepy.btle.ADDR_TYPE_PUBLIC)
        print( "worker%s: connected" % (worker_id) )
        peri.withDelegate(MyDelegate(bluepy.btle.DefaultDelegate,worker_id))
        while True:
            peri.writeCharacteristic(HANDLE_DATA + 1, b'\x01\x00',True) #要求
            time.sleep(0.001)
            if  time.time() - rec_time[worker_id] > 5 :
                break
        peri.disconnect()
    except Exception as e:
        print(e)
        print( "worker%s: disconnected" % (worker_id) )
        connected_list.remove(devadr)
        devadr = ''

def main():
    global devadr
    global rec_time
    global connected_list
    counter=0
    while True :
        if devadr != '' :
            time.sleep(1)
            continue
        print("search ESP32")
        scanner = bluepy.btle.Scanner(0)
        devices = scanner.scan(1)  #1秒スキャン
        for device in devices:
            if connected_list.count(device.addr) >0 :
                continue
            for (adtype, desc, value) in device.getScanData():
                if value == "ESP32" :
                    print('======================================================')
                    print('address : %s' % device.addr)
                    print('addrType: %s' % device.addrType)
                    print('RSSI    : %s' % device.rssi)
                    devadr = device.addr
                    connected_list.append(device.addr)
                    print("found")
                    rec_time[counter] = time.time()
                    t = threading.Thread(target=worker, args=(device.addr,counter))
                    t.start()
                    time.sleep(2)
                    counter+=1


if __name__ == "__main__":
    main()
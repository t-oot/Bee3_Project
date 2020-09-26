#30秒ごとにスキャン (スキャン時は全デバイス切断する)
#同時接続対応
import bluepy
import binascii
import time
import threading
import requests
import struct
from datetime import datetime
##API
url_inout = "http://api.bee3.tokyo/inout/register"
headers = {
	"auth" : "LWwgrDhtPnwjhYw3YB7E"
}
#####

connected_list = {}
rec_time = {}
needClose=False
uuid="b0c8c0fa-6d46-11e8-adc0-fa7ae01bbebc" #必要に応じて変更する
def worker(dev,worker_id):
    global connected_list
    global uuid
    try:
        print( "worker%s: connecting" % (worker_id) )
        peri = bluepy.btle.Peripheral()
        peri.connect(dev,"public")
        print( "worker%s: connected" % (worker_id) )
        #peri.withDelegate(MyDelegate(bluepy.btle.DefaultDelegate,worker_id))
        while True:
            if needClose == True:
                break
            latestDataRow = peri.getCharacteristics(uuid=uuid)[0]
            dataRow = latestDataRow.read()
            print("worker%s: data=%s" % (worker_id,dataRow))
            (seq,DATA1, DATA2, DATA3) = struct.unpack('<Bhhh', dataRow) #受信データのデコード
            print("worker%s: [SEQ%s]decoded DATA1=%s DATA2=%s DATA3=%s" % (worker_id,seq,DATA1, DATA2, DATA3))
            #TODO: ESP32から見た他のESP32の検出結果を取得する
            time.sleep(1) #1秒ごとにデータ取得要求
        print( "worker%s: disconnected(Close needed)" % (worker_id) )
        peri.disconnect()
    except Exception as e:
        print("worker%s error:%s"%(worker_id,e))
        print( "worker%s: disconnected" % (worker_id) )
        #connected_list.pop(dev.addr)

def main():
    global devadr
    global connected_list
    global needClose
    counter=0
    scanner = bluepy.btle.Scanner()
    while True :
        #if devadr != '' :
        #    time.sleep(1)
        #    continue
        try:
            print("search ESP32")
            needClose=True
            time.sleep(2)
            devices = scanner.scan(3.0)  #1秒スキャン
            needClose=False
            connected_list_local = {}
            #TODO: 登録デバイスの取得
            for device in devices:
                for (adtype, desc, value) in device.getScanData():
                    if device.addrType =="public":
                        print('======================================================')
                        print('address : %s' % device.addr)
                        print('addrType: %s' % device.addrType)
                        print('RSSI    : %s' % device.rssi)
                        print('desc    : %s' % desc)
                        print('value    : %s' % value)
                        if device.addr in connected_list_local.keys() : #接続済みの場合はスキップ
                            print("(connected)")
                            continue
                        connected_list_local[device.addr]=1
                        print("[%s] found" % value)
                        if device.addr not in connected_list.keys() :
                            print("API processing...") #入館した
                            payloads = {
                            "mac" : device.addr,
                            "time": int(datetime.now().timestamp()),
                            "status": "enter"
                            }
                            r = requests.get(url_inout, headers=headers, params=payloads)
                            print("API processed RESULT=%s" % (r.status_code))
                            connected_list[device.addr]=1
                        #TODO: RSSI強度(or距離)の送信
                        t = threading.Thread(target=worker, args=(device,counter))
                        t.start()
                        print("connected ==>%s" %(counter))
                        time.sleep(0.4) #次の接続処理まで1秒待機
                        counter+=1
            print("Scan end")
            #退館チェック
            for d in list(connected_list.keys())[:]:
                if d not in connected_list_local.keys() :
                    print("API processing...") #退館した
                    payloads = {
                    "mac" : d,
                    "time": int(datetime.now().timestamp()),
                    "status": "exit"
                    }
                    r = requests.get(url_inout, headers=headers, params=payloads)
                    print("API processed RESULT=%s" % (r.status_code))
                    connected_list.pop(d)

        except Exception as e:
            print(e)
            scan=False
            print( "scanner error")
            time.sleep(5)
        time.sleep(30) #スキャン間隔


if __name__ == "__main__":
    main()

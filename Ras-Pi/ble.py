#30秒ごとにスキャン (スキャン時は全デバイス切断する)hh
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

def temp_send(mac,taion, situon):
    global headers
    url = "http://api.bee3.tokyo/temp/register"
    payloads = {
        "mac" : mac,
        "temp1" : taion,
        "temp2" : situon
    }
    r = requests.get(url, headers=headers, params=payloads)
    return r.status_code


def rssi_send(dev_value,mac_value,rssi_value):
    global headers
    url = "http://api.bee3.tokyo/rssi/register"
    payloads = {
        "mac1" : dev_value,
        "mac2" : mac_value,
        "rssi" : rssi_value
    }
    r = requests.get(url, headers=headers, params=payloads)
    return r.status_code




connected_list = {}
rec_time = {}
needClose=False
uuid="b0c8c0fa-6d46-11e8-adc0-fa7ae01bbebc" #必要に応じて変更する
uuid2="b1c8c0fa-6d46-11e8-adc0-fa7ae01bbebc" #必要に応じて変更する
def worker(dev,worker_id):
    global connected_list
    global uuid
    global uuid2
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
            print(temp_send(mac=dev.addr ,taion=DATA2, situon=DATA1))
            #TODO: ESP32から見た他のESP32の検出結果を取得する
            latestDataRow = peri.getCharacteristics(uuid=uuid2)[0]
            dataRow = latestDataRow.read()
            #print("worker%s: data2=%s" % (worker_id,dataRow))
            for i in range(30):
                offset = i*7
                macadr = format(dataRow[offset+0], 'x').zfill(2)+":"+format(dataRow[offset+1], 'x').zfill(2)+":"+format(dataRow[offset+2], 'x').zfill(2)+":"+format(dataRow[offset+3], 'x').zfill(2)+":"+format(dataRow[offset+4], 'x').zfill(2)+":"+format(dataRow[offset+5], 'x').zfill(2)
                if macadr=="00:00:00:00:00:00" :
                    break
                print("worker%s: %s RSSI=-%s" % (worker_id,macadr,dataRow[offset+6]))
                if macadr=="fc:f5:c4:05:b1:ee" or "fc:f5:c4:05:af:7e":
                    print(rssi_send(dev_value=dev.addr,mac_value=macadr,rssi_value=dataRow[offset+6]))
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
            time.sleep(1.5)
            devices = scanner.scan(1.0)  #1秒スキャン
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
                            #"time": int(datetime.now().timestamp()),
                            "status": "enter",
                            "floor": 1
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
                #"time": int(datetime.now().timestamp()), timeパラメータを省略するとサーバー側に到達した時間が登録される
                "status": "exit",
                "floor": 1
                    }
                    r = requests.get(url_inout, headers=headers, params=payloads)
                    print("API processed RESULT=%s" % (r.status_code))
                    connected_list.pop(d)

        except Exception as e:
            print(e)
            scan=False
            print( "scanner error")
            time.sleep(5)
        if len(connected_list) >0 :
            time.sleep(30) #スキャン間隔


if __name__ == "__main__":
    main()

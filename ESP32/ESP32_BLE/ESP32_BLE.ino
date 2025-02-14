#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <esp_gatts_api.h>
#include <Wire.h>
#include <Adafruit_MLX90614.h> //温度のやつ
#include <BLEClient.h> //rssiの取得


// See the following for generating UUIDs:
// https://www.uuidgenerator.net/

#define SENSOR_UUID     "b0c8be70-6d46-11e8-adc0-fa7ae01bbebc"
#define LATESTDATA_UUID "b0c8c0fa-6d46-11e8-adc0-fa7ae01bbebc"

#define SENSOR_UUID2     "b1c8be70-6d46-11e8-adc0-fa7ae01bbebc"
#define LATESTDATA_UUID2 "b1c8c0fa-6d46-11e8-adc0-fa7ae01bbebc"

Adafruit_MLX90614 mlx = Adafruit_MLX90614();

BLEScan* pBLEScan;

String near1[30]; //mac
uint8_t  near2[30];  //rssi
int near_count = 0;
void bdaDump(esp_bd_addr_t bd) {
  for (int i = 0; i < ESP_BD_ADDR_LEN; i++) {
    Serial.printf("%02x", bd[i]);
    if (i < ESP_BD_ADDR_LEN - 1) {
      Serial.print(":");
    }
  }
};

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer, esp_ble_gatts_cb_param_t* param) {
      Serial.print("connected from: ");
      bdaDump(param->connect.remote_bda);
      Serial.println("");

      esp_ble_conn_update_params_t conn_params = {0};
      memcpy(conn_params.bda, param->connect.remote_bda, sizeof(esp_bd_addr_t));
      conn_params.latency = 0;
      conn_params.max_int = 0x20;    // max_int = 0x20*1.25ms = 40ms
      conn_params.min_int = 0x10;    // min_int = 0x10*1.25ms = 20ms
      conn_params.timeout = 400;    // timeout = 400*10ms = 4000ms
      //start sent the update connection parameters to the peer device.
      esp_ble_gap_update_conn_params(&conn_params);
    };

    void onDisconnect(BLEServer* pServer) {
      Serial.println("disconnected");
    }
};

uint8_t seq = 0;

//温度を送る
class dataCb: public BLECharacteristicCallbacks {
    void onRead(BLECharacteristic *pChar) {
      uint8_t buf[7];
      Serial.println("load");
      //// 送りたいデータ(とりあえず3つ)
      //// TODO:ここにセンサデータを代入する
      uint16_t DATA1 = mlx.readObjectTempC() * 100; //体温
      uint16_t DATA2 = mlx.readAmbientTempC() * 100; //気温
      uint16_t DATA3 = 12;
      ///
      memset(buf, 0, sizeof buf);               // バッファーを0クリア
      buf[0] = seq++;                           // シーケンス番号をバッファーにセット
      buf[1] = (uint8_t)(DATA1 & 0xff);
      buf[2] = (uint8_t)((DATA1 >> 8) & 0xff);
      buf[3] = (uint8_t)(DATA2 & 0xff);
      buf[4] = (uint8_t)((DATA2 >> 8) & 0xff);
      buf[5] = (uint8_t)(DATA3 & 0xff);
      buf[6] = (uint8_t)((DATA3 >> 8) & 0xff);
      pChar->setValue(buf, sizeof buf);         // データを書き込み
    }
};
//RSSIの一覧を送る
class dataCb2: public BLECharacteristicCallbacks {
    void onRead(BLECharacteristic *pChar) {
      uint8_t buf[7*30];
      Serial.println("load2");
      for (int i = 0; i < 30; i++) {
        int offset = i * 7;
        String mac = near1[i];
        mac.replace(":", "");
         String mac2 = mac.substring(0, 5+1);
         mac = mac.substring(6, 11+1);
        Serial.println("1:"+mac);
         Serial.println("2:"+mac2);
             Serial.println(near2[i]);
        byte macByte[3];
        unsigned long number = strtoul( mac.c_str(), nullptr, 16);
         Serial.println(number);
        for (int j = 3-1; j >= 0; j--) // start with lowest byte of number
        {
          macByte[j] = number & 0xFF;  // or: = byte( number);
          number >>= 8;            // get next byte into position
        }
      byte macByte2[3];
     number = strtoul( mac2.c_str(), nullptr, 16);
         Serial.println(number);
        for (int j = 3-1; j >= 0; j--) // start with lowest byte of number
        {
          macByte2[j] = number & 0xFF;  // or: = byte( number);
          number >>= 8;            // get next byte into position
        }

        buf[offset + 0] = (uint8_t)(macByte2[0]);
        buf[offset + 1] = (uint8_t)(macByte2[1]);
        buf[offset + 2] = (uint8_t)(macByte2[2]);
        buf[offset + 3] = (uint8_t)(macByte[0]);
        buf[offset + 4] = (uint8_t)(macByte[1]);
          buf[offset + 5] = (uint8_t)(macByte[2]);
        buf[offset + 6] = (uint8_t)(near2[i]);
      }
      pChar->setValue(buf, sizeof buf);         // データを書き込み
    }
};

class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
      //TODO これらのデータをどこか変数において、要求があったときにデバイスアドレスとRSSIを送信できるようにする
      String info = advertisedDevice.toString().c_str();
      int idx = info.indexOf("Rssi: ");
      int idx2 = info.indexOf("Address: ") + 9;
      if (idx == -1) {
        Serial.printf("No RSSi");
      } else {
        String mac  =  info.substring(idx2, idx2 + 17);
        info  = info.substring(idx+1+6);
        //Serial.printf("Advertised Device: %s ; RSSI=%s\n", advertisedDevice.toString().c_str(), info.c_str());
        if (near_count <= 30) {
          near1[near_count] = mac;
                Serial.println(info.c_str());
          near2[near_count] = (uint8_t)(atoi(info.c_str()));
          near_count++;
        }
      }
    }
};

void setup() {
  pinMode(SDA, INPUT_PULLUP); // SDAピンのプルアップの指定
  pinMode(SCL, INPUT_PULLUP); // SCLピンのプルアップの指定
  Wire.begin(SDA, SCL);

  Serial.begin(115200);
  Serial.println("Starting BLE work!");

  for (int i = 0; i < 30; i++) {
    near1[i] = "00:00:00:00:00:00"; //mac
    near2[i] = 0;  //rssi
  }

  BLEDevice::init("ESP32");                  // デバイスを初期化
  BLEServer *pServer = BLEDevice::createServer();    // サーバーを生成
  pServer->setCallbacks(new MyServerCallbacks());    // コールバック関数を設定

  BLEService *pService = pServer->createService(SENSOR_UUID);  // サービスを生成
  // キャラクタリスティクスを生成
  pService->createCharacteristic(LATESTDATA_UUID, BLECharacteristic::PROPERTY_READ)
  ->setCallbacks(new dataCb());                  // コールバック関数を設定

  pService->start();                                 // サービスを起動

  //TODO　もう1つサービスを作る　デバイスアドレスとRSSIを送るためのサービス
  BLEService *pService2 = pServer->createService(SENSOR_UUID2);
  pService2->createCharacteristic(LATESTDATA_UUID2, BLECharacteristic::PROPERTY_READ)
  ->setCallbacks(new dataCb2());                  // コールバック関数を設定

  pService2->start();

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SENSOR_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x7);  // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();

  Serial.println("Characteristic defined! Now you can read it in your phone!");

  //スキャンの設定
  pBLEScan = BLEDevice::getScan(); //create new scan
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(false); //active scan uses more power, but get results faster
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);  // less or equal setInterval value

  //温度センサ
  Serial.println("Adafruit MLX90614 test");
  mlx.begin();
}
void loop() {
  delay(5000);
  for (int i = 0; i < 30; i++) {
    near1[i] = "00:00:00:00:00:00"; //mac
    near2[i] = 0;  //rssi
  }
  near_count = 0;
  BLEScanResults foundDevices = pBLEScan->start(3, false); //3秒スキャン
  Serial.print("Devices found: ");
  Serial.println(foundDevices.getCount());
  Serial.println("Scan done!");
  pBLEScan->clearResults();
  Serial.print("温度は "); Serial.print(mlx.readObjectTempC()); Serial.println("*C");//温度センサ
}

# Sensor Suite for VOCs and Particulates

The idea of the codebase is to compare 4 different sensors manufactured by different brands to see if they can be used to corroborate data with existing VOC sensor deployment. 

The four sensors used in this case are - 
      1. A [Unbranded Gas Sensor](https://www.fruugo.us/hcho-vocs-sensor-gas-detection-sensor-module-detectors-0-1000ppm-ms1100/p-82360186-169946652?language=en&ac=google&utm_source=organic_shopping&utm_medium=organic) which sends data via an analog out pin. 
      2. A [Seeed Grove HCHO Sensor](https://www.digikey.com/en/products/detail/seeed-technology-co.,-ltd/101020001/5488087?utm_adgroup=Seeed%20Technology%20Co.%2C%20LTD.&utm_source=google&utm_medium=cpc&) which also sends data via an analog out pin.
      3. A [SGX Sensortech PS1-VOC](https://www.digikey.com/en/products/detail/amphenol-sgx-sensortech/PS1-VOC-10-MOD/16634087) which had to be queried using a command via UART.
      4. A [Sensirion SEN54](https://www.digikey.com/en/products/detail/sensirion-ag/SEN54-SDN-T/15903868) which had to be queried using a command via I2C.

The controller board to aggregate the data from these four sensors was an arduino [MKRWAN 1310](https://www.digikey.com/en/products/detail/sensirion-ag/SEN54-SDN-T/15903868). The reason this board was chosen was because two fold, first - the choice of board, a raspberry pi does not have ADCs, so I chose to use an arduino board I had lying around. Second, I needed a board that could supply 5V to the SEN54 device. One could choose any arduino board of their choosing, but be mindful of the voltage levels between the devices (especially for the communication lines.) 
    Note: Keep in mind, the MKRWAN 1310 does not supply 5V, it is merely connected to the USB 5V power line via a jumper, so if the MKRWAN device is not powered by USB, the 5V supply won't work. I tried powering the device with the RPi and running common ground with the MKRWAN 1310, but the communication did not work. 

For the data handling and pushing to the cloud, I used a [RPi 3B+](https://www.canakit.com/raspberry-pi-3-model-b-plus.html?cid=usd&src=raspberrypi&src=raspberrypi) which runs the parse_plants python script to query the MKRWAN 1310 for the data from all four sensors every 5 seconds and then publishes it to a server from where, the data can be visualized on Grafana. 


## Requirements: 
    For the arduino board:
        1. Install the Sensirion I2C SEN5X library on arduino library manager. 
        2. Use baud rate 9600 for the SGX Sensortech PS1-VOC device, that's the recommended speed on the datasheet. 
        3. Even though the SEN54 device needs a 5V supply, it works with a 3V3 tolerable I2C line, so no need to pull it up to 5V. 
        4. Remember that in case you are using the MKRWAN 1310 board, the board is rated for 3V3, meaning, the communication lines run on 3.3V, and so it should not be connected to 5V communication boards if both sides can take the lead on communication. 

    For the RPi:
        1. pip install paho-mqtt
        2. The mqtt package used in this code is [paho-mqtt](https://pypi.org/project/paho-mqtt/). 
        3. In the code, I removed MQTT details, please use your own broker, topic, port and credentials. 
        Note: I had to use client.tls_set() before the client could connect to the broker and publish messages. If your code is not working, this could be somthing useful for you. 
    

## Connection Diagram 

                                             ------------------
                                            |                  |
                                            |                  |
        ---------------                     |                  |                       -------------
       |            GND|                    |AREF            5V|                      |3V3          |
       |            3V3|                    |A0             VIN|                      |GND          |
       |             NC|                    |A1             VCC|             ---------|RX           | 
       |            SIG|-------------       |A2             GND|            |  -------|TX           |
        ---------------              |      |A3           RESET|            | |        -------------            
          Seeed Grove                |      |A4              TX|------------  |          PS1 - VOC          
          HCHO Sensor                 ------|A5              RX|--------------                       
                                      ------|A6             SCL|-------------                           
                                     |      |0              SDA|----------   |
        ---------------              |      |1             MISO|          |  |
       |            GND|             |      |~2             SCK|          |  |
       |           DOUT|             |      |~3            MOSI|          |  |
       |           AOUT|-------------       |~4                |          |  |         --------------
       |            3V3|                    |~5                |          |  |        |5V            |
        ---------------                     |                  |          |  |        |GND           |
           Unnamed Gas                      |                  |           --|--------|SDA           |
             Sensor                         |   MKR WAN 1310   |             ---------|SCL           |
                                             ------------------             ----------|SEL           |
                                                                           |          |NC            |
                                                                           |           --------------
                                                                           |                SEN54
                                                                        --------     
        * 3V3 on all boards connect to VCC on the MKRWAN 1310            ------
        * GND on all boards connect to GND on the MKRWAN 1310             ---- 
        * 5V on SEN54 connects to 5V on MKRWAN 1310                        --
        * SEL on SEN54 connects to GND on MKRWAN 1310
        * Seeed Grove HCHO sensor's analog output connects to A5 on the MKRWAN 1310
        * The unnamed gas sensor's AOUT connects to A6 on the MKRWAN 1310
        * SCL and SDA on the SEN54 connect to the SCL and SDA of the MKRWAN 1310 respectively
        * The Tx of the PS1-VOC connects to the Rx of the MKRWAN 1310 and vice versa.

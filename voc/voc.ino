/**********************************************************************************************************************************
# Program to aggregate sensor data and transfer to the RPi
# Author - Viswajith Govinda Rajan
# Ver 2.2
# Date - 1/24/2023
#
# Unnamed gas sensor - (I applied the same principle as that of grove hcho sensor and compute the ppm)
# Grove HCHO sensor - This sensor reports value in analog, this value is then resolved into ppm value
# EC Sense - This sensor reports values in ppb
# Sensirion SEN54 - This sensor reports PM1.0, PM2.5, PM4.0, PM10.0 and a VOC index ranging from 0 - 500
# The readings from these four sensors are then sent to a raspberry pi where the data will be further ingested to an influx db
# This sensor sends data once every five seconds.
# 
# Patch notes - Added a communication control, i.e, the RPi first requests data after which the MKRWAN aggregates data from the 4 
#               sensors and then sends it to the pi
#             - Changed the communication baud rate to 9600 
# Todo - SEN54 Fan clean operation
***********************************************************************************************************************************/


#include <Arduino.h>
#include <SensirionI2CSen5x.h>
#include <Wire.h>

#define GAS_SENSOR A6   // pin for unnamed gas sensor
#define HCHO_SENSOR A5  // pin for groove hcho sensor
#define DEBUG 0         // definition to toggle debug mode
#define R0_HCHO 38.35   // fixed value of the potentiometer on the Groove HCHO sensor
#define R0_GAS 4.95     // fixed value of the potentiometer on the Gas Sensor (most inexpensive one)
#define RPI 1
// #define SENSIRION_I2C 0x69

const unsigned long pauseInterval = 4500;
int value1 = 0;   // variable to store analog reading for unnamed gas sensor
int value2 = 0;   // variable to store analog reading for groove hcho sensor

// variables to store sensirion data below
float massConcentrationPm1p0;
float massConcentrationPm2p5;
float massConcentrationPm4p0;
float massConcentrationPm10p0;
float ambientHumidity;
float ambientTemperature;
float vocIndex;
float noxIndex;


// The used commands use up to 48 bytes. On some Arduino's the default buffer
// space is not large enough
#define MAXBUF_REQUIREMENT 48

#if (defined(I2C_BUFFER_LENGTH) &&                 \
     (I2C_BUFFER_LENGTH >= MAXBUF_REQUIREMENT)) || \
    (defined(BUFFER_LENGTH) && BUFFER_LENGTH >= MAXBUF_REQUIREMENT)
#define USE_PRODUCT_INFO
#endif

SensirionI2CSen5x sen5x;    // creating an object for the sensirion sensor

struct ec_command{
byte ec_sense_payload[9] = {0xFF,0x01,0x86,0x00,0x00,0x00,0x00,0x00,0x79};   // this has to be sent each time a query for data has to be made. The passive read does not seem to be working for some reason
}ec_command;

struct byte_values{
  uint8_t low, high;  // structure to store the converted byte values so it can be returned by the function
};

byte ec_sense_result[9];  // store the reading from the ec_sense module in this array. 


/* Function to compmute the ppm concentration for the groove and unnamed gas sensor. Takes in the analog value from sensor and computes the ppm value*/
float calculate_ppm(int gas_analog_reading, float R0){
  float sensor =0; static float result = 0;
  sensor = (1023.0/gas_analog_reading)-1;
  result = pow(10.0, ((log10 (sensor/R0) - 0.0827)/(-0.4807)));
  return result;
}

// convert the data from integer into two bytes so it can be sent over Serial
struct byte_values data_for_transmission(int value){
  struct byte_values result;
  result.low = value & 0x00FF;
  result.high = value >> 8;
  return result;
}

int float_to_int(float val){
  int result = (int) (val * 100);
  return result;
}

void run(){
   uint16_t error;
    char errorMessage[256];
    value1 = analogRead(GAS_SENSOR);    // poll unnamed gas sensor
    float gas = calculate_ppm(value1, R0_GAS);
    int gas_value = float_to_int(gas);
    byte_values gas_sensor = data_for_transmission(gas_value);

    value2 = analogRead(HCHO_SENSOR);   // poll groove hcho sensor
    float hcho = calculate_ppm(value2, R0_HCHO);
    int hcho_value = float_to_int(hcho);
    byte_values hcho_sensor = data_for_transmission(hcho_value);

    Serial1.write(ec_command.ec_sense_payload, 9); // ask ec_sense sensor for its measurement. 
    delay(500);                        // wait for 5 seconds because resolving the request might take some time. documentation mentioned <20s. 5s seems to work. 

    /* Check if data from ec_sense sensor is available. If it is, read it and store in a buffer. */
    if (Serial1.available()){
      int i = 0;
      while (Serial1.available()) {     // when receive buffer has data
        ec_sense_result[i++] = (byte)Serial1.read();
      }
    } 

  error = sen5x.readMeasuredValues( massConcentrationPm1p0, massConcentrationPm2p5, massConcentrationPm4p0, 
                                    massConcentrationPm10p0, ambientHumidity, ambientTemperature, vocIndex, noxIndex);  // read sensirion data

  int pm1p0 = float_to_int(massConcentrationPm1p0);
  int pm2p5 = float_to_int(massConcentrationPm2p5);
  int pm4p0 = float_to_int(massConcentrationPm4p0);
  int pm10p0 = float_to_int(massConcentrationPm10p0);
  int voc = float_to_int(vocIndex);

  byte_values pm_1p0 = data_for_transmission(pm1p0);
  byte_values pm_2p5 = data_for_transmission(pm2p5);
  byte_values pm_4p0 = data_for_transmission(pm4p0);
  byte_values pm_10p0 = data_for_transmission(pm10p0);
  byte_values voc_index = data_for_transmission(voc);

  if (error) {
    Serial.print("Error trying to execute readMeasuredValues(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
  }
  /*********************************************************************************************/

  /***************** Print values on serial display ********************************************/
  if (DEBUG == 1 && RPI == 0) {
  Serial.print("Gas Sensor value (ppm): ");
  Serial.print(gas);
  Serial.print(", ");
  Serial.println((gas_sensor.high << 8 | gas_sensor.low));
  Serial.print("HCHO Sensor value (ppm): ");
  Serial.print(hcho);
  Serial.print(", ");
  Serial.println((hcho_sensor.high << 8 | hcho_sensor.low));
  Serial.print("EC Sense value (ppb): ");
  Serial.println(ec_sense_result[6] << 8 | ec_sense_result[7]);
  Serial.print("MassConcentrationPm1p0: ");
  Serial.print(massConcentrationPm1p0);
  Serial.print(", ");
  Serial.println((pm_1p0.high << 8 | pm_1p0.low));
  Serial.print("MassConcentrationPm2p5: ");
  Serial.print(massConcentrationPm2p5);
  Serial.print(", ");
  Serial.println((pm_2p5.high << 8 | pm_2p5.low));
  Serial.print("MassConcentrationPm4p0: ");
  Serial.print(massConcentrationPm4p0);
  Serial.print(", ");
  Serial.println((pm_4p0.high << 8 | pm_4p0.low));
  Serial.print("MassConcentrationPm10p0: ");
  Serial.print(massConcentrationPm10p0);
  Serial.print(", ");
  Serial.println((pm_10p0.high << 8 | pm_10p0.low));
  Serial.print("VocIndex: ");
  Serial.print(vocIndex);
  Serial.print(", ");
  Serial.println((voc_index.high << 8 | voc_index.low));
  }
  /*********************************************************************************************/

  if (RPI){
    char payload[] = {gas_sensor.low, gas_sensor.high, hcho_sensor.low, hcho_sensor.high, ec_sense_result[7], ec_sense_result[6], pm_1p0.low, pm_1p0.high, pm_2p5.low, pm_2p5.high, pm_4p0.low, pm_4p0.high,
                      pm_10p0.low, pm_10p0.high, voc_index.low, voc_index.high,'\n'};
    Serial.write(payload, 17);
    }
    delay(4500);
}

// setup loop only runs once
void setup() {
// put your setup code here, to run once:

/********* Set pin modes for the analog pins ***********/
pinMode(GAS_SENSOR, INPUT);
pinMode(HCHO_SENSOR, INPUT);

Serial.begin(9600);     // initate serial communication with usb/rpi
Serial1.begin(9600);      // initate serial communication with ec_sense module

Wire.begin();

sen5x.begin(Wire);

uint16_t error;
char errorMessage[256];
error = sen5x.deviceReset();
if (error) {
    Serial.print("Error trying to execute deviceReset(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
}

// Start Measurement
error = sen5x.startMeasurement();
if (error) {
    Serial.print("Error trying to execute startMeasurement(): ");
    errorToString(error, errorMessage, 256);
    Serial.println(errorMessage);
}

delay(500);
}

// this is the main loop
void loop() {
  // run();
  if (Serial.available()){
    String data = Serial.readStringUntil('\n');
    if (data == "tx"){
        run();  
      }  
    else {
      if (DEBUG){ Serial.println("Wrong Command Sent");}
    }
  }
} 
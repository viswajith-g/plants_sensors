#define GAS_SENSOR A0   // pin for unnamed gas sensor
#define HCHO_SENSOR A1  // pin for groove hcho sensor
#define DEBUG 1         // definition to toggle debug mode
#define R0_HCHO 38.35   // fixed value of the potentiometer on the Groove HCHO sensor
#define R0_GAS 4.95     // fixed value of the potentiometer on the Gas Sensor (most inexpensive one)

byte ec_sense_payload[] = {0xFF,0x01,0x86,0x00,0x00,0x00,0x00,0x00,0x79};   // this has to be sent each time a query for data has to be made. The passive read does not seem to be working for some reason

/********* commands for the sensirion module. variable names reflect the command's utility ************/
byte sensirion_start_measurement[] = {0x00, 0x21};      
byte sensirion_start_measurement_gas_mode[] = {0x00, 0x37};
byte sensirion_stop_measurement[] = {0x01, 0x04};
byte sensirion_read_measured_values[] = {0x03, 0xC4};
byte sensirion_start_fan_cleaning[] = {0x56, 0x07};
byte sensirion_read_write_cleaning_interval[] = {0x80, 0x04};
byte sensirion_read_serial_number[] = {0xD0, 0x033};
byte sensirion_read_firmware_ver[] = {0xD1, 0x00};
byte sensirion_read_device_status[] = {0xD2, 0x06};
/*******************************************************************************************************/

byte ec_sense_result[9];  // store the reading from the ec_sense module in this array. 
int ec_sense_gas;         // variable used to store the actual gas concentration in ppb 

/* Function to compmute the ppm concentration for the groove and unnamed gas sensor. Takes in the analog value from sensor and computes the ppm value*/
double calculate_ppm(int gas_analog_reading, float R0){
  float sensor =0; double result = 0;
  sensor = (1023.0/gas_analog_reading)-1;
  result = pow(10.0, ((log10 (sensor/R0) - 0.0827)/(-0.4807)));
  return result;
}

// setup loop only runs once
void setup() {
// put your setup code here, to run once:

/********* Set pin modes for the analog pins ***********/
pinMode(GAS_SENSOR, INPUT);
pinMode(HCHO_SENSOR, INPUT);

Serial.begin(115200);     // initate serial communication with usb
Serial1.begin(9600);      // initate serial communication with ec_sense module

delay(1000);
}

// this is the main loop
void loop() {
// put your main code here, to run repeatedly:
int value1 = 0;   // variable to store analog reading for unnamed gas sensor
int value2 = 0;   // variable to store analog reading for groove hcho sensor

value1 = analogRead(GAS_SENSOR);    // poll unnamed gas sensor
double gas_sensor_result = calculate_ppm(value1, R0_GAS);
value2 = analogRead(HCHO_SENSOR);   // poll groove hcho sensor
double grove_hcho_result = calculate_ppm(value2, R0_HCHO);

Serial1.write(ec_sense_payload, 9); // ask ec_sense sensor for its measurement. 
delay(5000);                        // wait for 5 seconds because resolving the request might take some time. documentation mentioned <20s. 5s seems to work. 

/* Check if data from ec_sense sensor is available. If it is, read it and store in a buffer. */
if (Serial1.available()){
  int i = 0;
  while (Serial1.available()) {     // when receive buffer has data
    ec_sense_result[i++] = (byte)Serial1.read();
  }
  ec_sense_gas = ec_sense_result[6] * 256 + ec_sense_result[7];   // compute the ppb value in decimal representation
} 
/*********************************************************************************************/

/***************** Print values on serial display ********************************************/
if (DEBUG){
Serial.print("Gas Sensor value (ppm): ");
Serial.println(gas_sensor_result); // /82);
Serial.print("HCHO Sensor value (ppm): ");
Serial.println(grove_hcho_result);
Serial.print("EC Sense value (ppb): ");
Serial.println(ec_sense_gas);
/***** This block displays each byte of the ec_sense raw data per packet ******/
// for (int k = 0; k < 9; k++){
//   Serial.print(k);
//   Serial.print(": ");
//   Serial.println(ec_sense_result[k], HEX);
//   }
//   Serial.println();
}
/*********************************************************************************************/

delay(1000);  // wait for a second before taking next reading. can change this value depending on how often we want to measure. need to add 5 seconds from the ec_sense reading request however. 
}
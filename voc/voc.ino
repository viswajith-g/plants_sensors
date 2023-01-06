#define GAS_SENSOR A0
#define HCHO_SENSOR A1
#define DEBUG 1
#define R0_HCHO 38.35   // fixed value of the potentiometer on the Groove HCHO sensor
#define R0_GAS 4.95     // fixed value of the potentiometer on the Gas Sensor (most inexpensive one)

byte ec_sense_payload[] = {0xFF,0x01,0x86,0x00,0x00,0x00,0x00,0x00,0x79};   // this has to be sent each time a query for data has to be made. The passive read does not seem to be working for some reason

byte senserion_start_measurement[] = {0x00, 0x21};      
byte senserion_start_measurement_gas_mode[] = {0x00, 0x37};
byte senserion_stop_measurement[] = {0x01, 0x04};
byte senserion_read_measured_values[] = {0x03, 0xC4};
byte senserion_start_fan_cleaning[] = {0x56, 0x07};
byte senserion_read_write_cleaning_interval[] = {0x80, 0x04};
byte senserion_read_serial_number[] = {0xD0, 0x033};
byte senserion_start_measurement[] = {0xD1, 0x00};
byte senserion_read_device_status[] = {0xD2, 0x06};

byte ec_sense_result[9];
int ec_sense_gas;

double calculate_ppm(int gas_analog_reading, float R0){
  float sensor =0; double result = 0;
  sensor = (1023.0/gas_analog_reading)-1;
  result = pow(10.0, ((log10 (sensor/R0) - 0.0827)/(-0.4807)));
  return result;
}
  
void setup() {
// put your setup code here, to run once:

//SoftwareSerial Serial1(0,1);
pinMode(GAS_SENSOR, INPUT);
pinMode(HCHO_SENSOR, INPUT);
pinMode(GAS_RPI, OUTPUT);
pinMode(HCHO_RPI, OUTPUT);

Serial.begin(115200);
Serial1.begin(9600);

delay(1000);
}

void loop() {
// put your main code here, to run repeatedly:
int value1 = 0;
int value2 = 0;

value1 = analogRead(GAS_SENSOR);
double gas_sensor_result = calculate_ppm(value1, R0_GAS);
value2 = analogRead(HCHO_SENSOR);
double grove_hcho_result = calculate_ppm(value2, R0_HCHO);

Serial1.write(ec_sense_payload, 9);
delay(5000);
if (Serial1.available()){
  int i = 0;
  while (Serial1.available()) {     // when receive buffer has data
    ec_sense_result[i++] = (byte)Serial1.read();
  }
  ec_sense_gas = ec_sense_result[6] * 256 + ec_sense_result[7]; 
} 
if (DEBUG){
Serial.print("Gas Sensor value (ppm): ");
Serial.println(gas_sensor_result); // /82);
Serial.print("HCHO Sensor value (ppm): ");
Serial.println(grove_hcho_result);
Serial.print("EC Sense value (ppb): ");
Serial.println(ec_sense_gas);
// for (int k = 0; k < 9; k++){
//   Serial.print(k);
//   Serial.print(": ");
//   Serial.println(ec_sense_result[k], HEX);
//   }
//   Serial.println();
}
delay(1000);
}
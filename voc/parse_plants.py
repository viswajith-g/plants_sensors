#!/usr/bin/env python3

#################################################################################################################
# Python program to receive data from MKRWAN 1310
# Author - Viswajith Govinda Rajan
# Ver 1.0
# Date - 1/13/2023
#
# This piece of code receives the data from all four air sensors attached to the MKRWAN, decodes and resolves 
# it into a human readable format. The data from the sensors are as follows:
# Unnamed gas sensor - (I applied the same principle as that of grove hcho sensor and compute the ppm)
# Grove HCHO sensor - This sensor reports value in analog, this value is then resolved into ppm value
# EC Sense - This sensor reports values in ppb
# Sensirion SEN54 - This sensor reports PM1.0, PM2.5, PM4.0, PM10.0 and a VOC index ranging from 0 - 500
#
#
# Todo:
# Need to do something with the data - whether it be saved locally, or be pushed to the cloud has to be discussed
####################################################################################################################

import serial
import time

payload_resolved = [0] * 17		# list to store the incoming data from UART
payload_decoded = [0] * 16		# list to store the integer values. it is only 16 bytes instead of 17 because we have no use for the newline character
debug = False		# macro used to toggle print statements for debug


''' This function converts the two different bytes into a single reading. It takes the low byte and high byte and shifts the high byte to the left before oring
with the low byte to get the full 2 byte data'''
def resolve_readings(low, high, scale = 100):
	result = float(high << 8 | low) / scale
	# print("resolution value: {}\n".format(result))
	return result

'''This function takes the length of the payload that needs resolving from ASCII to int and converts each byte to int and stores that data in a list which is 
returned'''
def decode_payload(idx):
	result = [0] * 17
	for i in range(idx-1):
		if payload_resolved[i] == 0:
			result[i] = 0
		else:	 
			result[i] = int(payload_resolved[i], 16)
	if debug:
		print("decode value: {}\n".format(result))
	return result

if __name__ == '__main__':		# start the program
    ser = serial.Serial('/dev/ttyACM0', 115200)		# setup the UART channel
    ser.reset_input_buffer()						# clear UART buffer

    while True:
	
	payload = ser.readline()	# read UART line
	# print(payload)
	for vals in payload:
        	payload_resolved[payload.index(vals)] = hex(ord(vals))	# store the UART data into a list
	payload_decoded = decode_payload(len(payload_resolved))			# convert the 
	if debug:
		print("original payload is: {}".format(payload))
		print('\n')
		print("decoded payload is: {}".format(payload_decoded))
	# print(payload_resolved)

	''' This block resolves the bytes of data into the actual sensor reading '''
	gas_sensor = resolve_readings(payload_decoded[0], payload_decoded[1])
	hcho_sensor = resolve_readings(payload_decoded[2], payload_decoded[3])
	ec_sense = resolve_readings(payload_decoded[4], payload_decoded[5], 1)
	pm1p0 = resolve_readings(payload_decoded[6], payload_decoded[7])
	pm2p5 = resolve_readings(payload_decoded[8], payload_decoded[9])
	pm4p0 = resolve_readings(payload_decoded[10], payload_decoded[11])
	pm10p0 = resolve_readings(payload_decoded[12], payload_decoded[13])
	voc = resolve_readings(payload_decoded[14], payload_decoded[15])
	if debug:
		print("Gas Sensor reading in ppm is: {}".format(gas_sensor))
		print("HCHO Sensor reading in ppm is: {}".format(hcho_sensor))
		print("EC Sense reading in ppb is: {}".format(ec_sense))
		print("PM 1.0 reading in ug/m3 is: {}".format(pm1p0))
		print("PM 2.5 reading in ug/m3 is: {}".format(pm2p5))
		print("PM 4.0 reading in ug/m3 is: {}".format(pm4p0))
		print("PM 10.0 reading in ug/m3 is: {}".format(pm10p0))
		print("VOC index (0-500) is: {}\n".format(voc))
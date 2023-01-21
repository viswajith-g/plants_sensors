#!/usr/bin/env python

#################################################################################################################
# Python program to receive data from MKRWAN 1310
# Author - Viswajith Govinda Rajan
# Ver 2.0
# Date - 1/20/2023
#
# This piece of code receives the data from all four air sensors attached to the MKRWAN, decodes and resolves 
# it into a human readable format. The data from the sensors are as follows:
# Unnamed gas sensor - (I applied the same principle as that of grove hcho sensor and compute the ppm)
# Grove HCHO sensor - This sensor reports value in analog, this value is then resolved into ppm value
# EC Sense - This sensor reports values in ppb
# Sensirion SEN54 - This sensor reports PM1.0, PM2.5, PM4.0, PM10.0 and a VOC index ranging from 0 - 500
#
# Publishes the data to MQTT broker from where it will be ingested by the influx platform
# 
####################################################################################################################

import serial
import datetime
from paho.mqtt import client as mqtt
import json
import os
import sys
import csv

def flags_init():
	global debug_mqtt, debug_print, csv_header_flag, csv_active_flag
	debug_mqtt = False			# flag to check json payload for mqtt
	debug_print = False			# flag to print stuff for debug			
	csv_header_flag = False		# flag to check if header has to be inserted for csv
	csv_active_flag = False		# flag to check if csv part of the code has to be run

'''mqtt_init() initializes the parameters needed to make a connection with and publish data to the MQTT broker '''
def mqtt_init():
	global MQTT_TOPIC_NAME, MQTT_BROKER, MQTT_PORT, username, password, client_id
	MQTT_TOPIC_NAME = 'gateway-data'
	MQTT_BROKER = ''
	MQTT_PORT = ''
	username = ''
	password = ''
	client_id = 'RPI_001'

'''lists_and_dicts_init() initilalizes the lists and dictionary that contain the data from uart, decoded data, sensor data, etc.'''
def lists_and_dicts_init():
	global payload_resolved, payload_decoded, sensor_data, influx_list, influx_dict, influx_json
	payload_resolved = [0] * 17		# list to store the incoming data from UART
	payload_decoded = [0] * 16		# list to store the integer values. it is only 16 bytes instead of 17 because we have no use for the newline character
	sensor_data = [0] * 8			# list to store the float values of the sensor readings
	influx_list = ["gas_sensor_ppm", "hcho_sensor_ppm", "ec_sense_ppb", "PM_1.0", "PM_2.5", "PM_4.0", "PM_10.0", "VOC_Index"]
	influx_dict = {
				"gas_sensor_ppm": 0.0,
				"hcho_sensor_ppm": 0.0,
				"ec_sense_ppb": 0.0,
				"PM_1.0": 0.0,
				"PM_2.5": 0.0,
				"PM_4.0": 0.0,
				"PM_10.0": 0.0,
				"VOC_Index": 0.0,
				"_meta": {"device_id" : "RPI_001", 
							"location" : "Conf Room 211", 
							"location_specific" : "Near Sensor B", 
							"sensors" : "gas_sensor, grove_hcho, ec_sense, SEN54"}
				}
	influx_json = json.dumps(influx_dict)

'''detect_path() checks for the path of the file and returns the cwd'''
def detect_path():
	global path, csv_header_flag
	if getattr(sys, 'frozen', False):
		application_path = sys._MEIPASS
	elif __file__:
		application_path = os.path.dirname(__file__)
	return application_path

'''path_check() checks for the absolute path of the file and sets/resets the header flag accordingly'''
def path_check():
	global path, csv_header_flag
	cwd_path = os.path.realpath(os.path.join(os.getcwd(), detect_path()))
	# print(cwd_path)
	csv_abs_path = 'sensor_data.csv'
	path = os.path.join(cwd_path, csv_abs_path)
	path_exists = os.path.exists(path)
	# print(path_exists)
	if path_exists:
		csv_header_flag = True
	else:
		csv_header_flag = False

''' This function converts the two different bytes into a single reading. It takes the low byte and high byte and shifts the high byte to the left before oring
with the low byte to get the full 2 byte data'''
def resolve_readings(low, high, scale = 100):
    result = float(high << 8 | low) / scale
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
	if debug_print:
		print("decode value: {}\n".format(result))
	return result

'''on_connect() is a built in paho-mqtt function that returns the status of the connection when a connect request is made'''
def on_connect(client, userdata, flags, rc):
	print("Connection returned result: "+connack_string(rc))
	# if rc == 0:
	# 	print('Connected to MQTT broker\n')
	# else:
	# 	print('Failed to connect to MQTT broker, reason is {}\n'.format(rc))

'''mqtt_connect() connects to the mqtt broker and returns the client object'''
def mqtt_connect():
	client = mqtt.Client(client_id)
	client.username_pw_set(username, password)
	client.on_connect = on_connect
	client.connect(MQTT_BROKER, MQTT_PORT)
	print('connection attempt made\n')
	return client

'''mqtt_publish takes in the client object from mqtt_connect as an argument and publishes the message to said client'''
def mqtt_publish(client):
	try:
		msg_result = client.publish(MQTT_TOPIC_NAME, influx_json)
	except:
		print('There was a problem publishing the message\n')
	status = msg_result[0]
	if status == 0:
		print('Sent message successfully\n')
	else:
		print('Failed to send message\n')

'''write_to_csv() writes the sensor data to a csv file to enable offline monitoring'''
def write_to_csv():
	global csv_header_flag, path
	with open (path, 'a') as logfile:
		file = csv.writer(logfile)
		if not csv_header_flag:
			file.writerow(['Timestamp', 'Gas Sensor (PPM)', 'HCHO Sensor (PPM)', 'EC Sense (PPB)', 'PM 1.0 (ug/m3)', 'PM 2.5 (ug/m3)', 
							'PM 4.0 (ug/m3)', 'PM 10.0 (ug/m3)', 'VOC Index (0-500)'])
			file.writerow([datetime.datetime.now(), influx_dict["gas_sensor_ppm"], influx_dict['hcho_sensor_ppm'], influx_dict['ec_sense_ppb'], influx_dict['PM_1.0'], 
							influx_dict['PM_2.5'], influx_dict['PM_4.0'], influx_dict['PM_10.0'], influx_dict['VOC_Index']])
			csv_header_flag = True
		else:
			file.writerow([datetime.datetime.now(), influx_dict["gas_sensor_ppm"], influx_dict['hcho_sensor_ppm'], influx_dict['ec_sense_ppb'], influx_dict['PM_1.0'], 
							influx_dict['PM_2.5'], influx_dict['PM_4.0'], influx_dict['PM_10.0'], influx_dict['VOC_Index']])

'''mqtt_handler() is called in the main loop to take care of all the mqtt operations for a loop'''
def mqtt_handler():
	mqtt_client = mqtt_connect()
	mqtt_client.loop_start()
	mqtt_publish(mqtt_client)
	mqtt_client.loop_stop()
	mqtt_client.disconnect()


if __name__ == '__main__':		# start the program

	flags_init()
	lists_and_dicts_init()
	mqtt_init()
	if csv_active_flag:			# check if csv file exists, given the csv flag is set
		path_check()
		
	ser = serial.Serial('/dev/ttyACM0', 115200)		# setup the UART channel
	ser.reset_input_buffer()						# clear UART buffer
	while True:
		payload = ser.readline()	# read UART line
		# print(payload)
		for vals in payload:
			payload_resolved[payload.index(vals)] = hex(ord(vals))	# store the UART data into a list
		payload_decoded = decode_payload(len(payload_resolved))
		if debug_print:
			print("original payload is: {}".format(payload))
			print("decoded payload is: {}".format(payload_decoded))
		# print(payload_resolved)

		''' This block resolves the bytes of data into the actual sensor reading '''
		sensor_data[0] = resolve_readings(payload_decoded[0], payload_decoded[1])		# gas_sensor
		sensor_data[1] = resolve_readings(payload_decoded[2], payload_decoded[3])		# hcho sensor
		sensor_data[2] = resolve_readings(payload_decoded[4], payload_decoded[5], 1)	# ec sense 
		sensor_data[3] = resolve_readings(payload_decoded[6], payload_decoded[7])		# pm 1.0
		sensor_data[4] = resolve_readings(payload_decoded[8], payload_decoded[9])		# pm 2.5
		sensor_data[5] = resolve_readings(payload_decoded[10], payload_decoded[11])		# pm 4.0
		sensor_data[6] = resolve_readings(payload_decoded[12], payload_decoded[13])		# pm 10.0
		sensor_data[7] = resolve_readings(payload_decoded[14], payload_decoded[15])		# voc

		for values in sensor_data:
			influx_dict[influx_list[sensor_data.index(values)]] = sensor_data[sensor_data.index(values)]

		influx_json = json.dumps(influx_dict)

		if debug_mqtt:
			print(influx_json)
		
		if csv_active_flag:
			write_to_csv()
		
		if debug_print:
			print("Timestamp: {}".format(datetime.datetime.now()))
			print("Gas Sensor reading in ppm is: {}".format(sensor_data[0]))
			print("HCHO Sensor reading in ppm is: {}".format(sensor_data[1]))
			print("EC Sense reading in ppb is: {}".format(sensor_data[2]))
			print("PM 1.0 reading in ug/m3 is: {}".format(sensor_data[3]))
			print("PM 2.5 reading in ug/m3 is: {}".format(sensor_data[4]))
			print("PM 4.0 reading in ug/m3 is: {}".format(sensor_data[5]))
			print("PM 10.0 reading in ug/m3 is: {}".format(sensor_data[6]))
			print("VOC index (0-500) is: {}".format(sensor_data[7]))

		mqtt_handler()		# mqtt actions
		
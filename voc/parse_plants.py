#!/usr/bin/env python
# coding=utf-8

#################################################################################################################
# Python program to receive data from MKRWAN 1310
# Author - Viswajith Govinda Rajan
# Ver 2.4
# Date - 1/23/2023
#
# This piece of code receives the data from all four sensors attached to the MKRWAN, decodes and publishes the 
# data to MQTT broker from where it will be ingested by the influx platform. The four sensors are:
#
# Unnamed gas sensor - (I applied the same principle as that of grove hcho sensor and compute the ppm)
# Grove HCHO sensor - This sensor reports value in analog, this value is then resolved into ppm value
# EC Sense - This sensor reports values in ppb
# Sensirion SEN54 - This sensor reports pm1.0, pm2.5, pm4.0, pm10.0 and a VOC index ranging from 0 - 500
#
# patch notes 	- added client.reconnect() in case the built in reconnect fails when a disconnect happens
# 				- removed clean session
# 				- added logging capability
# 				- added a try - except block so no data is published when the sensor has serial read issues
####################################################################################################################

import serial
import datetime
from paho.mqtt import client as mqtt
import json
import os
import sys
import csv
import logging
import time

def flags_init():
	global debug_mqtt, debug_print, csv_header_flag, csv_active_flag, i2c_data_flag, exception_flag
	debug_mqtt = False			# flag to check json payload for mqtt
	debug_print = False			# flag to print stuff for debug			
	csv_header_flag = False		# flag to check if header has to be inserted for csv
	csv_active_flag = True		# flag to check if csv part of the code has to be run
	exception_flag = False

def logging_init():
	log_filename = 'parse_plants_operation.log'
	log_directory = 'log'

	if not os.path.exists(log_directory):
		os.makedirs(log_directory)

	logging.basicConfig(filename =log_directory+'/'+log_filename, level=logging.INFO) # formating log file
	logging.info('===================================================================')
	logging.info('[Events]: Parse Plants script started at '+str(datetime.utcnow().isoformat()))

'''mqtt_init() initializes the parameters needed to make a connection with and publish data to the MQTT broker '''
def mqtt_init():
	global MQTT_TOPIC_NAME, MQTT_BROKER, MQTT_PORT, username, password, client_id
	MQTT_TOPIC_NAME = ''
	MQTT_BROKER = ''
	MQTT_PORT = ''
	username = ''
	password = ''
	client_id = ''

'''lists_and_dicts_init() initilalizes the lists and dictionary that contain the data from uart, decoded data, sensor data, etc.'''
def lists_and_dicts_init(id):
	global payload_resolved, payload_decoded, sensor_data, gas_dict, grove_dict, ps1_dict, sen54_dict
	payload_resolved = [0] * 17		# list to store the incoming data from UART
	payload_decoded = [0] * 16		# list to store the integer values. it is only 16 bytes instead of 17 because we have no use for the newline character
	sensor_data = [0] * 8			# list to store the float values of the sensor readings
	
	gas_dict = {
				"voc_ppm": 0.0,
				"_meta": {"device_id" : id, 
							"sensor" : "Unnamed_gas_sensor"}
	} 

	grove_dict = {
				"voc_ppm": 0.0,
				"_meta": {"device_id" : id, 
							"sensor" : "Seeed_Grove_HCHO_sensor"}
	} 

	ps1_dict = {
				"voc_ppb": 0.0,
				"_meta": {"device_id" : id, 
							"sensor" : "EC_Sense_PS1_VOC"}
	} 

	sen54_dict = {
				"pm1.0_μg/m3": 0.0,
				"pm2.5_μg/m3": 0.0,
				"pm4.0_μg/m3": 0.0,
				"pm10.0_μg/m3": 0.0,
				"voc_index": 0.0,
				"_meta": {"device_id" : id, 
							"sensors" : "Sensirion_SEN54"}
				}
	

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
	csv_abs_path = 'sensor_data.csv'
	path = os.path.join(cwd_path, csv_abs_path)
	path_exists = os.path.exists(path)
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
	return result

'''on_connect() is a built in paho-mqtt function that returns the status of the connection when a connect request is made'''
def on_connect(client, userdata, flags, rc):
	if rc == 0:
		print('Connected to MQTT broker\n')
	else:
		print('Failed to connect to MQTT broker, reason is {}\n'.format(rc))

'''on_disconnect() is a built in paho-mqtt function we try to get the client to reconnect to the broker in the event of a disconnection'''
def on_disconnect():
	global mqtt_client
	print("Disconnected. Trying to reconnect...\n")
	logging.info("[MQTT Conn]: Connection to broker lost. Trying to reconnect...")
	mqtt_client.reconnect()

'''mqtt_connect() connects to the mqtt broker and returns the client object'''
def mqtt_connect():
	global username, password, MQTT_BROKER, MQTT_PORT, client_id
	client = mqtt.Client(client_id, clean_session=False)
	client.username_pw_set(username, password)
	client.tls_set()
	client.on_connect = on_connect
	client.on_disconnect = on_disconnect
	client.connect(MQTT_BROKER, MQTT_PORT, 60)
	return client

'''mqtt_publish takes in the client object from mqtt_connect as an argument and publishes the message to said client'''
def mqtt_publish(client, topic, data1, data2, data3, data4):
	msg_result1 = client.publish(topic, data1)
	msg_result2 = client.publish(topic, data2)
	msg_result3 = client.publish(topic, data3)
	msg_result4 = client.publish(topic, data4)
	status1 = msg_result1[0]
	status2 = msg_result2[0]
	status3 = msg_result3[0]
	status4 = msg_result4[0]

	if status1 == 0 and status2 == 0 and status3 == 0 and status4 == 0:
		print('{}: Sent message successfully'.format(datetime.datetime.now()))
	else:
		print('{}: Failed to send message'.format(datetime.datetime.now()))

'''write_to_csv() writes the sensor data to a csv file to enable offline monitoring'''
def write_to_csv(data1, data2, data3, data4):
	global csv_header_flag, path
	with open (path, 'a') as logfile:
		file = csv.writer(logfile)
		if not csv_header_flag:
			file.writerow(['Timestamp', 'Unnamed Gas Sensor (PPM)', 'Grove HCHO Sensor (PPM)', 'EC Sense PS1  (PPB)', 'pm1.5 (μg/m3)', 'pm2.5 (μg/m3)', 
							'pm4.0 (μg/m3)', 'pm10.0 (μg/m3)', 'VOC Index (0-500)'])
			file.writerow([datetime.datetime.now(), data1["voc_ppm"],data2['voc_ppm'], data3['voc_ppb'], data4['pm1.0_μg/m3'], 
							data4['pm2.5_μg/m3'], data4['pm4.0_μg/m3'], data4['pm10.0_μg/m3'], data4['voc_index']])
			csv_header_flag = True
		else:
			file.writerow([datetime.datetime.now(), data1["voc_ppm"],data2['voc_ppm'], data3['voc_ppb'], data4['pm1.0_μg/m3'], 
							data4['pm2.5_μg/m3'], data4['pm4.0_μg/m3'], data4['pm10.0_μg/m3'], data4['voc_index']])

'''update_dictionaries(data) takes a list of sensor readings as input and updates the values of their respective dictionaries and converts it to JSON format
	so it can be published'''
def update_dictionaries(data, dict1, dict2, dict3, dict4):
	gas_dict.update({"voc_ppm": data[0]})
	grove_dict.update({"voc_ppm": data[1]})
	ps1_dict.update({"voc_ppb": data[2]})
	sen54_dict.update({"pm1.0_μg/m3": data[3], "pm2.5_μg/m3": data[4], "pm4.0_μg/m3": data[5], "pm10.0_μg/m3": data[6], "voc_index": data[7]})
	
	gas = json.dumps(gas_dict)
	grove = json.dumps(grove_dict)
	ps1 = json.dumps(ps1_dict)
	sen54 = json.dumps(sen54_dict)

	return gas, grove, ps1, sen54


'''main function'''
if __name__ == '__main__':		# start the program

	flags_init()
	mqtt_init()
	lists_and_dicts_init(client_id)
	logging_init()
	if csv_active_flag:			# check if csv file exists, given the csv flag is set
		path_check()
	ser = serial.Serial('/dev/serial/by-id/usb-Arduino_LLC_Arduino_MKR_WAN_1310_72F7C6B05055344E312E3120FF13322D-if00', 9600)		# setup the UART channel - had to call it this way or it kept breaking after a while if I used \dev\ttyACM0
	# /dev/serial/by-id/usb-Arduino_LLC_Arduino_MKR_WAN_1310_72F7C6B05055344E312E3120FF13322D-if00
	mqtt_client = mqtt_connect()
	mqtt_client.loop_start()
	transmit_prompt = "tx\n"
	
	while True:
		try:
			ser.write(transmit_prompt.encode("utf-8"))
			time.sleep(0.5)
			payload = ser.readline()	# read UART line

			for vals in payload:
				payload_resolved[payload.index(vals)] = hex(ord(vals))	# store the UART data into a list
			payload_decoded = decode_payload(len(payload_resolved))

			''' This block resolves the bytes of data into the actual sensor reading '''
			sensor_data[0] = resolve_readings(payload_decoded[0], payload_decoded[1])		# gas_sensor
			sensor_data[1] = resolve_readings(payload_decoded[2], payload_decoded[3])		# hcho sensor
			sensor_data[2] = resolve_readings(payload_decoded[4], payload_decoded[5], 1)	# ec sense 
			sensor_data[3] = resolve_readings(payload_decoded[6], payload_decoded[7])		# pm 1.0
			sensor_data[4] = resolve_readings(payload_decoded[8], payload_decoded[9])		# pm 2.5
			sensor_data[5] = resolve_readings(payload_decoded[10], payload_decoded[11])		# pm 4.0
			sensor_data[6] = resolve_readings(payload_decoded[12], payload_decoded[13])		# pm 10.0
			sensor_data[7] = resolve_readings(payload_decoded[14], payload_decoded[15])		# voc

		except:
			logging.info("[Serial]: Error in reading serial data at " + str(datetime.utcnow().isoformat()))
			for i in sensor_data:
				sensor_data[i] = None
			exception_flag = True

		gas_json, grove_json, ps1_json, sen54_json = update_dictionaries(sensor_data, gas_dict, grove_dict, ps1_dict, sen54_dict)
		
		if not exception_flag:
			mqtt_publish(mqtt_client, MQTT_TOPIC_NAME, gas_json, grove_json, ps1_json, sen54_json)
		else:
			print("Not sending MQTT Message!\n")
			logging.info("[Events]: Not sending MQTT message because of bad serial read.")
			exception_flag = False

		if debug_mqtt:
			print(gas_json + '\n')
			print(grove_json + '\n')
			print(ps1_json + '\n')
			print(sen54_json + '\n')
		
		if csv_active_flag:
			write_to_csv(gas_dict, grove_dict, ps1_dict, sen54_dict)
		
		if debug_print:
			print("Timestamp: {}".format(datetime.datetime.now()))
			print("Gas Sensor reading in ppm is: {}".format(sensor_data[0]))
			print("HCHO Sensor reading in ppm is: {}".format(sensor_data[1]))
			print("EC Sense reading in ppb is: {}".format(sensor_data[2]))
			print("PM 1.0 reading in μg/m3 is: {}".format(sensor_data[3]))
			print("PM 2.5 reading in μg/m3 is: {}".format(sensor_data[4]))
			print("PM 4.0 reading in μg/m3 is: {}".format(sensor_data[5]))
			print("PM 10.0 reading in μg/m3 is: {}".format(sensor_data[6]))
			print("VOC index (0-500) is: {}".format(sensor_data[7]))
		time.sleep(4.5)
	mqtt_client.loop_stop()
	mqtt_client.disconnect()

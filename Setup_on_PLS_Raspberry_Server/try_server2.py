'''
Note: This script contacts the server through Port 5000. It is known that
National Instrument's LabView also uses this portal. So tagsrv.exe needs to be
terminated first. This is not a problem on Raspberry Pi.

This version has one sensor. The network settings are also changed. 
'''

import socket
import types
import time
import datetime
import threading
import os
#import decode_data
import copy
import select

import queue as Q
import numpy as np
import errno
from struct import *

#from pandas import read_excel

#ServerIP and port config.
PORT = 5000	#udp protocol port
ServerIp = '192.168.10.52'
# sensor config
sensor_ip_list =[]

sensor_ip_list.append('192.168.10.50')
#sensor_ip_list.append('192.168.10.51')
#sensor_ip_list.append('192.168.1.107')
#sensor_ip_list.append('192.168.1.232')
#sensor_ip_list.append('192.168.1.244')

# file saved path.
FILEPATH = './'  #data saved path

#data_time = 4000000 #receiv data time limit, the unit is seconds, 0 means receive data all the time.
data_time = 60

GAIN = 80
#GAIN = 20
RATE = 10000  # sampling rate
ERR_LEN = 800 # if one sensor received data legth les then REE_LEN reconfig sensor
#*************config end*************

#server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #UDP
#server_address = (ServerIp, PORT)
#server_socket.bind(server_address)

"""Read conversion factor for the SLAB"""
vec = np.loadtxt("conversion_l_over_e.txt")
conv_fac = np.diag(vec)
#mapping = read_excel("mapping.xls", header=None).to_numpy()
mapping = np.loadtxt("mapping.txt")
viewMatrix_long = np.loadtxt("v_office.mtx",skiprows=10)
viewMatrix = viewMatrix_long[:, ::3]

def decode_config_message(msg_bit):
	"""Decode and remove all non-ASCII char's."""
	return ''.join([x for x in msg_bit.decode() if ord(x) < 127 and ord(x) > 31])

def decodeVal_opt(low_b, high_b):
	low = int.from_bytes(low_b, byteorder='big', signed=False)
	high = int.from_bytes(high_b, byteorder='big', signed=False)
	expo = high >> 4
	frac = (low | high << 8) & 0xfff
	return 0.01 * 2**expo * frac

def decode_data(receive_data_bit):
	"""Decode reading data from the OPT3001 sensors. (12 * 16 = ) 192 readings in total."""
	receive_data_lst = [bytes([i]) for i in receive_data_bit]
	readings = np.zeros(192)
	for aa in range(192):
		low_b = receive_data_lst[18 + 3 * aa]
		high_b = receive_data_lst[19 + 3 * aa]
		readings[aa] = decodeVal_opt(low_b, high_b)
	return readings

def config_system(server_socket):
	print ("\n*****config information***** \nGain =  %d , record time = %d seconds \nstarted sensor are : %s \n**************************\n" % (GAIN, data_time, str(sensor_ip_list)))
	for ii in sensor_ip_list:
		sensor_config_start(server_socket, ii, GAIN, RATE )

def receive_one_data(server_socket, sensor_ip_list, doSave):
	"""Read one data from the SLAB. Only this and nothing else.
	The start and the termination of the connection and the reading process
	should be handled elsewhere."""

	#time_tag = get_time_tag()
	#old_min = time_tag[14:16]
	#file_date = time_tag[0:14]
	#start_second = int(time.time());

	all_data  = []

	for ii in range(len(sensor_ip_list)):
		all_data.append([])  #initial data list
		all_data[ii] = ''

	server_socket.setblocking(0)
	data_flag = False
	initial_flag = True

	# receive sensor package
	while True:
		try:
			empty_socket(server_socket)
			time.sleep(0.001)
			receive_data, client_address = server_socket.recvfrom(2048)
			data_flag = True
			#time_tag = get_time_tag()
			print("Received!")

			data_ip = str(client_address[0])

			if len(receive_data) < 100:
				#re_message = decode_data.decode_config_message(receive_data)
				re_message = decode_config_message(receive_data)
				if re_message in 'Sp':
					print("%s is stoped!"%data_ip)
				continue
			if data_ip in sensor_ip_list:
				data_location_num = sensor_ip_list.index(data_ip)
			else:
				print ('%s sensor still upload data!'%data_ip)
				continue
			break
		except IOError as e:
			if e.errno == errno.EWOULDBLOCK:
				data_flag = False
			continue

	#de_code_data =  decode_data.decode_data(receive_data)
	readings = decode_data(receive_data)
	illu = np.matmul(mapping, readings)
	luminance = np.matmul(conv_fac, illu)
	
	"""Save data"""
	if doSave:
		all_data[data_location_num] =all_data[data_location_num] + np.array2string(luminance) +'\n'
		# #all_data[data_location_num] =all_data[data_location_num] + time_tag + de_code_data +'\n'
		# #print(readings[0])
		# now_second = int(time.time())
		time_tag = get_time_tag()
		file_date = time_tag[0:14]
		new_min = time_tag[14:19]
		#save file
		# print("Save last file. Time elapsed: ", now_second - start_second)
		filename = file_date + new_min + '.txt'
		writ_data = copy.deepcopy(all_data)
		threading.Thread(target=save_file, args=(sensor_ip_list,filename,writ_data,)).start()
	"""return data"""
	return luminance

def save_file(sensor_ip_list, filename, data_list):
	date = filename.split('_')[0]
	for count in range( len(sensor_ip_list)):
		if os.path.exists(FILEPATH + sensor_ip_list[count] +'/'+ date +'/') == False:
			os.makedirs(FILEPATH + sensor_ip_list[count] + '/'+ date)
		complete_filename = FILEPATH + sensor_ip_list[count] +'/' + date +'/' +filename
		print(complete_filename)
		datafile = open(complete_filename,'wb')
		print(len(data_list[count]))
		datafile.write(data_list[count].encode())
		datafile.close()
        
def get_time_tag():
	timenow = datetime.datetime.now()
	filename = str(timenow)
	filename = filename.replace(' ','_')
	filename = filename.replace(':','-')
	return filename

def reconnect(ServerIp, PORT):
	"""Reconnect"""
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #UDP
	server_address = (ServerIp, PORT)
	server_socket.bind(server_address)
	return server_socket

def close_connection(server_socket):
	"""Close the socket."""
	server_socket.close()

def send_data(server_socket, sensor_ip, data_str):
	sensor_address = (sensor_ip, PORT)
	server_socket.sendto(data_str.encode(),sensor_address)

def receive_data(server_socket, sensor_ip, target_str):

	flag = False
	start_time = time.time()
	while True:
		receive_data, client_address = server_socket.recvfrom(65535)
		print(receive_data)
		print(client_address)
		#real_data = decode_data.decode_config_message(receive_data)
		real_data = decode_config_message(receive_data)
		print ('%s and message is %s'%(str(client_address[0]), real_data))

		if (str(client_address[0]) == sensor_ip) and target_str in real_data:
			flag = True
			break
		now_time = time.time()
		if now_time - start_time > 1:
			break
	return flag

def empty_socket(sock):
	"""remove the data present on the socket"""
	input = [sock]
	while 1:
		inputready, o, e = select.select(input,[],[], 0.0)
		if len(inputready)==0: break
		for s in inputready: s.recv(1)

def sensor_config_start(server_socket, sensor_ip, GAIN, RATE):

	ZERO = chr(0)+chr(0)
	state = 0

	reset_com = 'r' + ZERO
	test_com ='t' + ZERO
	print('Reset')
	send_data(server_socket, sensor_ip, reset_com)
	print('Test')
	send_data(server_socket, sensor_ip, test_com)

	if receive_data(server_socket, sensor_ip, 'T'):
		print('test success')
		state = 1
	else:
		print ('%s test err'%sensor_ip)

	#config_com = 'c' + chr(0) +chr(0) + chr(4)+chr(0) +chr(16) + chr(39)+chr(GAIN) +chr(0)
	config_com = 'c' + chr(0) +chr(0) + chr(4)+chr(0) +pack('<H', RATE).decode() +chr(GAIN) +chr(0)
	send_data(server_socket, sensor_ip, config_com)
	if receive_data(server_socket, sensor_ip, 'Co'):
		print('config success')
		state = state + 1
	else:
		print ('%s config fail'%sensor_ip)

	start_com  = 's' + ZERO + chr(1)+chr(0) + 't'
	if state == 2:
		send_data(server_socket, sensor_ip, start_com)
		if receive_data(server_socket, sensor_ip ,'St'): # it means it start to update data
			print("%s start upload data!"%sensor_ip)
		else:
			print( "%s can not start"%sensor_ip)

def sensor_stop(server_socket, sensor_ip_list):

	stop_com  = 's' + chr(0)+chr(0)+ chr(1)+chr(0) + 'p'
	for ii in sensor_ip_list:
		send_data(server_socket, ii, stop_com)

s = socket.socket()
host = '192.168.10.52'
port = 5001
s.bind((host, port))
s.listen(5)
print("Listening")
while True:
	c, addr = s.accept()
	print("Connection accepted from " + repr(addr[1]))
	#c.send("Server approved connection\n".encode())
	instr = c.recv(1026).decode()
	print(repr(addr[1]) + ": " + instr)
	if "START" in instr:
		server_socket = reconnect(ServerIp, PORT)
		print("Start! ")
		print ("\n*****config information***** \nGain =  %d , record time = %d seconds \nstarted sensor are : %s \n**************************\n" % (GAIN, data_time, str(sensor_ip_list)))
		for ii in sensor_ip_list:
			sensor_config_start(server_socket, ii, GAIN, RATE)
		"""This should be done per sensor."""
		print("Receive one data.")
		
		doSave = False
		if "-S" in instr:
			doSave = True
		
		lum = receive_one_data(server_socket, sensor_ip_list, doSave)
		
		illum = viewMatrix.dot(lum)
		
		#lum_str = ','.join(str(x) for x in lum)
		#illum_str = str(illum)
		illum_str = ','.join(str(x) for x in illum)

		print("Stop sensor.")
		sensor_stop(server_socket, sensor_ip_list)

		"""This is done once"""
		print("Close socket.")
		server_socket.close()

		#c.send(lum_str.encode())
		c.send(illum_str.encode())
		
	c.close()

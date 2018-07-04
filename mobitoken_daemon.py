#!/usr/bin/python

import bluetooth
import time
import socket
import struct
import os
import _thread
from subprocess import check_output
from subprocess import STDOUT
from threading import Barrier
from threading import Lock


def current_milli_time():
	return int(round(time.time() * 1000))


class PingPongThread:

	def __init__(self, bluetooth_socket, lock, barrier):
		self.bluetooth_socket = bluetooth_socket
		self.lock = lock
		self.barrier = barrier
		#connected = connected
		self.thread_id = _thread.start_new_thread(self.loop, ())

	def loop(self):
		global connected
		while True:
			try:
				self.debug("Send pong")
				self.lock.acquire()  # critical section
				if not connected:
					self.lock.release()
					return
				self.bluetooth_socket.send("ping")
				pong = self.bluetooth_socket.recv(1024)
				if not connected:
					self.lock.release()
					return
				self.lock.release()  # critical section
				self.debug("Received pong")
				time.sleep(5)
				if not connected:
					return
			except IOError as e:
				self.debug("Exception in ping")
				check_output("dbus-send --session --type=method_call --dest=org.gnome.ScreenSaver "
					"/org/gnome/ScreenSaver org.gnome.ScreenSaver.Lock", shell=True, stderr=STDOUT)
				# lets notify error
				self.lock.acquire(blocking=False)  # critical section. maybe acquired?
				connected = False
				self.lock.release()
				break
		self.debug("Waiting in the barrier")
		barrier.wait()

	def debug(self, text):
		print("PingPongThread: " + text)


class UnixSocketThread:

	def __init__(self, bluetooth_socket, lock, barrier, unix_socket_address):
		self.debug("Creating UnixSocketThread")
		self.bluetooth_socket = bluetooth_socket
		self.lock = lock
		self.barrier = barrier
		#connected = connected
		self.unix_socket_address = unix_socket_address
		self.unix_socket = None
		self.thread_id = _thread.start_new_thread(self.loop, ())

	def loop(self):
		SO_PEERCRED = 17  # /usr/include/asm-generic/socket.h
		pid, uid, gid = None, None, None
		global connected
		while True:
			# Make sure the socket does not already exist
			try:
				os.unlink(self.unix_socket_address)
			except OSError:
				if os.path.exists(self.unix_socket_address):
					raise

			# Create a UDS socket
			socket.setdefaulttimeout(0.5)
			self.unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

			# Bind the socket to the address
			self.debug("Starting up on {}".format(self.unix_socket_address))
			self.unix_socket.bind(self.unix_socket_address)

			# Listen for incoming connections
			self.unix_socket.listen(1)

			while True:
				# Wait for a connection
				self.debug("Waiting for a connection")
				while True:
					try:
						connection, client_address = self.unix_socket.accept()
						creds = connection.getsockopt(socket.SOL_SOCKET, SO_PEERCRED, struct.calcsize('3i'))
						pid, uid, gid = struct.unpack('3i', creds)
						self.debug("pid: %d, uid: %d, gid %d" % (pid, uid, gid))
						break
					except socket.timeout:
						self.debug("Timeout")
						self.lock.acquire()  # critical section
						if not connected:
							self.lock.release()
							self.debug("Waiting in the barrier")
							barrier.wait()
							return
						self.lock.release()

				try:
					while True:
						data = connection.recv(128)  # 16
						self.debug("Received " + data.decode("utf-8").rstrip('\x00'))
						if data:
							data = data.decode("utf-8").rstrip('\x00')
							self.lock.acquire()  # critical section
							if not connected:
								self.lock.release()
								return
							self.debug("Lets check bluetooth mobitoken")
							self.bluetooth_socket.send("pid:%d;uid:%d;%s" % (pid, uid, data))
							data = self.bluetooth_socket.recv(1024)
							if not connected:
								self.lock.release()
								return
							self.lock.release()  # critical section
							self.debug("Received data")
							connection.sendall(data.decode("utf-8").rstrip('\x00').encode("utf-8"))
							#data_split = data.decode("utf-8").rstrip('\x00').split(":")
							#if len(data_split) == 1: # cred login password
							#	self.debug("Sending cred password...")
							#	connection.sendall(data.encode("utf-8"))
							#else:
							#	self.debug("Sending url password...")
							#	connection.sendall(data.encode("utf-8"))
							break
						else:
							self.debug("no data from client")
							connection.sendall("no_pass".encode("utf-8"))
							break
				except IOError as e:  # TODO tengo que distinguir mejor entre esta excepcion
					print(e)
					self.debug("Unix socket exception. No Bluetooth connection")
					connection.sendall("no_pass".encode("utf-8"))
				except AttributeError as e:
					print(e)
					self.debug("no mobitoken/password found, send no_pass")
					connection.sendall("no_pass".encode("utf-8"))
				except BrokenPipeError:
					self.debug("broken pipe")
					break
				finally:
					# Clean up the connection
					connection.close()
					os.remove(self.unix_socket_address)
					self.debug("closed socket")
					self.lock.acquire(blocking=False)  # critical section. maybe acquired?
					# connected = False
					self.lock.release()
					break

	def debug(self, text):
		print("UnixSocketThread: " + text)

connected = False
barrier = Barrier(3)
lock = Lock()
address = "88:79:7E:E8:CB:80"
address_alba = "44:D4:E0:16:E8:75"
uuid = "00001101-0000-1000-8000-00805F9B34FB"
unix_socket_address = '/home/alberto/mobitoken.socket'
while True:
	service_matches = bluetooth.find_service(uuid=uuid, address=address)  # try to find the mobitoken service
	if service_matches:  # found?
		first_match = service_matches[0]
		port = first_match["port"]
		bluetooth_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)  # create RFCOMM socket
		bluetooth_socket.connect((address, port))  # connect to address and found port
		connected = True
		ping_pong_thread = PingPongThread(bluetooth_socket, lock, barrier)
		unix_socket_thread = UnixSocketThread(bluetooth_socket, lock, barrier, unix_socket_address)
		barrier.wait()
		print("Main: they returns!")
	else:
		print("Main: service not found :(")
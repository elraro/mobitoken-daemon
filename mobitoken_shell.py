import socket
import datetime

server_address = '/home/alberto/mobitoken.socket'
SO_PASSCRED = 16 # Pulled from /usr/include/asm-generic/socket.h

# request login credentials
def request_login_cred(username):
	s = socket.socket(socket.AF_UNIX)
	s.setsockopt(socket.SOL_SOCKET, SO_PASSCRED, 1)
	s.settimeout(6)  # 1 second timeout, after all it should be instant because its local
	try:
		s.connect(server_address)
		s.send(("cred:" + username).encode("utf-8"))
		data = s.recv(256)
		now = datetime.datetime.now()
		print("Data: " + data.decode("utf-8"))
	except socket.timeout:
		print("Timeout :(")
	except ConnectionRefusedError:
		print("ConnectionRefusedError :(")
	finally:
		print("---------")
		s.close()


def request_url_cred(url):
	s = socket.socket(socket.AF_UNIX)
	s.setsockopt(socket.SOL_SOCKET, SO_PASSCRED, 1)
	s.settimeout(6)  # 1 second timeout, after all it should be instant because its local
	try:
		s.connect(server_address)
		s.send(("url:" + url).encode("utf-8"))
		data = s.recv(256)
		now = datetime.datetime.now()
		print("Data: " + data.decode("utf-8"))
	except socket.timeout:
		print("Timeout :(")
	except ConnectionRefusedError:
		print("ConnectionRefusedError :(")
	finally:
		print("---------")
		s.close()


print("Mobitoken shell")
print("Command list:")
print("-----------")
print("cred <user>")
print("quit")
print("-----------")
print("Example:")
print("cred alberto")
print("cred alba")
print("url mail.google.com")

while True:
	command = input("Command to execute: ")
	command_split = command.split(" ")
	if command_split[0] == "cred":
		request_login_cred(command_split[1])
	elif command_split[0] == "url":
		request_url_cred(command_split[1])
	elif command_split[0] == "quit":
		break
	else:
		print("Unknown command.")
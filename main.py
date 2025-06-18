import socket
import struct

HOST = '127.0.0.1'
PORT = 2237

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    udp_socket.bind((HOST, PORT))
    print(f"Listening on {HOST}:{PORT}")
except socket.error as msg:
    print(f"Socket error: {msg}. Could not listen on {HOST}:{PORT}.")

while True:
    data, addr = udp_socket.recvfrom(1024)
    if len(data) >= 12:
        message_type = struct.unpack(">I", data[8:12])[0]
        print(f"Type: {message_type} Length: {len(data)}")
        if message_type == 2:
            print(data)

import socket
import struct
from classes import *

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
        match message_type:
            case 2: # Message packets
                schema = struct.unpack('>I', data[4:8])[0]
                program = struct.unpack('>6s', data[16:22])[0].decode('utf-8')
                snr = struct.unpack(">i", data[27:31])[0]
                time_delta = struct.unpack(">d", data[31:39])[0]
                fq_offset = struct.unpack('>i', data[39:43])[0]
                msg = data[52:-2]
                decoded_msg = msg.decode('utf-8')
                parsed_packet = Packet(packet_type=message_type, schema=schema, program=program, snr=snr,
                                       delta_time=time_delta, frequency=fq_offset, message=decoded_msg)
                print(parsed_packet.message)
            case 1: # Status packets
                pass




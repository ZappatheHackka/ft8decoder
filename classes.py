import socket
import struct
from dataclasses import dataclass

data_motherload = []
convo = {

}

@dataclass
class Packet:
    snr: int #
    delta_time: float
    frequency: int
    message: str
    schema: int
    program: str
    packet_type: int


# Make class that does the UDP parsing
class WsjtxParser:
    def __init__(self, packet_list: list=None):
        self.packet_list = packet_list if packet_list is not None else []

    def parse(self, host, port):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udp_socket.bind((host, port))
            print(f"Listening on {host}:{port}...")
            ans = input("Begin packet parsing? (Y/n)\n").lower()
            if ans == "n":
                print("Quitting...")
                exit()
            if ans == "y":
                print("Parsing packets...")
                while True:
                    data, addr = udp_socket.recvfrom(1024)
                    if len(data) >= 12:
                        self.parse_packet(data=data)
        except socket.error as msg:
            print(f"Socket error: {msg}. Could not listen on {host}:{port}.")


    def parse_packet(self, data):
        message_type = struct.unpack(">I", data[8:12])[0]
        match message_type:
            case 2:  # Message packets
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
                self.packet_list.append(parsed_packet)
            case 1:  # Status packets
                pass
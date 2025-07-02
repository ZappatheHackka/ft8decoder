import queue
import socket
import time
import struct
from threading import Thread
from dataclasses import dataclass

data_motherload = []

# ---------------------DATA GRABBING---------------------------

@dataclass
class Packet:
    snr: int #
    delta_time: float
    frequency: int
    message: str
    schema: int
    program: str
    packet_type: int

class WsjtxParser:
    def __init__(self):
        self.packet_queue = queue.Queue()

    def start_listening(self, host, port):
        listen_thread = Thread(target=self.listen, args=(host, port))
        listen_thread.start()

    def listen(self, host, port):
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
                grabbing_thread = Thread(target=self.start_grabbing, args=(30,))
                grabbing_thread.start()
                while True:
                    udp_socket.settimeout(1.0)
                    try:
                        data, addr = udp_socket.recvfrom(1024)
                        if len(data) >= 12:
                            self.parse_packets(data=data)
                    except socket.timeout:
                        print("Waiting for message...")
        except socket.error as msg:
            print(f"Socket error: {msg}. Could not listen on {host}:{port}.")

    def parse_packets(self, data):
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
                self.packet_queue.put(parsed_packet)
            case 1:  # Status packets
                pass

    def start_grabbing(self, seconds: int):

        while True:
            time.sleep(seconds)
            print(f"Dumped data: {data_motherload}")
            while not self.packet_queue.empty():
                data_motherload.append(self.packet_queue.get_nowait())


# -----------------DATA PROCESSING-----------------------

@dataclass
class MessageTurn:
    turn: int
    message: str
    translated_message: str
    packet: Packet | str

@dataclass
class CQ:
    message: str
    packet: Packet

# data is data_motherload
class MessageProcessor:
    def __init__(self):
        self.cqs = []
        self.convo_dict = {}

    def order(self, data: list):
        pass

    def order_callsigns(self, data: list):
        for packet in data:
            message = packet.message.split()
            if message[0] == "CQ":
                self.handle_cq(packet)
            message_callsigns = []
            for i in message:
                # TODO: Add more robust parsing to catch callsigns of all shapes and sizes
                if len(i) == 5:
                    message_callsigns.append(i)
            callsigns = sorted(message_callsigns)
            if self.convo_dict[(callsigns[0], callsigns[1])]:
                pass # continue here
            else:
                convo_list = [MessageTurn(turn=1, message="", translated_message="", packet=""),
                              MessageTurn(turn=2, message="", translated_message="", packet=""),
                              MessageTurn(turn=3, message="", translated_message="", packet=""),
                              MessageTurn(turn=4, message="", translated_message="", packet=""),
                              MessageTurn(turn=5, message="", translated_message="", packet=""),]
                self.convo_dict[(callsigns[0], callsigns[1])] = convo_list
                self.sort_message(packet, callsigns, message_callsigns)


    def sort_message(self, packet: Packet, callsigns: list, message_callsigns: list):
        message = packet.message.split()

    # TODO track CQs separately from conversation turns
    def handle_cq(self, packet: Packet):
        cq = CQ(packet=packet, message=packet.message)
        self.cqs.append(cq)




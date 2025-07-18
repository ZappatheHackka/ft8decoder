import socket
import queue
import struct
from threading import Thread
from ft8decoder.processor import MessageProcessor
from ft8decoder.core import Packet

class WsjtxParser:
    def __init__(self):
        self.packet_queue = queue.Queue()

    def start_listening(self, host, port, processor: MessageProcessor):
        print(f"Listening on {host}:{port}...")
        ans = input("Begin packet parsing? (Y/n)\n").lower()
        if ans == "n":
            print("Quitting...")
            exit()
        if ans == "y":
            listen_thread = Thread(target=self.listen, args=(host, port, processor))
            listen_thread.start()

    def listen(self, host, port, processor: MessageProcessor):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udp_socket.bind((host, port))
            print("Parsing packets...")
            grabbing_thread = Thread(target=self.start_grabbing, args=(processor,))
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

    def start_grabbing(self, processor: MessageProcessor):
        while True:
            try:
                packet = self.packet_queue.get(timeout=1)  # Block for 1 second max
                processor.data_motherload.append(packet)
            except queue.Empty:
                continue
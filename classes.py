import queue
import socket
import time
import struct
from threading import Thread
from dataclasses import dataclass

# TODO write create_message() func on MessageProcessor that creates MessageTurn objects and stores them appropriately.
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
        processor = MessageProcessor()
        while True:
            time.sleep(seconds)
            print(f"Dumped data: {processor.data_motherload}")
            while not self.packet_queue.empty():
                processor.data_motherload.append(self.packet_queue.get_nowait())


# -----------------DATA PROCESSING-----------------------

@dataclass
class MessageTurn:
    turn: int
    message: str
    translated_message: str
    packet: Packet | str
    type: str

@dataclass
class CQ:
    message: str
    translated_message: str
    caller: str
    packet: Packet


class MessageProcessor:
    def __init__(self):
        self.cqs = []
        self.data_motherload = []
        self.misc_comms = {}
        self.convo_dict = {}

    def order(self, data: list):
        pass

    # TODO Write tests for this- create a list of sample FT8 contacts and run it through [DONE]
    def check_callsigns(self, data: list):
        for packet in data:
            message = packet.message.split()
            if len(message) > 3:
                self.handle_longer_msg(packet=packet, message=message)
            # TODO Handle messages w/ >3 words (dx etc)
            if 1 < len(message) < 3:
                self.handle_short_msg(packet=packet, message=message)
            if message[0] == "CQ":
                self.handle_cq(packet)
                continue
            message_callsigns = [message[0], message[1]]
            # TODO: Add more robust parsing to catch callsigns of all shapes and sizes
            callsigns = sorted(message_callsigns)
            if (callsigns[0], callsigns[1]) in self.convo_dict:
                self.sort_message(packet, callsigns, new_convo=False)
            else:
                self.convo_dict[(callsigns[0], callsigns[1])] = [{"completed": False}]
                self.sort_message(packet, callsigns, new_convo=True)

    # TODO REFACTOR SO MessageTurn() OBJECTS CREATED AS PACKETS RECEIVED--NOT PRE-DEFINED [DONE]

    # Handles new messages & retroactively places CQ call in list
    def sort_message(self, packet: Packet, callsigns: list, new_convo: bool):
        if new_convo:
            # TODO Reorder checking order, place CQ updater in first func [DONE]
            self.add_cq(callsigns=callsigns)
        message = packet.message.split()
        if self.is_ack_reply(message):
            self.handle_ack_reply(callsigns, packet, message)
        elif self.is_grid_square(message):
            self.handle_grid_square(callsigns, packet, message)
        elif self.is_signal_report(message):
            self.handle_signal_report(callsigns, packet, message)

    # TODO Handle messages w/ <=2 words [DONE]
    def handle_short_msg(self, packet: Packet, message: list):
        second_part = message[1]
        if self.is_grid_square(message):
            convo_turn = MessageTurn(turn=0, message="".join(message), translated_message=f"{message[0]} "
                        f"announces their position at {second_part}.", packet=packet, type="Grid Square announcement.")
            keys = sorted(message)
            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
        elif second_part == "73":
            convo_turn = MessageTurn(turn=0, message="".join(message),
                                     translated_message=f"{message[0]} says goodbye.",
                                     packet=packet, type="73 sign off.")
            keys = sorted(message)
            # TODO write search func that can check main list for potential matches--where is the message 73ing to?
            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
        elif second_part == "RR73":
            convo_turn = MessageTurn(turn=0, message="".join(message),
                                     translated_message=f"{message[0]} says Roger Roger and signs off.",
                                     packet=packet, type="RR73")
            keys = sorted(message)
            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
        # Just two callsigns
        elif "/QRP" in message:
            if "/QRP" in message[0]:
                keys = sorted(message)
                if (keys[0], keys[1]) in self.convo_dict:
                    convo_turn = MessageTurn(turn=len(self.convo_dict[(keys[0], keys[1])]), message="".join(message),
                                             translated_message=f"{message[1]} pings low power {message[0]}.",
                                             packet=packet, type="Two Callsigns")
                    self.convo_dict[(keys[0], keys[1])].append(convo_turn)
                else:
                    convo_turn = MessageTurn(turn=0, message="".join(message),
                                             translated_message=f"{message[1]} pings low power {message[0]}.",
                                             packet=packet, type="Two Callsigns")
                    self.convo_dict[(keys[0], keys[1])] = [{"completed": False}, convo_turn]
            else:
                keys = sorted(message)
                if (keys[0], keys[1]) in self.convo_dict:
                    convo_turn = MessageTurn(turn=len(self.convo_dict[(keys[0], keys[1])]), message="".join(message),
                                             translated_message=f"{message[1]} pings {message[0]} at low power.",
                                             packet=packet, type="Two Callsigns")
                    self.convo_dict[(keys[0], keys[1])].append(convo_turn)
                else:
                    convo_turn = MessageTurn(turn=0, message="".join(message),
                                             translated_message=f"{message[1]} pings {message[0]} at low power.",
                                             packet=packet, type="Two Callsigns")
                    self.convo_dict[(keys[0], keys[1])] = [{"completed": False}, convo_turn]
        else:
            keys = sorted(message)
            if (keys[0], keys[1]) in self.convo_dict:
                convo_turn = MessageTurn(turn=len(self.convo_dict[(keys[0], keys[1])]), message="".join(message),
                                         translated_message=f"{message[1]} pings {message[0]}.", packet=packet,
                                         type="Two Callsigns.")
                self.convo_dict[(keys[0], keys[1])].append(convo_turn)
            else:
                convo_turn = MessageTurn(turn=0, message="".join(message), translated_message=f"{message[1]} pings "
                                            f"{message[0]}.", packet=packet, type="Two Callsigns.")
                self.convo_dict[(keys[0], keys[1])] = [{"completed": False}, convo_turn]

    def handle_longer_msg(self, packet: Packet, message: list):
        code = message[1]
        geo_list = ["NA", "EU", "AS", "AF", "SA", "OC", "UK", "JA", 'VK', 'ZL', 'UA', 'HL', 'BV', 'W', 'VE', 'K']
        if code in geo_list:
            convo_turn = MessageTurn(turn=0, message="".join(message),)

    # TODO make logic more robust- check for int(), place after Grid & Ack checks [DONE]
    def is_signal_report(self, message):
        signal = message[-1]
        if len(signal) > 2:
            if signal != "RR73" and signal != "RRR":
                if int(signal[2:]) or signal[2:] == '00':
                    return True
                return False
            return False
        return False

    def handle_signal_report(self, callsigns: list, packet: Packet, message: list):
        first_callsign = message[0]
        second_callsign = message[1]
        if len(message[2]) > 3:
            nums = message[2][1:]
            translated_message = (f"{second_callsign} says Roger and reports a signal report of {nums} "
                                  f"to {first_callsign}.")
        else:
            translated_message = f"{second_callsign} sends signal report of {message[2]} to {first_callsign}."

        # Putting this as the second signal report--assuming the CQ caller sends report first
        m_type = "Signal Report"
        turn_obj = MessageTurn(turn=len(self.convo_dict[(callsigns[0], callsigns[1])]),
                               message=packet.message, translated_message=translated_message, packet=packet,
                               type=m_type)
        self.convo_dict[(callsigns[0], callsigns[1])].append(turn_obj)
        print("Updated convo_dict with signal report.")

    def is_ack_reply(self, message):
        code = message[-1]
        if code == "RRR" or code == "RR73" or code == "73":
            return True
        return False

    def handle_ack_reply(self, callsigns: list, packet: Packet, message: list):
        ack = message[-1]
        if ack == "RRR":
            translated_message = f"{message[1]} sends a Roger Roger Roger to {message[0]}."
            convo_turn = MessageTurn(turn=(len(self.convo_dict[(callsigns[0], callsigns[1])])), message=packet.message,
                                     translated_message=translated_message, packet=packet, type="RRR")
            self.convo_dict[(callsigns[0], callsigns[1])].append(convo_turn)
            print("Updated convo_dict with RRR reply.")
        elif ack == "RR73":
            translated_message = (f"{message[1]} sends a Roger Roger to {message[0]} and says goodbye, "
                                  f"concluding the connection.")
            convo_turn = MessageTurn(turn=(len(self.convo_dict[(callsigns[0], callsigns[1])])), message=packet.message,
                                     translated_message=translated_message, packet=packet, type="RR & Goodbye")
            self.convo_dict[(callsigns[0], callsigns[1])].append(convo_turn)
            self.convo_dict[(callsigns[0], callsigns[1])][0]["completed"] = True
            print("Updated convo_dict with RR73 reply.")
        elif ack == "73":
            translated_message = f"{message[1]} sends their well wishes to {message[0]}, concluding the connection."
            convo_turn = MessageTurn(turn=(len(self.convo_dict[(callsigns[0], callsigns[1])])), message=packet.message,
                                     translated_message=translated_message, packet=packet, type="Goodbye")
            self.convo_dict[(callsigns[0], callsigns[1])].append(convo_turn)
            self.convo_dict[(callsigns[0], callsigns[1])][0]["completed"] = True
            print("Updated convo_dict with 73 reply.")

    def is_grid_square(self, message):
        code = str(message[-1])
        if len(code)  == 4:
            if code[0].isalpha() and code[0].isupper():
                if code[1].isalpha() and code[1].isupper():
                    if code[2].isnumeric():
                        if code[3].isnumeric():
                            return True
                        else:
                            return False
                    else:
                        return False
                else:
                    return False
            else:
                return False
        else:
            return False

    def handle_grid_square(self, callsigns: list, packet: Packet, message: list):
        grid_square = message[-1]
        translated_message = f"{message[1]} sends a grid square location of {grid_square} to {message[0]}."
        convo_turn = MessageTurn(turn=(len(self.convo_dict[(callsigns[0], callsigns[1])])),
                                 message=packet.message, translated_message=translated_message, packet=packet,
                                 type="Grid Square Report")
        self.convo_dict[(callsigns[0], callsigns[1])].append(convo_turn)
        print("Updated convo_dict with grid square report.")

    # TODO track CQs separately from conversation turns [DONE]
    def handle_cq(self, packet: Packet):
        caller = packet.message.split()[1]
        grid = packet.message.split()[2]
        translated = f"Station {caller} is calling for any response from grid {grid}."
        cq = CQ(packet=packet, message=packet.message, caller=caller, translated_message=translated)
        self.cqs.append(cq)

    # TODO add error handling if None
    def add_cq(self, callsigns: list):
        for callsign in callsigns:
            for cq in self.cqs:
                if cq.caller == callsign:
                    this_cq = cq
                    cq_turn = MessageTurn(turn=1, message=this_cq.message, translated_message=this_cq.translated_message,
                                  packet=this_cq.packet, type="CQ Call.")
                    self.convo_dict[(callsigns[0], callsigns[1])].insert(1, cq_turn)
                    print("Updated convo_dict with initial CQ call.")
                    break
                else:
                    continue
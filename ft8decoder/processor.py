from threading import Thread
import time
from ft8decoder.core import *
from dataclasses import asdict
import json

class MessageProcessor:
    def __init__(self):
        self.cqs = []
        self.data_motherload = []
        self.misc_comms = {}
        self.convo_dict = {}
        self.translation_templates = {    # Cleaner for catching rare / niche message types than endless conditionals.
            "DX": "{sender} is calling long-distance stations from grid {grid}.",
            "POTA": "Parks on the Air participant {sender} is calling from grid {grid}.",
            "SOTA": "Summits on the Air participant {sender} is calling from grid {grid}.",
            "TEST": "{sender} is making a contest call from grid {grid}.",
            "NA": "{sender} is calling North America from grid {grid}.",
            "EU": "{sender} is calling Europe from grid {grid}.",
            "SA": "{sender} is calling South America from grid {grid}.",
            "AS": "{sender} is calling Asia from grid {grid}.",
            "AF": "{sender} is calling Africa from grid {grid}.",
            "OC": "{sender} is calling Oceania from grid {grid}.",
            "JA": "{sender} is calling Japan from grid {grid}.",
            "HL": "{sender} is calling South Korea from grid {grid}.",
            "VK": "{sender} is calling Australia from grid {grid}.",
            "UA": "{sender} is calling Russia from grid {grid}.",
            "BV": "{sender} is calling Taiwan from grid {grid}.",
            "VOTA": "Volunteers On The Air participant {sender} is calling from grid {grid}.",
            "ZL": "{sender} is calling New Zealand from grid {grid}.",
            "CN": "{sender} is calling China from grid {grid}.",
            "BY": "{sender} is calling China from grid {grid}.",
            "WFD": "{sender} is operating in Winter Field Day from grid {grid}.",
            "FD": "{sender} is operating in Field Day from grid {grid}.",
            "SKCC": "{sender} is calling SKCC (Straight Key Century Club) members from grid {grid}.",
            "NAQP": "{sender} is participating in the North American QSO Party from grid {grid}.",
            "ARRL": "{sender} is participating in an ARRL event from grid {grid}.",
            "CQWW": "{sender} is participating in CQ World Wide from grid {grid}.",
        }
        self.master_data = [{"Successfull Comms": self.convo_dict}, {"CQs": self.cqs}, {'Misc. Comms': self.misc_comms}]

    def order(self, seconds: int):
        thread = Thread(target=self.organize_messages, args=(seconds,))
        thread.start()

    def organize_messages(self, seconds: int):
        while True:
            time.sleep(seconds)

            packets_to_process = self.data_motherload.copy()
            self.data_motherload.clear()
            print(f"Processing {len(packets_to_process)} packets...")

            if packets_to_process:
                for packet in packets_to_process:
                    message = packet.message.split()
                    if message[0] == "CQ":
                        self.handle_cq(packet)
                        continue
                    if len(message) == 2:
                        self.handle_short_msg(packet=packet, message=message)
                        continue
                    if len(message) > 3:
                        self.handle_longer_msg(packet=packet, message=message)
                        continue
                    # TODO Handle messages w/ >3 words (dx etc)
                    message_callsigns = [message[0], message[1]]
                    # TODO: Add more robust parsing to catch callsigns of all shapes and sizes
                    callsigns = sorted(message_callsigns)
                    if (callsigns[0], callsigns[1]) in self.convo_dict:
                        self.sort_message(packet, callsigns, new_convo=False)
                    else:
                        self.convo_dict[(callsigns[0], callsigns[1])] = [{"completed": False}]
                        self.sort_message(packet, callsigns, new_convo=True)
                    print(f"Processed {len(packets_to_process)} packets!")
            else:
                print(f"No packets found! Waiting {seconds} more seconds...")

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
        else:
            print(f"Could not parse packet:", packet)

    def handle_short_msg(self, packet: Packet, message: list):
        second_part = message[1]
        if self.is_grid_square(message):
            convo_turn = MessageTurn(turn=0, message="".join(message), translated_message=f"{message[0]} "
                        f"announces their position at {second_part}.", packet=packet, type="Grid Square announcement.")
            keys = sorted(message)
            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
                print("Message added to misc_comms list!")
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
                print("Message added to misc_comms list!")
        elif second_part == "73":
            convo_turn = MessageTurn(turn=0, message="".join(message),
                                     translated_message=f"{message[0]} says goodbye.",
                                     packet=packet, type="73 sign off.")
            keys = sorted(message)
            # TODO write search func that can check main list for potential matches--where is the message 73ing to?
            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
                print("Message added to misc_comms list!")
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
                print("Message added to misc_comms list!")
        elif second_part == "RR73":
            convo_turn = MessageTurn(turn=0, message="".join(message),
                                     translated_message=f"{message[0]} says Roger Roger and signs off.",
                                     packet=packet, type="RR73")
            keys = sorted(message)
            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
                print("Message added to misc_comms list!")
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
                print("Message added to misc_comms list!")
        # Just two callsigns
        elif "/QRP" in "".join(message):
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
                print("Message added to convo_dict!")
            else:
                convo_turn = MessageTurn(turn=0, message="".join(message), translated_message=f"{message[1]} pings "
                                            f"{message[0]}.", packet=packet, type="Two Callsigns.")
                self.convo_dict[(keys[0], keys[1])] = [{"completed": False}, convo_turn]
                print("Message added to convo_dict!")

    def handle_longer_msg(self, packet: Packet, message: list):
        code = message[1]
        callsign = message[2]
        grid = message[3]
        if code in self.translation_templates:  # Only called for four part CQs
            translated_message = self.translation_templates[code].format(sender=callsign, grid=grid)
            convo_turn = CQ(message=" ".join(message), translated_message=translated_message, caller=callsign,
                            packet=packet)
            self.cqs.append(convo_turn)
            print("Longer message add to convo_dict")

    def is_signal_report(self, message: list):
        signal = message[-1]
        if len(signal) > 2:  # > 2 to return False for 73s
            if signal != "RR73" and signal != "RRR":
                if 'RR' in signal:
                    if int(signal[2:]) or signal[2:] == '00':
                        return True
                elif 'R' in signal:
                    if int(signal[1:]) or signal[1:] == '00':
                        return True
                else:
                    if int(signal[1:]) or signal[1:] == '00':
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

    def handle_cq(self, packet: Packet):
        split_message = packet.message.split()
        if len(split_message) == 4:
            self.handle_longer_msg(packet=packet, message=split_message)
        elif len(split_message) == 3:
            caller = packet.message.split()[1]
            print(packet.message)
            grid = packet.message.split()[2]
            translated = f"Station {caller} is calling for any response from grid {grid}."
            cq = CQ(packet=packet, message=packet.message, caller=caller, translated_message=translated)
            self.cqs.append(cq)
            print("CQ added to convo_dict")
        elif len(split_message) == 2:
            caller = packet.message.split()[1]
            translated = f"Station {caller} is calling for any response."
            cq = CQ(packet=packet, message=packet.message, caller=caller, translated_message=translated)
            self.cqs.append(cq)
            print("CQ added to convo_dict")
        else:
            cq = CQ(packet=packet, message=packet.message, caller=packet.message, translated_message="Unconfigured")
            self.cqs.append(cq)
            print("CQ added to convo_dict")

    def add_cq(self, callsigns: list):
        for callsign in callsigns:
            for cq in self.cqs:
                if cq.caller == callsign:
                    this_cq = cq
                    cq_turn = MessageTurn(turn=1, message=this_cq.message, translated_message=this_cq.translated_message,
                                  packet=this_cq.packet, type="CQ Call.")
                    self.convo_dict[(callsigns[0], callsigns[1])].insert(1, cq_turn)
                    self.cqs.remove(cq)
                    print("Updated convo_dict with initial CQ call.")
                    break
                else:
                    continue

# ---------------------DATA EXPORTING--------------------------
    def comms_to_json(self):
        with open("ft8_comms.json", "w") as json_file:
            json_dict = {"COMMS": [{}]}

            for k, v in self.convo_dict.items():
                key_str = str(k)
                json_dict["COMMS"][0][key_str] = []

                for item in v:
                    if isinstance(item, MessageTurn):
                        json_dict["COMMS"][0][key_str].append(asdict(item))
                    else:
                        json_dict["COMMS"][0][key_str].append(item)

            for k, v in json_dict.items():
                for i, field in enumerate(v):
                    if isinstance(field, Packet):
                        while len(json_dict[k]) <= i + 1:
                            json_dict[k].append({})
                        json_dict[k][i + 1]["packet"] = asdict(field)

            json_file.write(json.dumps(json_dict))

    def cqs_to_json(self):
        with open("ft8_cqs.json", "w") as json_file:
            json_dict = {"CQS": []}
            for i, cq in enumerate(self.cqs):
                while len(json_dict["CQS"]) <= i:
                    json_dict["CQS"].append({})

                if isinstance(cq, CQ):
                    json_dict["CQS"][i] = asdict(cq)
                else:
                    json_dict["CQS"][i] = cq

            for k, v in json_dict.items():
                for i, field in enumerate(v):
                    if isinstance(field, Packet):
                        while len(json_dict[k]) <= i + 1:
                            json_dict[k].append({})
                        json_dict[k][i + 1]["packet"] = asdict(field)

            json_file.write(json.dumps(json_dict))

    def misc_to_json(self):
        with open("ft8_misc.json", "w") as json_file:
            json_dict = {"MISC": []}

            for k, v in self.misc_comms.items():
                key_str = str(k)
                json_dict["MISC. COMMS"][0][key_str] = []

                for item in v:
                    if isinstance(item, MessageTurn):
                        json_dict["MISC. COMMS"][0][key_str].append(asdict(item))
                    else:
                        json_dict["MISC. COMMS"][0][key_str].append(item)

            for k, v in json_dict.items():
                for i, field in enumerate(v):
                    if isinstance(field, Packet):
                        while len(json_dict[k]) <= i + 1:
                            json_dict[k].append({})
                        json_dict[k][i + 1]["packet"] = asdict(field)
            json_file.write(json.dumps(json_dict))

    def to_json(self):
        with open("ft8_data.json", "w") as json_file:
            json_dict = {"COMMS": [{}], "CQS": [], "MISC. COMMS": [{}]}

            for k, v in self.convo_dict.items():
                key_str = str(k)
                json_dict["COMMS"][0][key_str] = []

                for item in v:
                    if isinstance(item, MessageTurn):
                        json_dict["COMMS"][0][key_str].append(asdict(item))
                    else:
                        json_dict["COMMS"][0][key_str].append(item)

            for i, cq in enumerate(self.cqs):
                while len(json_dict["CQS"]) <= i:
                    json_dict["CQS"].append({})

                if isinstance(cq, CQ):
                    json_dict["CQS"][i] = asdict(cq)
                else:
                    json_dict["CQS"][i] = cq

            for k, v in self.misc_comms.items():
                key_str = str(k)
                json_dict["MISC. COMMS"][0][key_str] = []

                for item in v:
                    if isinstance(item, MessageTurn):
                        json_dict["MISC. COMMS"][0][key_str].append(asdict(item))
                    else:
                        json_dict["MISC. COMMS"][0][key_str].append(item)

            for k, v in json_dict.items():
                for i, field in enumerate(v):
                    if isinstance(field, Packet):
                        while len(json_dict[k]) <= i + 1:
                            json_dict[k].append({})
                        json_dict[k][i + 1]["packet"] = asdict(field)

            data = json.dumps(json_dict, indent=2)
            json_file.write(data)
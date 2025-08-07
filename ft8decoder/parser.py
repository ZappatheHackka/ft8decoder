import socket
import logging
from datetime import datetime
import queue
import struct
from threading import Thread
from ft8decoder.processor import MessageProcessor
from ft8decoder.core import Packet

class WsjtxParser:
    def __init__(self, dial_frequency: float, log_level=logging.INFO):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.packet_queue = queue.Queue()
        self.dial_frequency = dial_frequency

    def frequency_handle(self, fq_offset: float):
        try:
            offset_mhz = fq_offset / 1_000_000
            frequency = self.dial_frequency + offset_mhz
            return frequency
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Invalid frequency offset {fq_offset}: {e}")
            return self.dial_frequency

    def determine_band(self, frequency: float):
        band_center_freqs = {
            "160m": 1.840,
            "80m": 3.573,
            "40m": 7.074,
            "30m": 10.136,
            "20m": 14.074,
            "17m": 18.100,
            "15m": 21.074,
            "12m": 24.915,
            "10m": 28.074,
            "6m": 50.313,
            "2m": 144.174
        }
        try:
            for band, freq in band_center_freqs.items():
                if abs(freq - frequency) < 0.015:
                    return band
            self.logger.debug(f"Unknown band for frequency {frequency} MHz")
            return "Unknown"
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Error determining band for frequency {frequency}: {e}")
            return "Unknown"

    def start_listening(self, host, port, processor: MessageProcessor):
        self.logger.info(f"Ready to listen on {host}:{port}...")
        ans = input("Begin packet parsing? (Y/n)\n").lower()
        if ans == "n":
            print("Quitting...")
            exit()
        if ans == "y":
            listen_thread = Thread(target=self.listen, args=(host, port, processor))
            listen_thread.start()
            self.logger.info(f"Listening on {host}:{port}...")

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
                except ConnectionResetError:
                    self.logger.warning("Connection reset. Continuing...")
                    continue
                except OSError as e:
                    self.logger.error(f"Network error: {e}")
                    break

        except socket.error as msg:
            print(f"Socket error: {msg}. Could not listen on {host}:{port}.")
            self.logger.error(f"Socket error: {msg}. Could not listen on {host}:{port}.")

    def parse_packets(self, data):
        try:
            message_type = struct.unpack(">I", data[8:12])[0]
            match message_type:
                case 2:
                    try: # Message packets
                        schema = struct.unpack('>I', data[4:8])[0]
                        program = struct.unpack('>6s', data[16:22])[0].decode('utf-8')
                        snr = struct.unpack(">i", data[27:31])[0]
                        time_delta = struct.unpack(">d", data[31:39])[0]
                        fq_offset = struct.unpack('>i', data[39:43])[0]
                        msg = data[52:-2]
                        decoded_msg = msg.decode('utf-8')
                        frequency = self.frequency_handle(fq_offset)
                        time = datetime.now()
                        parsed_packet = Packet(packet_type=message_type, schema=schema, program=program, snr=snr,
                                               delta_time=time_delta, frequency_offset=fq_offset, frequency=frequency,
                                               band=self.determine_band(frequency), message=decoded_msg, time_captured=str(time))
                        self.packet_queue.put(parsed_packet)
                    except (struct.error, UnicodeDecodeError, IndexError) as e:
                        self.logger.warning(f"Failed to parse message packet: {e}")
                        return
                case 1:  # Status packets
                    pass

        except Exception as e:
            self.logger.error(f"Unexpected error parsing packet: {e}")


    def start_grabbing(self, processor: MessageProcessor):
        while True:
            try:
                packet = self.packet_queue.get(timeout=1)  # Block for 1 second max
                processor.data_motherload.append(packet)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error packet grabbing: {e}")
                continue
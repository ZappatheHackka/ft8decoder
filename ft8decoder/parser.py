import socket
import logging
from datetime import datetime
import queue
import struct
from threading import Thread
from ft8decoder.processor import MessageProcessor
from ft8decoder.core import Packet

class WsjtxParser:
    """
        A UDP packet parser for WSJT-X FT8 messages.

        This class listens for UDP packets from WSJT-X software, parses the binary
        packet data to extract FT8 message information, and queues the parsed packets
        for processing by a MessageProcessor.

        The parser handles WSJT-X's binary protocol format and converts frequency
        offsets to absolute frequencies while determining the amateur radio band
        based on the calculated frequency.

        Attributes:
            logger (logging.Logger): Logger instance for this class
            packet_queue (queue.Queue): Thread-safe queue for storing parsed packets
            dial_frequency (float): Base dial frequency in MHz from WSJT-X

        Example:
            >>> parser = WsjtxParser(dial_frequency=14.074)
            >>> processor = MessageProcessor()
            >>> parser.start_listening('127.0.0.1', 2237, processor)
        """
    def __init__(self, dial_frequency: float, log_level=logging.INFO):
        """
               Initialize the WSJT-X packet parser.

               Sets up logging, initializes the packet queue, and stores the dial frequency
               used to calculate absolute frequencies from WSJT-X frequency offsets.

               Args:
                   dial_frequency (float): The dial frequency in MHz that WSJT-X is tuned to.
                                         Common FT8 frequencies include 14.074 MHz (20m),
                                         7.074 MHz (40m), etc.
                   log_level (int, optional): Python logging level. Defaults to logging.INFO.
                                            Use logging.DEBUG for verbose output.

               Example:
                   >>> # Initialize for 20m FT8
                   >>> parser = WsjtxParser(14.074, log_level=logging.DEBUG)
        """
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
        """
                Convert WSJT-X frequency offset to absolute frequency.

                WSJT-X sends frequency offsets in Hz relative to the dial frequency.
                This method converts the offset to MHz and adds it to the dial frequency
                to get the absolute transmission frequency.

                Args:
                    fq_offset (float): Frequency offset in Hz from WSJT-X packet data.
                                     Typically ranges from 0 to 3000 Hz for FT8.

                Returns:
                    float: Absolute frequency in MHz. Returns dial_frequency if offset
                          is invalid.

                Example:
                    >>> parser = WsjtxParser(14.074)
                    >>> freq = parser.frequency_handle(1500.0)  # 1500 Hz offset
                    >>> print(freq)  # 14.0755 MHz
        """
        try:
            offset_mhz = fq_offset / 1_000_000
            frequency = self.dial_frequency + offset_mhz
            return frequency
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Invalid frequency offset {fq_offset}: {e}")
            return self.dial_frequency

    def determine_band(self, frequency: float):
        """
                Determine amateur radio band from frequency.

                Maps the calculated frequency to the appropriate amateur radio band
                designation based on common FT8 frequencies. Uses a tolerance of
                ±15 kHz to account for frequency variations.

                Args:
                    frequency (float): Frequency in MHz to classify.

                Returns:
                    str: Band designation (e.g., "20m", "40m", "80m") or "Unknown"
                        if frequency doesn't match any known FT8 band.

                Example:
                    >>> parser = WsjtxParser(14.074)
                    >>> band = parser.determine_band(14.076)
                    >>> print(band)  # "20m"
        """
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
        """
                Start the UDP listening process with user confirmation.

                Prompts the user to confirm before starting packet capture, then
                launches the UDP listener in a separate thread. This is the main
                entry point for beginning FT8 packet capture.

                Args:
                    host (str): IP address to bind to, typically '127.0.0.1' for localhost.
                    port (int): UDP port number, typically 2237 for WSJT-X.
                    processor (MessageProcessor): Processor instance to handle parsed packets.

                Example:
                    >>> parser = WsjtxParser(14.074)
                    >>> processor = MessageProcessor()
                    >>> parser.start_listening('127.0.0.1', 2237, processor)
                    Ready to listen on 127.0.0.1:2237...
                    Begin packet parsing? (Y/n)
        """
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
        """
               Main UDP listening loop.

               Creates a UDP socket, binds to the specified host/port, and continuously
               listens for WSJT-X packets. Packets are parsed and valid ones are added
               to the processing queue. Also starts a background thread to move packets
               from the queue to the processor.

               Args:
                   host (str): IP address to bind the UDP socket to.
                   port (int): UDP port number to bind to.
                   processor (MessageProcessor): Processor to handle parsed packets.

               Note:
                   This method runs in an infinite loop until a network error occurs.
                   Uses a 1-second timeout on socket operations to prevent blocking.
        """
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
        """
               Parse binary WSJT-X packet data into structured Packet objects.

               Decodes the binary UDP packet format used by WSJT-X to extract message
               information including SNR, frequency offset, timestamp delta, and the
               decoded message text. Currently handles message packets (type 2) and
               ignores status packets (type 1).

               Args:
                   data (bytes): Raw UDP packet data from WSJT-X, minimum 12 bytes.

               The WSJT-X packet format includes:
                   - Header: Magic number, schema version, packet type
                   - Message data: SNR, time delta, frequency offset, message text

               Example packet structure for type 2 (message):
                   [0:4]   Magic number
                   [4:8]   Schema version
                   [8:12]  Message type (2 for decoded messages)
                   [27:31] SNR in dB
                   [31:39] Time delta in seconds
                   [39:43] Frequency offset in Hz
                   [52:-2] UTF-8 encoded message text
        """
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
        """
               Background thread to transfer packets from queue to processor.

               Continuously monitors the packet queue and transfers parsed packets
               to the MessageProcessor's data store. Runs in an infinite loop with
               a 1-second timeout to prevent blocking.

               Args:
                   processor (MessageProcessor): Processor instance to receive packets.

               Note:
                   This method runs in a separate thread and handles queue.Empty
                   exceptions gracefully to avoid blocking when no packets are available.
        """
        while True:
            try:
                packet = self.packet_queue.get(timeout=1)  # Block for 1 second max
                processor.data_motherload.append(packet)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error packet grabbing: {e}")
                continue
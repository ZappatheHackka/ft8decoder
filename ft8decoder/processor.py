import json
import logging
import time
from dataclasses import asdict
from threading import Thread

import folium
import maidenhead as mh

from ft8decoder.core import CQ, MessageTurn, Packet


class MessageProcessor:
    """
    Processes and categorizes FT8 messages into QSOs, CQs, and miscellaneous communications.

    This class takes parsed FT8 packets and intelligently categorizes them based on
    message content and structure. It tracks complete QSO (contact) sequences,
    identifies CQ calls, handles grid square exchanges, and provides data export
    and mapping functionality.

    The processor understands FT8 protocol semantics including:
    - CQ calls (general and targeted)
    - Two-way QSO establishment and completion
    - Signal reports and grid square exchanges
    - Various acknowledgment and sign-off messages

    Attributes:
        logger (logging.Logger): Logger for this class
        cqs (list): List of unmatched CQ calls
        qso_coords (list): Coordinates for completed QSOs with grid squares
        cq_coords (list): Coordinates for CQ calls with grid squares
        grid_square_cache (dict): Cache mapping callsigns to their grid squares
        data_motherload (list): Raw packet buffer from parser
        misc_comms (dict): Miscellaneous communications that don't fit QSO pattern
        qso_dict (dict): Complete QSO conversations indexed by sorted callsign pairs
        translation_templates (dict): Templates for translating special CQ types
        master_data (list): Combined view of all processed data

    Example:
        >>> processor = MessageProcessor()
        >>> processor.start(seconds=5)  # Process packets every 5 seconds
        >>> # After some time...
        >>> processor.to_json('ft8_data')  # Export all data
        >>> processor.to_map('ft8_map')  # Create world map
    """

    def __init__(self, log_level=logging.INFO):
        """
        Initialize the FT8 message processor.

        Sets up logging, initializes data structures for tracking different
        message types, and defines translation templates for special CQ calls
        like contests, Parks/Summits on the Air, and geographic targets.

        Args:
            log_level (int, optional): Python logging level. Defaults to logging.INFO.

        Example:
            >>> processor = MessageProcessor(log_level=logging.DEBUG)
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.cqs = []
        self.qso_coords = []
        self.cq_coords = []
        self.grid_square_cache = {}
        self.data_motherload = []
        self.misc_comms = {}
        self.qso_dict = {}
        self.translation_templates = {
            'DX': '{sender} is calling long-distance stations from grid {grid}.',
            'POTA': 'Parks on the Air participant {sender} is calling from grid {grid}.',
            'SOTA': 'Summits on the Air participant {sender} is calling from grid {grid}.',
            'TEST': '{sender} is making a contest call from grid {grid}.',
            'NA': '{sender} is calling North America from grid {grid}.',
            'EU': '{sender} is calling Europe from grid {grid}.',
            'SA': '{sender} is calling South America from grid {grid}.',
            'AS': '{sender} is calling Asia from grid {grid}.',
            'AF': '{sender} is calling Africa from grid {grid}.',
            'OC': '{sender} is calling Oceania from grid {grid}.',
            'JA': '{sender} is calling Japan from grid {grid}.',
            'HL': '{sender} is calling South Korea from grid {grid}.',
            'VK': '{sender} is calling Australia from grid {grid}.',
            'UA': '{sender} is calling Russia from grid {grid}.',
            'BV': '{sender} is calling Taiwan from grid {grid}.',
            'VOTA': 'Volunteers On The Air participant {sender} is calling from grid {grid}.',
            'ZL': '{sender} is calling New Zealand from grid {grid}.',
            'CN': '{sender} is calling China from grid {grid}.',
            'BY': '{sender} is calling China from grid {grid}.',
            'WFD': '{sender} is operating in Winter Field Day from grid {grid}.',
            'FD': '{sender} is operating in Field Day from grid {grid}.',
            'SKCC': '{sender} is calling SKCC (Straight Key Century Club) members'
                    ' from grid {grid}.',
            'NAQP': '{sender} is participating in the North American QSO Party from grid {grid}.',
            'ARRL': '{sender} is participating in an ARRL event from grid {grid}.',
            'CQWW': '{sender} is participating in CQ World Wide from grid {grid}.',
        }
        self.master_data = [
            {'Successfull Comms': self.qso_dict},
            {'CQs': self.cqs},
            {'Misc. Comms': self.misc_comms},
        ]

    def start(self, seconds=5):
        """
        Start the message processing thread.

        Launches a background thread that periodically processes accumulated
        packets from the data buffer. The thread runs continuously, processing
        packets at the specified interval.

        Args:
            seconds (int, optional): Interval between processing cycles in seconds.
                                   Defaults to 5. Shorter intervals provide more
                                   real-time processing but use more CPU.

        Example:
            >>> processor = MessageProcessor()
            >>> processor.start(seconds=3)  # Process every 3 seconds
        """
        thread = Thread(target=self.organize_messages, args=(seconds,))
        thread.start()
        self.logger.info(f'Message processor started with {seconds}s intervals')

    def organize_messages(self, seconds: int):
        """
        Main message processing loop that categorizes FT8 messages.

        This method runs continuously in a background thread, processing
        accumulated packets at regular intervals. It handles the complete
        FT8 message classification workflow:

        1. Copies and clears the packet buffer
        2. Parses each message to identify type (CQ, QSO, misc)
        3. Routes messages to appropriate handlers
        4. Tracks QSO progression and completion

        Args:
            seconds (int): Sleep interval between processing cycles.

        Message Classification Logic:
            - CQ messages: Start with "CQ" keyword
            - Two-word messages: Grid squares, sign-offs, acknowledgments
            - Three-word messages: Standard QSO exchanges (callsign pairs + data)
            - Four+ word messages: Special CQs with targets/events

        Example message flows:
            >>> # CQ sequence
            >>> "CQ W1ABC FN42" -> handle_cq()
            >>> "W1ABC K2DEF" -> new QSO started
            >>> "K2DEF W1ABC -15" -> signal report
            >>> "W1ABC K2DEF FN42" -> grid square
            >>> "K2DEF W1ABC RRR" -> acknowledgment
            >>> "W1ABC K2DEF 73" -> QSO completed
        """
        while True:
            time.sleep(seconds)
            packets_to_process = self.data_motherload.copy()
            self.data_motherload.clear()

            if packets_to_process:
                self.logger.info(f'Processing {len(packets_to_process)} packets...')
                for packet in packets_to_process:
                    try:
                        message = packet.message.split()
                        if message[0] == 'CQ':
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
                        if (callsigns[0], callsigns[1]) in self.qso_dict:
                            self.sort_message(packet, callsigns, new_convo=False)
                        else:
                            self.qso_dict[(callsigns[0], callsigns[1])] = [{'completed': False}]
                            self.sort_message(packet, callsigns, new_convo=True)
                    except Exception as e:
                        self.logger.error(f'Error processing packet {packet.message}: {e}')
                        continue
                self.logger.info(f'Processed {len(packets_to_process)} packets successfully')
            else:
                self.logger.info(f'No packets found, waiting {seconds} more seconds...')

    # Handles new messages & retroactively places CQ call in list
    def sort_message(self, packet: Packet, callsigns: list, new_convo: bool):
        """
        Route QSO messages to appropriate handlers based on content.

        This method analyzes three-word FT8 messages (typically callsign pairs
        plus additional data) and routes them to specialized handlers based on
        the message type. For new conversations, it also searches for and
        incorporates any matching CQ call.

        Args:
            packet (Packet): The packet containing the message to process.
            callsigns (list): Sorted list of two callsigns from the message.
            new_convo (bool): True if this is the first message in a QSO.

        Message Types Handled:
            - Acknowledgments: RRR, RR73, 73 (conversation enders)
            - Grid squares: 4-character locator codes (e.g., FN42, IO91)
            - Signal reports: Numeric SNR values with optional R/RR prefix
            - Unknown: Added to misc_comms for manual review

        Example:
            >>> # New QSO starting
            >>> sort_message(packet, ['K2DEF', 'W1ABC'], new_convo=True)
            >>> # Continues existing QSO
            >>> sort_message(packet, ['K2DEF', 'W1ABC'], new_convo=False)
        """
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
            self.logger.info(f'Could not parse packet: {packet.message}, adding to misc_comms')
            self.misc_comms[(message[0], message[1])] = packet

    def handle_short_msg(self, packet: Packet, message: list):
        """
        Process two-word FT8 messages.

        Handles various two-word message types including grid square announcements,
        sign-offs, acknowledgments, and QRP (low power) indicators. These messages
        are typically not part of structured QSOs but provide important information
        or conclude conversations.

        Args:
            packet (Packet): The packet containing the two-word message.
            message (list): List of two words from the message.

        Message Types:
            - Grid announcements: "CALLSIGN GRID" (e.g., "W1ABC FN42")
            - Sign-offs: "CALLSIGN 73" (goodbye message)
            - Roger + sign-off: "CALLSIGN RR73" (acknowledgment + goodbye)
            - QRP indicators: "CALLSIGN/QRP CALLSIGN" (low power operations)
            - Simple pings: "CALLSIGN1 CALLSIGN2" (basic contact attempt)

        Example:
            >>> handle_short_msg(packet, ['W1ABC', 'FN42'])  # Grid announcement
            >>> handle_short_msg(packet, ['W1ABC', '73'])  # Sign-off
            >>> handle_short_msg(packet, ['W1ABC/QRP', 'K2DEF'])  # QRP ping
        """
        second_part = message[1]
        if self.is_grid_square(message):
            convo_turn = MessageTurn(
                turn=0,
                message=''.join(message),
                translated_message=f'{message[0]} announces their position at {second_part}.',
                packet=packet,
                type='Grid Square announcement.',
            )
            keys = sorted(message)
            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
                self.logger.debug('Updated misc_comms list with message!')
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
                self.logger.debug('Updated misc_comms list with message!')
        elif second_part == '73':
            convo_turn = MessageTurn(
                turn=0,
                message=''.join(message),
                translated_message=f'{message[0]} says goodbye.',
                packet=packet,
                type='73 sign off.',
            )
            keys = sorted(message)

            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
                self.logger.debug('Updated misc_comms list with message!')
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
                self.logger.debug('Updated misc_comms list with message!')
        elif second_part == 'RR73':
            convo_turn = MessageTurn(
                turn=0,
                message=''.join(message),
                translated_message=f'{message[0]} says Roger Roger and signs off.',
                packet=packet,
                type='RR73',
            )
            keys = sorted(message)
            if (keys[0], keys[1]) in self.misc_comms:
                self.misc_comms[(keys[0], keys[1])].append(convo_turn)
                self.logger.debug('Updated misc_comms list with message!')
            else:
                self.misc_comms[(keys[0], keys[1])] = [convo_turn]
                self.logger.debug('Updated misc_comms list with message!')
        # Just two callsigns
        elif '/QRP' in ''.join(message):
            if '/QRP' in message[0]:
                keys = sorted(message)
                if (keys[0], keys[1]) in self.qso_dict:
                    convo_turn = MessageTurn(
                        turn=len(self.qso_dict[(keys[0], keys[1])]),
                        message=''.join(message),
                        translated_message=f'{message[1]} pings low power {message[0]}.',
                        packet=packet,
                        type='Two Callsigns',
                    )
                    self.qso_dict[(keys[0], keys[1])].append(convo_turn)
                    self.logger.debug('Updated qso_dict with message!')
                else:
                    convo_turn = MessageTurn(
                        turn=0,
                        message=''.join(message),
                        translated_message=f'{message[1]} pings low power {message[0]}.',
                        packet=packet,
                        type='Two Callsigns',
                    )
                    self.qso_dict[(keys[0], keys[1])] = [{'completed': False}, convo_turn]
                    self.logger.debug('Updated qso_dict with message!')
            else:
                keys = sorted(message)
                if (keys[0], keys[1]) in self.qso_dict:
                    convo_turn = MessageTurn(
                        turn=len(self.qso_dict[(keys[0], keys[1])]),
                        message=''.join(message),
                        translated_message=f'{message[1]} pings {message[0]} at low power.',
                        packet=packet,
                        type='Two Callsigns',
                    )
                    self.qso_dict[(keys[0], keys[1])].append(convo_turn)
                    self.logger.debug('Updated qso_dict with message!')
                else:
                    convo_turn = MessageTurn(
                        turn=0,
                        message=''.join(message),
                        translated_message=f'{message[1]} pings {message[0]} at low power.',
                        packet=packet,
                        type='Two Callsigns',
                    )
                    self.qso_dict[(keys[0], keys[1])] = [{'completed': False}, convo_turn]
                    self.logger.debug('Updated qso_dict with message!')
        else:
            keys = sorted(message)
            if (keys[0], keys[1]) in self.qso_dict:
                convo_turn = MessageTurn(
                    turn=len(self.qso_dict[(keys[0], keys[1])]),
                    message=''.join(message),
                    translated_message=f'{message[1]} pings {message[0]}.',
                    packet=packet,
                    type='Two Callsigns.',
                )
                self.qso_dict[(keys[0], keys[1])].append(convo_turn)
                self.logger.debug('Updated qso_dict with message!')
            else:
                convo_turn = MessageTurn(
                    turn=0,
                    message=''.join(message),
                    translated_message=f'{message[1]} pings {message[0]}.',
                    packet=packet,
                    type='Two Callsigns.',
                )
                self.qso_dict[(keys[0], keys[1])] = [{'completed': False}, convo_turn]
                self.logger.debug('Updated qso_dict with message!')

    def handle_longer_msg(self, packet: Packet, message: list):
        """
        Process messages with more than three words.

        Handles specialized CQ calls that include specific targets or event
        indicators. These four-word messages typically follow the format:
        "CQ EVENT CALLSIGN GRID" where EVENT specifies the type of activity
        or geographic target.

        Args:
            packet (Packet): The packet containing the multi-word message.
            message (list): List of words from the message (4+ words expected).

        Expected Format:
            message[0]: "CQ" (already verified by caller)
            message[1]: Event/target code (e.g., "DX", "POTA", "TEST", "NA")
            message[2]: Calling station's callsign
            message[3]: Calling station's grid square

        Example:
            >>> handle_longer_msg(packet, ['CQ', 'POTA', 'W1ABC', 'FN42'])
            >>> # Creates: "Parks on the Air participant W1ABC is calling from grid FN42."
        """
        code = message[1]
        callsign = message[2]
        grid = message[3]
        if code in self.translation_templates:  # Only called for four part CQs
            translated_message = self.translation_templates[code].format(sender=callsign, grid=grid)
            convo_turn = CQ(
                message=' '.join(message),
                translated_message=translated_message,
                caller=callsign,
                packet=packet,
            )
            if (callsign, grid) not in self.grid_square_cache:
                self.grid_square_cache[callsign] = grid
            self.cqs.append(convo_turn)
            self.logger.debug('Updated qso_dict with longer message!')

    def is_signal_report(self, message: list):
        """
        Determine if a message contains an FT8 signal report.

        FT8 signal reports are numeric values (typically -24 to +50 dB) that
        indicate signal strength and decoding quality. They may be prefixed
        with 'R' (received/roger) or 'RR' (roger roger) to indicate acknowledgment.

        Args:
            message (list): List of words from the FT8 message.

        Returns:
            bool: True if the last word appears to be a signal report.

        Signal Report Formats:
            - Simple: "+05", "-15", "00" (raw SNR values)
            - Roger: "R+05", "R-15" (acknowledging receipt)
            - Roger Roger: "RR+05", "RR-15" (confirming exchange)

        Example:
            >>> is_signal_report(['W1ABC', 'K2DEF', '-15'])  # True
            >>> is_signal_report(['W1ABC', 'K2DEF', 'R+05'])  # True
            >>> is_signal_report(['W1ABC', 'K2DEF', '73'])  # False
        """
        signal = message[-1]
        if len(signal) > 2:  # > 2 to return False for 73s
            if signal != 'RR73' and signal != 'RRR':
                if 'RR' in signal:
                    try:
                        if int(signal[2:]) or signal[2:] == '00':
                            return True
                    except ValueError:
                        return False
                elif 'R' in signal:
                    try:
                        if int(signal[2:]) or signal[2:] == '00':
                            return True
                    except ValueError:
                        return False
                else:
                    try:
                        if int(signal[1:]) or signal[1:] == '00':
                            return True
                    except ValueError:
                        return False
                return False
            return False
        return False

    def handle_signal_report(self, callsigns: list, packet: Packet, message: list):
        """
        Process FT8 signal report exchanges.

        Signal reports are a critical part of FT8 QSOs, indicating how well
        each station is receiving the other. This method creates a MessageTurn
        object with appropriate human-readable translation and adds it to the
        ongoing QSO conversation.

        Args:
            callsigns (list): Sorted pair of callsigns involved in the QSO.
            packet (Packet): The packet containing the signal report.
            message (list): Message words, with signal report as the last element.

        Signal Report Translation:
            - Reports with 'R' prefix indicate acknowledgment of previous report
            - Numeric value represents signal-to-noise ratio in dB
            - Positive values indicate strong signals, negative indicate weak

        Example:
            >>> # Message: ["W1ABC", "K2DEF", "R-08"]
            >>> handle_signal_report(['K2DEF', 'W1ABC'], packet, message)
            >>> # Creates: "K2DEF says Roger and reports a signal report of -08 to W1ABC."
        """
        first_callsign = message[0]
        second_callsign = message[1]
        if len(message[2]) > 3:
            nums = message[2][1:]
            translated_message = (
                f'{second_callsign} says Roger and reports a signal report of {nums} '
                f'to {first_callsign}.'
            )
        else:
            translated_message = (
                f'{second_callsign} sends a signal report of {message[2]} to {first_callsign}.'
            )

        # Putting this as the second signal report--assuming the CQ caller sends report first
        m_type = 'Signal Report'
        turn_obj = MessageTurn(
            turn=len(self.qso_dict[(callsigns[0], callsigns[1])]),
            message=packet.message,
            translated_message=translated_message,
            packet=packet,
            type=m_type,
        )
        self.qso_dict[(callsigns[0], callsigns[1])].append(turn_obj)
        self.logger.debug('Updated qso_dict with signal report.')

    def is_ack_reply(self, message):
        """
        Determine if a message is an acknowledgment or sign-off.

        FT8 conversations typically end with acknowledgment codes that confirm
        receipt of information and/or indicate the QSO is complete.

        Args:
            message (list): List of words from the FT8 message.

        Returns:
            bool: True if the message ends with a recognized acknowledgment code.

        Acknowledgment Types:
            - "RRR": Roger Roger Roger (confirmation received)
            - "RR73": Roger Roger + 73 (confirmation + goodbye)
            - "73": Best wishes/goodbye (QSO completion)

        Example:
            >>> is_ack_reply(['W1ABC', 'K2DEF', 'RRR'])  # True
            >>> is_ack_reply(['W1ABC', 'K2DEF', 'RR73'])  # True
            >>> is_ack_reply(['W1ABC', 'K2DEF', 'FN42'])  # False
        """
        code = message[-1]
        if code == 'RRR' or code == 'RR73' or code == '73':
            return True
        else:
            return False

    def handle_ack_reply(self, callsigns: list, packet: Packet, message: list):
        """
        Process acknowledgment and sign-off messages in QSOs.

        Handles the final stages of FT8 QSOs where stations confirm receipt
        of information and formally conclude the contact. Different acknowledgment
        types have specific meanings and some mark the QSO as completed.

        Args:
            callsigns (list): Sorted pair of callsigns involved in the QSO.
            packet (Packet): The packet containing the acknowledgment.
            message (list): Message words, with acknowledgment code as last element.

        Acknowledgment Processing:
            - "RRR": Simple confirmation, QSO implied complete
            - "RR73": Confirmation + goodbye, marks QSO as completed
            - "73": Goodbye message, marks QSO as completed

        Example:
            >>> # Message: ["W1ABC", "K2DEF", "RR73"]
            >>> handle_ack_reply(['K2DEF', 'W1ABC'], packet, message)
            >>> # Marks QSO as completed and adds final turn
        """
        ack = message[-1]
        if ack == 'RRR':
            translated_message = f'{message[1]} sends a Roger Roger Roger to {message[0]}.'
            convo_turn = MessageTurn(
                turn=(len(self.qso_dict[(callsigns[0], callsigns[1])])),
                message=packet.message,
                translated_message=translated_message,
                packet=packet,
                type='RRR',
            )
            self.qso_dict[(callsigns[0], callsigns[1])].append(convo_turn)
            self.qso_dict[(callsigns[0], callsigns[1])][0]['completed'] = True
            self.logger.debug('Updated qso_dict with RRR reply.')
        elif ack == 'RR73':
            translated_message = (
                f'{message[1]} sends a Roger Roger to {message[0]} and says goodbye, '
                f'concluding the connection.'
            )
            convo_turn = MessageTurn(
                turn=(len(self.qso_dict[(callsigns[0], callsigns[1])])),
                message=packet.message,
                translated_message=translated_message,
                packet=packet,
                type='RR & Goodbye',
            )
            self.qso_dict[(callsigns[0], callsigns[1])].append(convo_turn)
            self.qso_dict[(callsigns[0], callsigns[1])][0]['completed'] = True
            self.logger.debug('Updated qso_dict with RR73 reply.')
        elif ack == '73':
            translated_message = (
                f'{message[1]} sends their well wishes to {message[0]}, concluding the connection.'
            )
            convo_turn = MessageTurn(
                turn=(len(self.qso_dict[(callsigns[0], callsigns[1])])),
                message=packet.message,
                translated_message=translated_message,
                packet=packet,
                type='Goodbye',
            )
            self.qso_dict[(callsigns[0], callsigns[1])].append(convo_turn)
            self.qso_dict[(callsigns[0], callsigns[1])][0]['completed'] = True
            self.logger.debug('Updated qso_dict with 73 reply.')

    def is_grid_square(self, message):
        """
        Determine if a message contains a Maidenhead grid square locator.

        Maidenhead grid squares are a coordinate system used by amateur radio
        operators to specify geographic location. They follow the format of
        two uppercase letters followed by two digits (e.g., FN42, IO91).

        Args:
            message (list): List of words from the FT8 message.

        Returns:
            bool: True if the last word is a valid 4-character grid square.

        Grid Square Format:
            - Character 1: Uppercase letter (A-R, longitude field)
            - Character 2: Uppercase letter (A-R, latitude field)
            - Character 3: Digit (0-9, longitude square)
            - Character 4: Digit (0-9, latitude square)

        Example:
            >>> is_grid_square(['W1ABC', 'K2DEF', 'FN42'])  # True (valid grid)
            >>> is_grid_square(['W1ABC', 'K2DEF', 'fn42'])  # False (lowercase)
            >>> is_grid_square(['W1ABC', 'K2DEF', 'FN4'])  # False (too short)
        """
        square = str(message[-1])
        callsign = str(message[1])
        if len(square) == 4:
            if square[0].isalpha() and square[0].isupper():
                if square[1].isalpha() and square[1].isupper():
                    if square[2].isnumeric():
                        if square[3].isnumeric():
                            if (callsign, square) not in self.grid_square_cache:
                                self.grid_square_cache[callsign] = square
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
        """
        Process grid square location exchanges in QSOs.

        Grid square exchanges are a standard part of FT8 QSOs, allowing
        operators to share their geographic locations. The grid square is
        cached for later use in mapping and coordinate resolution.

        Args:
            callsigns (list): Sorted pair of callsigns involved in the QSO.
            packet (Packet): The packet containing the grid square.
            message (list): Message words, with grid square as the last element.

        Example:
            >>> # Message: ["W1ABC", "K2DEF", "FN42"]
            >>> handle_grid_square(['K2DEF', 'W1ABC'], packet, message)
            >>> # Creates: "K2DEF sends a grid square location of FN42 to W1ABC."
        """
        grid_square = message[-1]
        translated_message = (
            f'{message[1]} sends a grid square location of {grid_square} to {message[0]}.'
        )
        convo_turn = MessageTurn(
            turn=(len(self.qso_dict[(callsigns[0], callsigns[1])])),
            message=packet.message,
            translated_message=translated_message,
            packet=packet,
            type='Grid Square Report',
        )
        self.qso_dict[(callsigns[0], callsigns[1])].append(convo_turn)
        self.logger.debug('Updated qso_dict with grid square report.')

    def handle_cq(self, packet: Packet):
        """
        Process CQ (calling any station) messages.

        CQ calls are the foundation of amateur radio contacts, indicating that
        a station is available for communication. This method handles various
        CQ formats from simple general calls to complex targeted calls with
        event indicators.

        Args:
            packet (Packet): The packet containing the CQ message.

        CQ Message Formats:
            - 2 words: "CQ CALLSIGN" (general call)
            - 3 words: "CQ CALLSIGN GRID" (call with location)
            - 4 words: "CQ EVENT CALLSIGN GRID" (targeted/special event call)

        Example:
            >>> handle_cq(packet)  # packet.message = "CQ W1ABC FN42"
            >>> # Creates: "Station W1ABC is calling for any response from grid FN42."
        """
        split_message = packet.message.split()
        if len(split_message) == 4:
            self.handle_longer_msg(packet=packet, message=split_message)
        elif len(split_message) == 3:
            caller = packet.message.split()[1]
            grid = packet.message.split()[2]
            if (caller, grid) not in self.grid_square_cache.items():
                self.grid_square_cache[caller] = grid
            translated = f'Station {caller} is calling for any response from grid {grid}.'
            cq = CQ(
                packet=packet, message=packet.message, caller=caller, translated_message=translated
            )
            self.cqs.append(cq)
            self.logger.debug('Updated qso_dict with CQ.')
        elif len(split_message) == 2:
            caller = packet.message.split()[1]
            translated = f'Station {caller} is calling for any response.'
            cq = CQ(
                packet=packet, message=packet.message, caller=caller, translated_message=translated
            )
            self.cqs.append(cq)
            self.logger.debug('Updated qso_dict with CQ.')
        else:
            cq = CQ(
                packet=packet,
                message=packet.message,
                caller=packet.message,
                translated_message='Unconfigured',
            )
            self.cqs.append(cq)
            self.logger.debug('Updated qso_dict with CQ.')

    def add_cq(self, callsigns: list):
        """
        Link CQ calls to newly started QSOs.

        When a new QSO begins, this method searches for any matching CQ call
        from one of the participants and incorporates it as the first turn
        of the conversation. This provides complete context for how the
        contact was initiated.

        Args:
            callsigns (list): Sorted pair of callsigns starting a new QSO.

        Process:
            1. Search through unmatched CQ calls
            2. Find CQ from either callsign in the new QSO
            3. Convert CQ to MessageTurn and insert as turn 1
            4. Remove CQ from unmatched list

        Example:
            >>> # Previous CQ: "CQ W1ABC FN42"
            >>> # New QSO starts: "W1ABC K2DEF"
            >>> add_cq(['K2DEF', 'W1ABC'])
            >>> # CQ becomes turn 1 of the W1ABC/K2DEF conversation
        """
        for callsign in callsigns:
            for cq in self.cqs:
                if cq.caller == callsign:
                    this_cq = cq
                    cq_turn = MessageTurn(
                        turn=1,
                        message=this_cq.message,
                        translated_message=this_cq.translated_message,
                        packet=this_cq.packet,
                        type='CQ Call.',
                    )
                    self.qso_dict[(callsigns[0], callsigns[1])].insert(1, cq_turn)
                    self.cqs.remove(cq)
                    self.logger.debug('Updated qso_dict with initial CQ call.')
                    break
                else:
                    continue

    # Given grid square, returns Lat/Lon
    def resolve_grid_square(self, grid_square):
        """
        Convert Maidenhead grid square to latitude/longitude coordinates.

        Uses the maidenhead library to convert 4-character grid squares into
        decimal degree coordinates for mapping and distance calculations.
        Returns a dictionary with coordinate information and a Google Maps link.

        Args:
            grid_square (str): 4-character Maidenhead grid square (e.g., "FN42").

        Returns:
            dict or None: Dictionary containing grid square, coordinates, and map URL.
                         Returns None if conversion fails.

        Return Format:
            {
                "Grid Square": "FN42",
                "Latitude": "42.5",
                "Longitude": "-71.5",
                "Map URL": "https://www.google.com/maps?q=42.5,-71.5"
            }

        Example:
            >>> coords = resolve_grid_square('FN42')
            >>> print(f'Location: {coords["Latitude"]}, {coords["Longitude"]}')
            >>> # Location: 42.5, -71.5
        """
        try:
            coords = mh.to_location(grid_square, center=True)
            return {
                'Grid Square': grid_square,
                'Latitude': str(coords[0]),
                'Longitude': str(coords[1]),
                'Map URL': f'https://www.google.com/maps?q={str(coords[0])},{str(coords[1])}',
            }
        except Exception as e:
            self.logger.warning(f'Failed to resolve grid square {grid_square}: {e}')
            return None

    # ---------------------DATA EXPORTING--------------------------
    def comms_to_json(self, filename: str):
        """
        Export QSO conversation data to JSON file.

        Serializes all completed and in-progress QSO conversations to a JSON
        file for analysis, archival, or import into other applications. Each
        QSO is indexed by the sorted callsign pair and contains all message
        turns with metadata.

        Args:
            filename (str): Output filename, .json extension added if missing.

        Raises:
            IOError: If file cannot be written due to permissions or disk space.
            OSError: If filename/path is invalid.

        JSON Structure:
            {
                "COMMS": [{
                    "('CALL1', 'CALL2')": [
                        {"completed": false},
                        {MessageTurn data...},
                        {MessageTurn data...}
                    ]
                }]
            }

        Example:
            >>> processor.comms_to_json('my_qsos')
            >>> # Creates my_qsos.json with all QSO data
        """
        if filename.endswith('.json'):
            out_filename = filename
        else:
            out_filename = f'{filename}.json'

        try:
            with open(out_filename, 'w') as json_file:
                json_dict = {'COMMS': [{}]}

                for k, v in self.qso_dict.items():
                    key_str = str(k)
                    json_dict['COMMS'][0][key_str] = []

                    for item in v:
                        if isinstance(item, MessageTurn):
                            json_dict['COMMS'][0][key_str].append(asdict(item))
                        else:
                            json_dict['COMMS'][0][key_str].append(item)

                for k, v in json_dict.items():
                    for i, field in enumerate(v):
                        if isinstance(field, Packet):
                            while len(json_dict[k]) <= i + 1:
                                json_dict[k].append({})
                            json_dict[k][i + 1]['packet'] = asdict(field)

                json_file.write(json.dumps(json_dict))
                self.logger.debug(f'QSOs exported to {out_filename}')

        except OSError as e:
            self.logger.error(f'Failed to write QSOs to {out_filename}: {e}')
            raise

    def cqs_to_json(self, filename: str):
        """
        Export unanswered CQ calls to JSON file.

        Saves all CQ calls that have not yet been matched to QSO conversations.
        Useful for analyzing calling patterns, popular frequencies, and
        propagation conditions.

        Args:
            filename (str): Output filename, .json extension added if missing.

        Raises:
            IOError: If file cannot be written.
            OSError: If filename/path is invalid.

        JSON Structure:
            {
                "CQS": [
                    {CQ object data...},
                    {CQ object data...}
                ]
            }

        Example:
            >>> processor.cqs_to_json('unanswered_cqs')
            >>> # Creates unanswered_cqs.json with CQ data
        """
        if filename.endswith('.json'):
            out_filename = filename
        else:
            out_filename = f'{filename}.json'
        try:
            with open(out_filename, 'w') as json_file:
                json_dict = {'CQS': []}
                for i, cq in enumerate(self.cqs):
                    while len(json_dict['CQS']) <= i:
                        json_dict['CQS'].append({})

                    if isinstance(cq, CQ):
                        json_dict['CQS'][i] = asdict(cq)
                    else:
                        json_dict['CQS'][i] = cq

                for k, v in json_dict.items():
                    for i, field in enumerate(v):
                        if isinstance(field, Packet):
                            while len(json_dict[k]) <= i + 1:
                                json_dict[k].append({})
                            json_dict[k][i + 1]['packet'] = asdict(field)

                json_file.write(json.dumps(json_dict))
                self.logger.debug(f'CQs exported to {out_filename}')

        except OSError as e:
            self.logger.error(f'Failed to write CQs to {out_filename}: {e}')
            raise

    def misc_to_json(self, filename: str):
        """
        Export miscellaneous communications to JSON file.

        Saves communications that don't fit the standard QSO pattern, including
        grid announcements, standalone sign-offs, and unrecognized message formats.
        Useful for debugging message parsing and analyzing non-standard activity.

        Args:
            filename (str): Output filename, .json extension added if missing.

        Raises:
            IOError: If file cannot be written.
            OSError: If filename/path is invalid.

        Example:
            >>> processor.misc_to_json('misc_messages')
            >>> # Creates misc_messages.json
        """
        if filename.endswith('.json'):
            out_filename = filename
        else:
            out_filename = f'{filename}.json'

        try:
            with open(out_filename, 'w') as json_file:
                json_dict = {'MISC': []}

                for k, v in self.misc_comms.items():
                    key_str = str(k)
                    json_dict['MISC. COMMS'][0][key_str] = []

                    for item in v:
                        if isinstance(item, MessageTurn):
                            json_dict['MISC. COMMS'][0][key_str].append(asdict(item))
                        else:
                            json_dict['MISC. COMMS'][0][key_str].append(item)

                for k, v in json_dict.items():
                    for i, field in enumerate(v):
                        if isinstance(field, Packet):
                            while len(json_dict[k]) <= i + 1:
                                json_dict[k].append({})
                            json_dict[k][i + 1]['packet'] = asdict(field)
                json_file.write(json.dumps(json_dict))
                self.logger.debug(f'misc messages exported to {out_filename}')

        except OSError as e:
            self.logger.error(f'Failed to write misc messages to {out_filename}: {e}')
            raise

    def to_json(self, filename: str):
        """
        Export all captured FT8 data to a comprehensive JSON file.

        Creates a complete export containing QSO conversations, unanswered CQ calls,
        and miscellaneous communications in a single file. This is the most
        comprehensive export option for complete session analysis.

        Args:
            filename (str): Output filename, .json extension added if missing.

        Raises:
            IOError: If file cannot be written due to permissions or disk space.
            OSError: If filename/path is invalid.

        JSON Structure:
            {
                "COMMS": [{QSO conversations...}],
                "CQS": [{CQ calls...}],
                "MISC. COMMS": [{miscellaneous messages...}]
            }

        Example:
            >>> processor.to_json('complete_session')
            >>> # Creates complete_session.json with all data types
        """
        if filename.endswith('.json'):
            out_filename = filename
        else:
            out_filename = f'{filename}.json'

        try:
            with open(out_filename, 'w') as json_file:
                json_dict = {'COMMS': [{}], 'CQS': [], 'MISC. COMMS': [{}]}

                for k, v in self.qso_dict.items():
                    key_str = str(k)
                    json_dict['COMMS'][0][key_str] = []

                    for item in v:
                        if isinstance(item, MessageTurn):
                            json_dict['COMMS'][0][key_str].append(asdict(item))
                        else:
                            json_dict['COMMS'][0][key_str].append(item)

                for i, cq in enumerate(self.cqs):
                    while len(json_dict['CQS']) <= i:
                        json_dict['CQS'].append({})

                    if isinstance(cq, CQ):
                        json_dict['CQS'][i] = asdict(cq)
                    else:
                        json_dict['CQS'][i] = cq

                for k, v in self.misc_comms.items():
                    key_str = str(k)
                    json_dict['MISC. COMMS'][0][key_str] = []

                    for item in v:
                        if isinstance(item, MessageTurn):
                            json_dict['MISC. COMMS'][0][key_str].append(asdict(item))
                        else:
                            json_dict['MISC. COMMS'][0][key_str].append(item)

                for k, v in json_dict.items():
                    for i, field in enumerate(v):
                        if isinstance(field, Packet):
                            while len(json_dict[k]) <= i + 1:
                                json_dict[k].append({})
                            json_dict[k][i + 1]['packet'] = asdict(field)

                data = json.dumps(json_dict, indent=2)
                json_file.write(data)
                self.logger.debug(f'All messages exported to {out_filename}')
        except OSError as e:
            self.logger.error(f'Failed to write all messages to {out_filename}: {e}')
            raise

    # -------------MAPPING-------------

    def gather_coords(self):
        """
        Collect and resolve geographic coordinates for QSOs and CQ calls.

        Processes the grid square cache to convert Maidenhead locators into
        latitude/longitude coordinates for mapping purposes. Creates coordinate
        tuples for both QSOs (with connection lines, as long as both participants
        have sent their grid squares) and CQ calls (as individual points).

        Coordinate Resolution Process:
            1. Check QSO participants for cached grid squares
            2. Resolve grid squares to lat/lon coordinates
            3. Create QSO coordinate tuples with both endpoints
            4. Process CQ calls similarly for standalone points

        Populates:
            self.qso_coords: List of QSO coordinate tuples
            self.cq_coords: List of CQ coordinate tuples

        QSO Coordinate Format:
            ((callsign1, lat1, lon1), (callsign2, lat2, lon2), (timestamp,))

        CQ Coordinate Format:
            (message, timestamp, latitude, longitude)

        Example:
            >>> processor.gather_coords()
            >>> print(f'Found {len(processor.qso_coords)} QSOs with coordinates')
            >>> print(f'Found {len(processor.cq_coords)} CQs with coordinates')
        """
        for key in self.qso_dict:  # Gathering QSO coords
            if (
                key[0].strip() in self.grid_square_cache
                and key[1].strip() in self.grid_square_cache
            ):
                if len(self.qso_dict[(key[0], key[1])]) > 2:
                    time_captured = self.qso_dict[(key[0], key[1])][2].packet.time_captured
                else:
                    time_captured = self.qso_dict[(key[0], key[1])][1].packet.time_captured
                first_coords = self.resolve_grid_square(self.grid_square_cache[key[0]])
                second_coords = self.resolve_grid_square(self.grid_square_cache[key[1]])

                if first_coords and second_coords:
                    coord_tuple = (
                        (key[0], first_coords['Latitude'], first_coords['Longitude']),
                        (key[1], second_coords['Latitude'], second_coords['Longitude']),
                        (time_captured,),
                    )
                    self.qso_coords.append(coord_tuple)
                    self.logger.debug(f'Added coordinates for QSO between {key[0]} and {key[1]}')
                else:
                    self.logger.warning(
                        f'Failed to resolve coordinates for QSO between {key[0]} and {key[1]}'
                    )
            else:
                self.logger.debug(f'Missing grid squares for QSO between {key[0]} and {key[1]}')

        for cq in self.cqs:  # Gathering CQ coords
            split_message = cq.message.split()
            time_captured = cq.packet.time_captured
            if len(split_message) < 4:
                callsign = split_message[1]
                if callsign in self.grid_square_cache:
                    cq_coords = self.resolve_grid_square(self.grid_square_cache[callsign])
                    if cq_coords:
                        cq_tuple = (
                            cq.message,
                            time_captured,
                            cq_coords['Latitude'],
                            cq_coords['Longitude'],
                        )
                        self.cq_coords.append(cq_tuple)
                        self.logger.debug(f'Added coordinates for CQ from {callsign}')
                else:
                    self.logger.warning(f'Failed to resolve grid square for CQ from {callsign}')
            else:
                callsign = split_message[2]
                if callsign in self.grid_square_cache:
                    cq_coords = self.resolve_grid_square(self.grid_square_cache[callsign])
                    if cq_coords:
                        cq_tuple = (
                            cq.message,
                            time_captured,
                            cq_coords['Latitude'],
                            cq_coords['Longitude'],
                        )
                        self.cq_coords.append(cq_tuple)
                        self.logger.debug(f'Added coordinates for CQ from {callsign}')
                else:
                    self.logger.warning(f'Failed to resolve grid square for CQ from {callsign}')

    def to_map(self, filename: str, all_cqs: bool = True):
        """
        Generate an interactive world map of FT8 activity.

        Creates a Folium-based HTML map showing QSO connections as lines between
        stations and CQ calls as individual markers. The map is automatically
        centered based on QSO activity and includes interactive layers for
        different data types.

        Args:
            filename (str): Output filename for the HTML map (without .html extension).
            all_cqs (bool, optional): If True, show all CQ calls. If False, only
                                     show CQs from stations that have not participated in a QSO.
                                     Defaults to True.

        Raises:
            Exception: If map generation fails due to coordinate resolution errors
                      or file writing issues.

        Map Features:
            - QSO participants: Green radio icons with callsign popups
            - QSO connections: Blue lines connecting stations with QSO details
            - CQ calls: Red radio icons for unanswered calls
            - Layer control: Toggle between QSOs and CQs
            - Auto-centering: Map centers on mean QSO coordinates

        Map Centering Logic:
            - If 3+ QSOs with coordinates: Centers on mean lat/lon of all participants
            - If <3 QSOs: Uses default world view (0,0) coordinates

        Example:
            >>> processor.to_map('activity_map')
            >>> # Creates activity_map.html with all QSOs and CQs
            >>> processor.to_map('qso_only', all_cqs=False)
            >>> # Creates qso_only.html showing only successful contacts
        """
        try:
            self.gather_coords()

            if len(self.qso_coords) > 3:
                cumulative_lat = 0
                cumulative_lon = 0
                total_len = len(self.qso_coords)
                for tuple in self.qso_coords:
                    cumulative_lat += float(tuple[0][1]) + float(tuple[1][1])
                    cumulative_lon += float(tuple[0][2]) + float(tuple[1][2])

                mean_lat = round(cumulative_lat / total_len, 2)
                mean_lon = round(cumulative_lon / total_len, 2)

                m = folium.Map(location=(mean_lat, mean_lon), zoom_start=2)
                self.logger.info(f'Created map centered at {mean_lat}, {mean_lon}')
            else:
                m = folium.Map(location=(0, 0), zoom_start=2)
                self.logger.info(
                    'Created map with default center (insufficient QSO data for centering)'
                )

            cqs = folium.FeatureGroup('CQs').add_to(m)
            qsos = folium.FeatureGroup('QSOs').add_to(m)

            for coords in self.qso_coords:
                folium.Marker(
                    location=[coords[0][1], coords[0][2]],
                    tooltip='QSO Participant',
                    popup=coords[0][0],
                    icon=folium.Icon(icon='radio', prefix='fa', color='green'),
                ).add_to(qsos)
                point1 = (float(coords[0][1]), float(coords[0][2]))

                folium.Marker(
                    location=[coords[1][1], coords[1][2]],
                    tooltip='QSO Participant',
                    popup=coords[1][0],
                    icon=folium.Icon(icon='radio', prefix='fa', color='green'),
                ).add_to(qsos)
                point2 = (float(coords[1][1]), float(coords[1][2]))

                line = folium.PolyLine(
                    locations=[point1, point2],
                    color='blue',
                    weight=3,
                    opacity=0.55,
                    tooltip=f'QSO between {coords[0][0]} and {coords[1][0]}',
                    popup=f'Contact began at {coords[2]}.',
                )
                line.add_to(m)

                qso_callsigns = []
                for coords in self.qso_coords:
                    qso_callsigns.append(str(coords[0][0]))
                    qso_callsigns.append(str(coords[1][0]))

                for cq in self.cq_coords:
                    callsign = ''.join(cq[0])
                    if not all_cqs:
                        if callsign in qso_callsigns:
                            continue
                    else:
                        time_captured = cq[1]
                        folium.Marker(
                            location=[cq[2], cq[3]],
                            tooltip='Unanswered CQ call',
                            popup=f'{callsign}, {time_captured}',
                            icon=folium.Icon(icon='radio', prefix='fa', color='red'),
                        ).add_to(cqs)

            folium.LayerControl().add_to(m)
            m.save(f'{filename}.html')
            self.logger.info(
                f'Map saved as {filename}.html with {len(self.qso_coords)} QSOs'
                f' and {len(self.cq_coords)} CQs'
            )

        except Exception as e:
            self.logger.error(f'Failed to create map {filename}.html: {e}')
            raise

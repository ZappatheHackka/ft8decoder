from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Packet:
    """
    Represents a WSJT-X UDP packet containing signal and metadata information for each
    captured FT8 message.

    Attributes:
        snr: Signal-to-noise ratio in decibels
        delta_time: Time offset from expected timing in seconds
        frequency_offset: Frequency offset from expected frequency in Hz
        frequency: Actual received frequency in Hz or MHz
        band: Radio frequency band (e.g., "20m", "40m", "2m")
        message: Raw message content from the packet
        schema: Schema version or protocol identifier
        program: Software/program that captured or processed the packet
        time_captured: Timestamp when the packet was received (ISO format string)
        packet_type: Numeric identifier for the type of packet
    """

    snr: int
    delta_time: float
    frequency_offset: int
    frequency: float
    band: str
    message: str
    schema: int
    program: str
    time_captured: str
    packet_type: int


@dataclass
class MessageTurn:
    """
    Represents a single turn in a radio communication exchange.

    Attributes:
        turn: Sequential turn number in the conversation
        message: Original raw message content
        translated_message: Human-readable or decoded version of the message
        packet: Associated Packet object or string identifier
        type: Type of message turn (e.g., "CQ", "response", "73")
    """

    turn: int
    message: str
    translated_message: str
    packet: Packet | str
    type: str


@dataclass
class CQ:
    """
    Represents a CQ (calling any station) message in amateur radio.

    CQ messages are general calls broadcast to invite any station to respond,
    typically used to initiate new contacts or conversations.

    Attributes:
        message: Original CQ message content
        translated_message: Human-readable interpretation of the CQ
        caller: Call sign of the station making the CQ call
        packet: Packet object containing the raw signal data
    """

    message: str
    translated_message: str
    caller: str
    packet: Packet

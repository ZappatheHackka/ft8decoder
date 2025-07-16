from dataclasses import dataclass

@dataclass
class Packet:
    snr: int
    delta_time: float
    frequency: int
    message: str
    schema: int
    program: str
    packet_type: int

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

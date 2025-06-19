class Packet:
    def __init__(self, packet_type: int, schema: int, program: str, snr: int, delta_time: float, frequency: int,
                 message: str):
        self.snr = snr #
        self.delta_time = delta_time
        self.frequency = frequency
        self.message = message
        self.schema = schema
        self.program = program
        self.packet_type = packet_type

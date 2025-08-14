from ft8decoder.parser import WsjtxParser

# Raw byte parsing tests


def test_packet_parsing_cq():
    raw_bytes = (b'\xad\xbc\xcb\xda\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x06WSJT-X'
                 b'\x01\x04\x05\r\x80\x00\x00\x00\x03?\xc9\x99\x99\xa0\x00\x00\x00\x00\x00'
                 b'\x03\x9e\x00\x00\x00\x01~\x00\x00\x00\x0cCQ NU1D EN61\x00\x00')
    parser = WsjtxParser(dial_frequency=14.074000)
    parser.parse_packets(raw_bytes)
    packet = parser.packet_queue.get()
    assert packet.message == 'CQ NU1D EN61'
    assert packet.schema == 2
    assert packet.program == 'WSJT-X'
    assert packet.packet_type == 2
    assert packet.snr == 3
    assert packet.delta_time == 0.20000000298023224
    assert packet.frequency_offset == 926
    assert packet.frequency == 14.074926
    assert packet.band == '20m'


def test_packet_parsing_grid():
    raw_bytes = (b'\xad\xbc\xcb\xda\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x06WSJT-X'
                 b'\x01\x04\x14cH\xff\xff\xff\xf0?\xe0\x00\x00\x00\x00\x00\x00\x00\x00\x03%'
                 b'\x00\x00\x00\x01~\x00\x00\x00\x11BG5JGG PA8DC JO21\x00\x00')
    parser = WsjtxParser(dial_frequency=14.074000)
    parser.parse_packets(raw_bytes)
    packet = parser.packet_queue.get()
    assert packet.message == 'BG5JGG PA8DC JO21'
    assert packet.schema == 2
    assert packet.program == 'WSJT-X'
    assert packet.packet_type == 2
    assert packet.snr == -16
    assert packet.delta_time == 0.5
    assert packet.frequency_offset == 805
    assert packet.frequency == 14.074805
    assert packet.band == '20m'


def test_packet_parsing_RR73():
    raw_bytes = (b'\xad\xbc\xcb\xda\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x06WSJT-X'
                 b'\x01\x04\x14cH\xff\xff\xff\xec?\xe0\x00\x00\x00\x00\x00\x00\x00\x00\x03'
                 b'\xb6\x00\x00\x00\x01~\x00\x00\x00\x11S56GS PA0NKK RR73\x00\x00')
    parser = WsjtxParser(dial_frequency=14.074000)
    parser.parse_packets(raw_bytes)
    packet = parser.packet_queue.get()
    assert packet.message == 'S56GS PA0NKK RR73'
    assert packet.schema == 2
    assert packet.program == 'WSJT-X'
    assert packet.packet_type == 2
    assert packet.snr == -20
    assert packet.delta_time == 0.5
    assert packet.frequency_offset == 950
    assert packet.frequency == 14.07495
    assert packet.band == '20m'

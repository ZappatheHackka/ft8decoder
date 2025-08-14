from ft8decoder import CQ, MessageProcessor, MessageTurn, Packet

# IDENTIFYING MESSAGES

def test_is_grid_square():
    true_data = ['W1AW', 'K9XYZ', 'EL09']
    false_data = ['W1AW', 'K9XYZ', '73']
    false_again = ['W1AW', 'KYBA9', 'R+02']
    processor = MessageProcessor()

    assert processor.is_grid_square(true_data) is True
    assert processor.is_grid_square(false_data) is False
    assert processor.is_grid_square(false_again) is False


def test_is_signal_report():
    true_data = ['W1AW', 'K9XYZ', 'R-09']
    true_data_ = ['W1AW', 'K9XYZ', '+12']
    false_data = ['W1AW', 'K9XYZ', 'EN56']
    processor = MessageProcessor()

    assert processor.is_signal_report(true_data) is True
    assert processor.is_signal_report(true_data_) is True
    assert processor.is_signal_report(false_data) is False


def test_is_ack_reply():
    true_data = ['W1AW', 'K9XYZ', '73']
    true_data_ = ['W1AW', 'K9XYZ', 'RR73']
    false_data = ['W1AW', 'K9XYZ', 'EN56']
    false_data_ = ['W1AW', 'KYBA9', 'R+02']

    processor = MessageProcessor()

    assert processor.is_ack_reply(true_data) is True
    assert processor.is_ack_reply(true_data_) is True
    assert processor.is_ack_reply(false_data) is False
    assert processor.is_ack_reply(false_data_) is False


# HANDLING MESSAGES


def test_handle_signal_report():
    test_data_packet = Packet(
        snr=-20,
        delta_time=0.5,
        frequency_offset=950,
        frequency=14.07495,
        band='20m',
        message='W1AW K9XYZ -10',
        program='WSJT-X',
        schema=2,
        packet_type=2,
    )
    test_message_list = ['W1AW', 'K9XYZ', '-10']
    test_callsigns = sorted(['W1AW', 'K9XYZ'])

    expected_result = [
        MessageTurn(
            turn=0,
            message='W1AW K9XYZ -10',
            translated_message=f'{test_message_list[1]} '
            f'sends a signal report of {test_message_list[2]} to {test_message_list[0]}.',
            packet=test_data_packet,
            type='Signal Report',
        ),
    ]

    processor = MessageProcessor()
    processor.qso_dict[(test_callsigns[0], test_callsigns[1])] = []
    processor.handle_signal_report(
        callsigns=test_callsigns, message=test_message_list, packet=test_data_packet
    )

    assert processor.qso_dict[(test_callsigns[0], test_callsigns[1])] == expected_result


def test_handle_ack_reply():
    test_data_packet = Packet(
        snr=-20,
        delta_time=0.5,
        frequency_offset=950,
        message='W1AW K9XYZ RR73',
        program='WSJT-X',
        schema=2,
        packet_type=2,
        band='20m',
        frequency=14.07495,
    )
    test_message_list = ['W1AW', 'K9XYZ', 'RR73']
    test_callsigns = sorted(['W1AW', 'K9XYZ'])

    processor = MessageProcessor()
    processor.qso_dict[(test_callsigns[0], test_callsigns[1])] = [{'completed': False}]

    expected_result = [
        {'completed': True},
        MessageTurn(
            turn=1,
            message='W1AW K9XYZ RR73',
            translated_message=f'{test_message_list[1]} '
            f'sends a Roger Roger to {test_message_list[0]} and says goodbye,'
            f' concluding the connection.',
            packet=test_data_packet,
            type='RR & Goodbye',
        ),
    ]

    processor.handle_ack_reply(
        callsigns=test_callsigns, message=test_message_list, packet=test_data_packet
    )

    assert processor.qso_dict[(test_callsigns[0], test_callsigns[1])] == expected_result


def test_handle_grid_square():
    test_data_packet = Packet(
        snr=-20,
        delta_time=0.5,
        frequency_offset=950,
        message='W1AW K9XYZ EN87',
        program='WSJT-X',
        schema=2,
        packet_type=2,
        frequency=14.07495,
        band='20m',
    )
    test_message_list = ['W1AW', 'K9XYZ', 'EN87']
    test_callsigns = sorted(['W1AW', 'K9XYZ'])

    processor = MessageProcessor()
    processor.qso_dict[(test_callsigns[0], test_callsigns[1])] = []

    expected_result = [
        MessageTurn(
            turn=0,
            message='W1AW K9XYZ EN87',
            translated_message=f'{test_message_list[1]} '
            f'sends a grid square location of {test_message_list[-1]} to {test_message_list[0]}.',
            packet=test_data_packet,
            type='Grid Square Report',
        )
    ]

    processor.handle_grid_square(
        packet=test_data_packet, message=test_message_list, callsigns=test_callsigns
    )

    assert processor.qso_dict[(test_callsigns[0], test_callsigns[1])] == expected_result


def test_handle_cq():
    test_data_packet = Packet(
        snr=-20,
        delta_time=0.5,
        frequency_offset=950,
        message='CQ K9XYZ EN87',
        program='WSJT-X',
        schema=2,
        packet_type=2,
        band='20m',
        frequency=14.07495,
    )

    expected_result = [
        CQ(
            message='CQ K9XYZ EN87',
            translated_message='Station K9XYZ is calling for any response from grid EN87.',
            caller='K9XYZ',
            packet=test_data_packet,
        )
    ]
    processor = MessageProcessor()
    processor.handle_cq(packet=test_data_packet)

    assert processor.cqs == expected_result


def test_handle_longer_message():
    test_data_packet = Packet(
        snr=-20,
        delta_time=0.5,
        frequency_offset=950,
        message='CQ POTA N0PAT EM18',
        program='WSJT-X',
        schema=2,
        packet_type=2,
        frequency=14.07495,
        band='20m',
    )
    test_message = ['CQ', 'POTA', 'N0PAT', 'EM18']
    expected_result = [
        CQ(
            message='CQ POTA N0PAT EM18',
            translated_message='Parks on the Air participant N0PAT is calling from grid EM18.',
            caller='N0PAT',
            packet=test_data_packet,
        )
    ]

    processor = MessageProcessor()
    processor.handle_longer_msg(packet=test_data_packet, message=test_message)

    assert processor.cqs == expected_result


# MESSAGE SORTING ALGO


def test_message_sort():
    test_data_packet1 = Packet(
        snr=-20,
        delta_time=0.5,
        frequency_offset=950,
        message='W1AW K9XYZ EN87',
        program='WSJT-X',
        schema=2,
        packet_type=2,
        frequency=14.07495,
        band='20m',
    )
    test_callsigns1 = sorted(['W1AW', 'K9XYZ'])
    test_message_list = ['W1AW', 'K9XYZ', 'EN87']
    expected_result1 = [
        MessageTurn(
            turn=0,
            message='W1AW K9XYZ EN87',
            translated_message=f'{test_message_list[1]} '
            f'sends a grid square location of {test_message_list[-1]} to {test_message_list[0]}.',
            packet=test_data_packet1,
            type='Grid Square Report',
        )
    ]

    processor = MessageProcessor()
    processor.qso_dict[(test_callsigns1[0], test_callsigns1[1])] = []

    processor.sort_message(packet=test_data_packet1, callsigns=test_callsigns1, new_convo=False)

    assert processor.qso_dict[(test_callsigns1[0], test_callsigns1[1])] == expected_result1

    test_data_packet2 = Packet(
        snr=-20,
        delta_time=0.5,
        frequency_offset=950,
        message='W1AW K9XYZ -10',
        program='WSJT-X',
        schema=2,
        packet_type=2,
        band='20m',
        frequency=14.07495,
    )
    test_message_list2 = ['W1AW', 'K9XYZ', '-10']
    test_callsigns2 = sorted(['W1AW', 'K9XYZ'])

    processor.qso_dict[(test_callsigns2[0], test_callsigns2[1])] = []

    processor.sort_message(packet=test_data_packet2, callsigns=test_callsigns2, new_convo=False)

    expected_result2 = [
        MessageTurn(
            turn=0,
            message='W1AW K9XYZ -10',
            translated_message=f'{test_message_list2[1]} '
            f'sends a signal report of {test_message_list2[2]} to {test_message_list2[0]}.',
            packet=test_data_packet2,
            type='Signal Report',
        )
    ]

    assert processor.qso_dict[(test_callsigns2[0], test_callsigns2[1])] == expected_result2


def test_square_resolve():
    test_data = ['DN50', 'FK68', 'KN22', 'CN89', 'EM62', 'EN58']
    expected_result = [
        {
            'Grid Square': 'DN50',
            'Latitude': '40.5',
            'Longitude': '-109.0',
            'Map URL': 'https://www.google.com/maps?q=40.5,-109.0',
        },
        {
            'Grid Square': 'FK68',
            'Latitude': '18.5',
            'Longitude': '-67.0',
            'Map URL': 'https://www.google.com/maps?q=18.5,-67.0',
        },
        {
            'Grid Square': 'KN22',
            'Latitude': '42.5',
            'Longitude': '25.0',
            'Map URL': 'https://www.google.com/maps?q=42.5,25.0',
        },
        {
            'Grid Square': 'CN89',
            'Latitude': '49.5',
            'Longitude': '-123.0',
            'Map URL': 'https://www.google.com/maps?q=49.5,-123.0',
        },
        {
            'Grid Square': 'EM62',
            'Latitude': '32.5',
            'Longitude': '-87.0',
            'Map URL': 'https://www.google.com/maps?q=32.5,-87.0',
        },
        {
            'Grid Square': 'EN58',
            'Latitude': '48.5',
            'Longitude': '-89.0',
            'Map URL': 'https://www.google.com/maps?q=48.5,-89.0',
        },
    ]

    result_list = []
    p = MessageProcessor()
    for i in test_data:
        result_list.append(p.resolve_grid_square(i))
    assert result_list == expected_result

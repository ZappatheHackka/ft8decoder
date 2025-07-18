from ft8decoder.processor import MessageProcessor

def test_is_grid_square():
    false_data = ['W1AW', 'K9XYZ', 'RR73']
    true_data = ['W1AW', 'K9XYZ', 'EL09']

    processor = MessageProcessor()

    assert processor.is_grid_square(false_data) is False
    assert processor.is_grid_square(true_data) is True

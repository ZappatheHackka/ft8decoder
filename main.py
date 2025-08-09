from ft8decoder import WsjtxParser, MessageProcessor
import time

# Get HOST and PORT from WSJT-X settings
HOST = '127.0.0.1'
PORT = 2237

# Initialize parser with your desired dial frequency,
parser = WsjtxParser(dial_frequency=14.074000)

# Initialize processor
processor = MessageProcessor()

# Pass the HOST, PORT, and processor into the parser and begin listening
parser.start_listening(HOST, PORT, processor)

# Start the processor
processor.start()

# Sleep for however long you want to compile data for
time.sleep(180)

# Access the parsed and processed data
print("All captured packets:", processor.master_data)
processor.to_map('map1', all_cqs=True)
processor.to_json(filename="ft8_data")
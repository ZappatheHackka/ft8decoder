from classes import WsjtxParser, MessageProcessor
import time

HOST = '127.0.0.1'
PORT = 2237

parser = WsjtxParser()
processor = MessageProcessor()
parser.start_listening(HOST, PORT, processor)
processor.order(seconds=3)

time.sleep(80)
print("All captured packets:", processor.master_data)
# processor.to_json()
processor.comms_to_json()
processor.cqs_to_json()
processor.misc_to_json()
exit()
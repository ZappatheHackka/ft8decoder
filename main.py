from classes import WsjtxParser, MessageProcessor
import time

HOST = '127.0.0.1'
PORT = 2237

parser = WsjtxParser()
processor = MessageProcessor()
parser.start_listening(HOST, PORT, processor)
processor.order(seconds=3)

time.sleep(60)
print("Convo Dict:", processor.convo_dict)
processor.to_json()
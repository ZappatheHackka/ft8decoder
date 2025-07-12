from classes import WsjtxParser, MessageProcessor

HOST = '127.0.0.1'
PORT = 2237

parser = WsjtxParser()
processor = MessageProcessor()
parser.start_listening(HOST, PORT, processor)

print(processor.convo_dict)


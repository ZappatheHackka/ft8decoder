from classes import WsjtxParser, Packet

HOST = '127.0.0.1'
PORT = 2237

parser = WsjtxParser()

parser.parse(HOST, PORT)




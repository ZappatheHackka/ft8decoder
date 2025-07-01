from classes import WsjtxParser

HOST = '127.0.0.1'
PORT = 2237

parser = WsjtxParser()

parser.start_listening(HOST, PORT)


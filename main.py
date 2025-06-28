from classes import WsjtxParser, data_motherload

HOST = '127.0.0.1'
PORT = 2237

parser = WsjtxParser()

parser.start(HOST, PORT)

while True:
    print(data_motherload)
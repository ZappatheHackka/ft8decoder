from classes import WsjtxParser, data_motherload

HOST = '127.0.0.1'
PORT = 2237

parser = WsjtxParser()

parser.listen(HOST, PORT, seconds=15)

while True:
    print(data_motherload)
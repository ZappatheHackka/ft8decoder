import argparse

def main():
    parser = argparse.ArgumentParser(
        prog="FT8Decoder",
        description="CLI tool for parsing and decoding FT8 messages from WSJT-X packets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    listen_parser = subparsers.add_parser("listen", help="Listen to FT8 packets")
    listen_parser.add_argument('--host', default='127.0.0.1', type="str", help='Host to bind to.')
    listen_parser.add_argument('--port', default=2237, type=int, help='Port to bind to.')

    process_parser = subparsers.add_parser("process packets", help="Process FT8 packets")
    process_parser.add_argument('--interval', default=5, type=int, help='Interval in seconds between.')



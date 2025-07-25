import argparse
from ft8decoder import *
import time

def main():
    parser = argparse.ArgumentParser(
        prog="FT8Decoder",
        description="CLI tool for parsing and decoding FT8 messages from WSJT-X packets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    listen_parser = subparsers.add_parser("listen", help="Listen and process FT8 packets")
    listen_parser.add_argument('--host', default='127.0.0.1', type=str, required=True, help='Host to bind to.')
    listen_parser.add_argument('--port', default=2237, type=int, required=True, help='Port to bind to.')
    listen_parser.add_argument('--dial', default=14.074000, type=float, required=True, help='WSJT-X dial frequency.')
    listen_parser.add_argument('--interval', default=5, type=int, required=True, help='Interval in seconds between.')
    listen_parser.add_argument('--duration', default=120, type=int, required=True, help='Listening duration before data exporting.')
    listen_parser.add_argument('--export', default='ft8_data.json', type=str, required=True, help='File containing all parsed & ordered FT8 data.')

    args = parser.parse_args()

    if args.command == "listen":
        parser = WsjtxParser(dial_frequency=args.dial)
        processor = MessageProcessor()

        parser.start_listening(host=args.host, port=args.port, processor=processor)
        processor.order(seconds=args.interval)

        time.sleep(args.duration)
        print(f"Listened for {args.duration} seconds.\nAll captured packets:\n{processor.master_data}")
        if args.export:
            print(f"Exporting data to {args.export}.")
            processor.to_json(filename=args.export)


if __name__ == "__main__":
    main()

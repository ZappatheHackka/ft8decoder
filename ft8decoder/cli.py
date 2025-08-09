import argparse
from ft8decoder import *
import time

def main():
    """
        Main entry point for the FT8 Decoder command-line interface.

        Provides a comprehensive CLI for capturing, processing, and exporting FT8
        messages from WSJT-X. Supports real-time packet capture with configurable
        processing intervals and multiple export formats including JSON data files
        and interactive world maps.

        Command Structure:
            ft8decoder listen [options]

        Key Features:
            - Real-time FT8 packet capture from WSJT-X UDP stream
            - Intelligent message classification (QSOs, CQs, misc communications)
            - Multiple export formats (JSON, interactive maps)
            - Configurable processing intervals and capture duration
            - Automatic band detection and frequency calculation

        Example Usage:
            $ python main.py listen --dial 14.074 --duration 300 --export-all session1
            $ python main.py listen --port 2237 --interval 10 --to-map activity_map
            $ python main.py listen --host 192.168.1.100 --export-comms qsos_only
    """
    parser = argparse.ArgumentParser(
        prog="FT8Decoder",
        description="CLI tool for parsing and decoding FT8 messages from WSJT-X packets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    listen_parser = subparsers.add_parser("listen", help="Listen and process FT8 packets")
    listen_parser.add_argument('--host', default='127.0.0.1', type=str, help='Host to bind to.')
    listen_parser.add_argument('--port', default=2237, type=int, help='Port to bind to.')
    listen_parser.add_argument('--dial', default=14.074000, type=float, help='WSJT-X dial frequency.')
    listen_parser.add_argument('--interval', default=5, type=int, help='Interval in seconds between.')
    listen_parser.add_argument('--duration', default=120, type=int, help='Listening duration before data exporting.')
    listen_parser.add_argument('--export-all', type=str, help='Export all captured FT8 data to a json file.')
    listen_parser.add_argument('--export-comms', type=str, help='Export only FT8 convo data to a json file.')
    listen_parser.add_argument('--export-cqs', type=str, help='Export only unanswered CQ data to a json file.')
    listen_parser.add_argument('--export-misc', type=str, help='Export only miscellaneous data to a json file.')
    listen_parser.add_argument('--to-map', type=str, help='Create a dynamic world map that plots all QSOs and CQs with grid squares.')


    args = parser.parse_args()

    if args.command == "listen":
        parser = WsjtxParser(dial_frequency=args.dial)
        processor = MessageProcessor()

        parser.start_listening(host=args.host, port=args.port, processor=processor)
        processor.start(seconds=args.interval)

        time.sleep(args.duration)
        print(f"Listened for {args.duration} seconds.\nAll captured packets:\n{processor.master_data}")
        if args.export_all:
            print(f"Exporting all FT8 data to {args.export_all}.")
            processor.to_json(filename=args.export_all)
        elif args.export_comms:
            print(f"Exporting all FT8 conversation data to {args.export_comms}.")
            processor.comms_to_json(filename=args.export_comms)
        elif args.export_cqs:
            print(f"Exporting all unanswered FT8 CQ data to {args.export_cqs}.")
            processor.cqs_to_json(filename=args.export_cqs)
        elif args.export_misc:
            print(f"Exporting all miscellaneous data to {args.export_misc}.")
            processor.misc_to_json(args.export_misc)
        if args.to_map:
            print(f"Creating dynamic world map titled {args.to_map}.html.")
            processor.to_map(filename=args.to_map)


if __name__ == "__main__":
    main()

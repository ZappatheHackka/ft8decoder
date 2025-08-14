# ft8decoder

 [![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/ZappatheHackka/ft8decoder)

`ft8decoder` is a Python-based tool for decoding, translating, and organizing FT8 digital radio communications in real-time. It listens for UDP packets broadcast by WSJT-X, parses the cryptic messages into human-readable text, sorts them into distinct conversations (QSOs), and provides options to export the captured data into structured JSON files or visualize them on a world map.

This tool is perfect for amateur radio enthusiasts who want to log, understand, and analyze FT8 communications happening on the bands.

## Key Features

- **Live Packet Listening**: Connects directly to the WSJT-X UDP stream to process radio traffic as it happens.
- **Message Parsing & Translation**: Decodes standard FT8 messages, including CQ calls, grid squares, signal reports, and sign-offs, translating them into plain English.
- **Conversation Tracking**: Intelligently groups individual transmissions into complete conversations (QSOs) from the initial CQ call to the final "73".
- **Data Exporting**: Saves all captured communications, including completed QSOs, unanswered CQs, and miscellaneous messages, into a well-structured JSON file for logging or further analysis.
- **Geographic Visualization**: Generates a dynamic HTML map using Folium, plotting the locations of operators (via Maidenhead grid squares) and drawing lines to represent their QSOs.

## How It Works

The application is built around two core components:

1.  **`WsjtxParser`**: This class is responsible for the low-level networking. It binds to the specified UDP port that WSJT-X uses to broadcast its data. It listens for incoming packets, validates them, and unpacks the binary data into a structured `Packet` object containing details like SNR, frequency, time delta, and the raw message content.

2.  **`MessageProcessor`**: This class handles the logic of understanding the parsed packets. It ingests a stream of `Packet` objects and organizes them:
    -   **CQ Calls**: Identifies and logs general "CQ" calls.
    -   **QSO Assembly**: When a station responds to a CQ, a new conversation thread is started. The processor tracks each turn of the conversation, from grid square exchange to signal reports and final acknowledgments (`RR73`, `73`).
    -   **Translation**: Each message type is translated into a descriptive sentence (e.g., `N5YHF WB7SRC R+05` becomes "WB7SRC says Roger and reports a signal report of +05 to N5YHF.").
    -   **Grid Square Caching**: It caches the grid square of each station heard to resolve their location for mapping, even if they don't repeat it in every transmission.

## Installation

Ensure you have Python 3.8+ and a running instance of WSJT-X.

1.  **Install from PyPI (recommended):**
    ```bash
    pip install ft8decoder
    ```
    This will install the package and its dependencies (`maidenhead` and `folium`).

2.  **Install from source:**
    ```bash
    git clone https://github.com/ZappatheHackka/ft8decoder.git
    cd ft8decoder
    pip install .
    ```
    For development, install Poetry and run:
    ```bash
    pip install poetry
    poetry install
    ```

3.  **Configure WSJT-X:**
    In WSJT-X, go to `File` > `Settings` > `Reporting`. Ensure the "UDP Server" is enabled and set to `127.0.0.1:2237`, which are the defaults for this tool.

### Python API Usage

You can use the core classes directly in your Python code in the following manner:

```python
from ft8decoder import WsjtxParser, MessageProcessor
import time

# Get HOST and PORT from WSJT-X settings
HOST = '127.0.0.1'
PORT = 2237

# Initialize parser with your desired dial frequency
parser = WsjtxParser(dial_frequency=14.074000)

# Initialize processor
processor = MessageProcessor()

# Pass the HOST, PORT, and processor into the parser and begin listening
parser.start_listening(HOST, PORT, processor)

# Start the processor
processor.start()

# Sleep for however long you want to compile data for
time.sleep(180)

# Access the parsed and processed data
print("All captured packets:", processor.master_data)
processor.to_map('map1', all_cqs=True)
processor.to_json(filename="ft8_data")
```

## CLI Usage

The application also includes an easy command-line interface. The primary command is `ft8decoder listen`.

### Basic CLI Usage

To start listening to packets, run the following command. It will listen for 2 minutes (120 seconds) and then print the captured data.

```bash
ft8decoder listen
```

### Command-Line Arguments

You can customize the behavior with the following arguments:

-   `--host`: The host IP to bind to (default: `127.0.0.1`).
-   `--port`: The UDP port to listen on (default: `2237`).
-   `--dial`: Your radio's dial frequency in MHz for accurate frequency calculation (default: `14.074000`).
-   `--interval`: The interval in seconds for processing collected packets (default: `5`).
-   `--duration`: Total listening duration in seconds before the program exits and exports data (default: `120`).
-   `--export-all <filename>`: Export all captured data (QSOs, CQs, Misc.) to a specified JSON file.
-   `--export-comms <filename>`: Export only conversation data to a JSON file.
-   `--export-cqs <filename>`: Export only unanswered CQ calls to a JSON file.
-   `--export-misc <filename>`: Export only miscellaneous messages.
-   `--to-map <filename>`: Generate an interactive HTML map visualizing the QSOs and CQs.

### Example

Listen for 5 minutes, export all data to `my_log.json`, and create a map named `activity_map.html`:

```bash
ft8decoder listen --duration 300 --export-all my_log.json --to-map activity_map
```

After running, you will find `my_log.json` and `activity_map.html` in your directory.

### Sample Output

## JSON Data
```json
      "('KF5WCP', 'KT4KB')": [
        {
          "completed": true
        },
        {
          "turn": 1,
          "message": "CQ KT4KB EM94",
          "translated_message": "Station KT4KB is calling for any response from grid EM94.",
          "packet": {
            "snr": 1,
            "delta_time": 0.5,
            "frequency_offset": 831,
            "frequency": 14.074831,
            "band": "20m",
            "message": "CQ KT4KB EM94",
            "schema": 2,
            "program": "WSJT-X",
            "time_captured": "2025-08-08 10:17:56.951461",
            "packet_type": 2
          },
          "type": "CQ Call."
        },
        {
          "turn": 2,
          "message": "KT4KB KF5WCP EM25",
          "translated_message": "KF5WCP sends a grid square location of EM25 to KT4KB.",
          "packet": {
            "snr": -5,
            "delta_time": 0.30000001192092896,
            "frequency_offset": 710,
            "frequency": 14.07471,
            "band": "20m",
            "message": "KT4KB KF5WCP EM25",
            "schema": 2,
            "program": "WSJT-X",
            "time_captured": "2025-08-08 10:18:11.935844",
            "packet_type": 2
          },
          "type": "Grid Square Report"
        },
        {
          "turn": 3,
          "message": "KF5WCP KT4KB -16",
          "translated_message": "KT4KB sends a signal report of -16 to KF5WCP.",
          "packet": {
            "snr": 8,
            "delta_time": 0.5,
            "frequency_offset": 830,
            "frequency": 14.07483,
            "band": "20m",
            "message": "KF5WCP KT4KB -16",
            "schema": 2,
            "program": "WSJT-X",
            "time_captured": "2025-08-08 10:18:26.962332",
            "packet_type": 2
          },
          "type": "Signal Report"
        },
        {
          "turn": 4,
          "message": "KT4KB KF5WCP R-19",
          "translated_message": "KF5WCP says Roger and reports a signal report of -19 to KT4KB.",
          "packet": {
            "snr": 1,
            "delta_time": 0.30000001192092896,
            "frequency_offset": 710,
            "frequency": 14.07471,
            "band": "20m",
            "message": "KT4KB KF5WCP R-19",
            "schema": 2,
            "program": "WSJT-X",
            "time_captured": "2025-08-08 10:18:41.909084",
            "packet_type": 2
          },
          "type": "Signal Report"
        },
        {
          "turn": 5,
          "message": "KF5WCP KT4KB RR73",
          "translated_message": "KT4KB sends a Roger Roger to KF5WCP and says goodbye, concluding the connection.",
          "packet": {
            "snr": 3,
            "delta_time": 0.5,
            "frequency_offset": 831,
            "frequency": 14.074831,
            "band": "20m",
            "message": "KF5WCP KT4KB RR73",
            "schema": 2,
            "program": "WSJT-X",
            "time_captured": "2025-08-08 10:18:56.898584",
            "packet_type": 2
          },
          "type": "RR & Goodbye"
        },
        {
          "turn": 6,
          "message": "KT4KB KF5WCP 73",
          "translated_message": "KF5WCP sends their well wishes to KT4KB, concluding the connection.",
          "packet": {
            "snr": 6,
            "delta_time": 0.30000001192092896,
            "frequency_offset": 711,
            "frequency": 14.074711,
            "band": "20m",
            "message": "KT4KB KF5WCP 73",
            "schema": 2,
            "program": "WSJT-X",
            "time_captured": "2025-08-08 10:19:11.914567",
            "packet_type": 2
          },
          "type": "Goodbye"
        }
      ],
```
Full JSON file [HERE](https://github.com/ZappatheHackka/ft8decoder/blob/master/all_comms.json)

## Folium Map

[Sample QSO Map Data](https://github.com/ZappatheHackka/ft8decoder/blob/master/docs/images/map1.png)


[Sample CQ Map Data](https://github.com/ZappatheHackka/ft8decoder/blob/master/docs/images/map2.png)


## Project Structure

-   `ft8decoder/`: The main source code package.
    -   `cli.py`: Defines the command-line interface using `argparse`.
    -   `parser.py`: Contains the `WsjtxParser` for handling UDP packets.
    -   `processor.py`: Contains the `MessageProcessor` for logic, translation, and data organization.
    -   `core.py`: Core dataclasses for `Packet`, `MessageTurn`, and `CQ`.
-   `tests/`: Unit tests for the parser and processor logic.
-   `setup.py`: Package setup and dependency information.
-   `all_comms.json`: An example JSON output file containing captured data.
-   `map.html`: An example map generated by the tool.

## Documentation
For the fully comprehensive documentation, click **[HERE](https://zappathehackka.github.io/ft8decoder/)**
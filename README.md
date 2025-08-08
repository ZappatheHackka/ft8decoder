# ft8translator
[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/ZappatheHackka/ft8translator)

`ft8translator` is a Python-based tool for decoding, translating, and organizing FT8 digital radio communications in real-time. It listens for UDP packets broadcast by WSJT-X, parses the cryptic messages into human-readable text, sorts them into distinct conversations (QSOs), and provides options to export the captured data into structured JSON files or visualize them on a world map.

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

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ZappatheHackka/ft8translator.git
    cd ft8translator
    ```

2.  **Install the required dependencies:**
    The project uses `setuptools` for packaging. Install it directly using pip:
    ```bash
    pip install .
    ```
    This will also install the necessary libraries, `maidenhead` and `folium`.

3.  **Configure WSJT-X:**
    In WSJT-X, go to `File` > `Settings` > `Reporting`. Ensure the "UDP Server" is enabled and set to `127.0.0.1:2237`, which are the defaults for this tool.

## Usage

The application is run from the command line. The primary command is `ft8decoder listen`.

### Basic Usage

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
-   `--to-map <filename>`: Generate an interactive HTML map visualizing the QSOs and CQs.

### Example

Listen for 5 minutes, export all data to `my_log.json`, and create a map named `activity_map.html`:

```bash
ft8decoder listen --duration 300 --export-all my_log.json --to-map activity_map
```

After running, you will find `my_log.json` and `activity_map.html` in your directory.

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
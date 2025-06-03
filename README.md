# Python Network Utility Script with Curses TUI

This project provides a simple Text User Interface (TUI) based network utility written in Python. It allows you to either listen on a specified TCP or UDP port for incoming data or write (send) data to a remote TCP/UDP endpoint. All interactions, including setting up the connection parameters and sending messages, are handled directly within the terminal interface.

## Features

* **TUI (Text User Interface):** Interactive command-line interface using the `curses` library for a more engaging user experience.

* **TCP and UDP Support:** Supports both TCP (Transmission Control Protocol) for connection-oriented communication and UDP (User Datagram Protocol) for connectionless datagrams.

* **Listen Mode:** Act as a server to receive data on a specified IP address and port.

* **Write Mode:** Act as a client to send data to a specified IP address and port.

* **Dynamic Configuration:** All network parameters (IP, Port, Protocol, Mode, Display Format) are prompted for within the TUI at startup.

* **Real-time Display:** Shows incoming and outgoing messages in a dedicated output area.

* **Configurable Display Format:** Choose to view received data in either human-readable ASCII or detailed hexadecimal dump format.

* **Responsive Input:** Designed to allow smooth typing even while receiving concurrent data.

* **Local IP Auto-detection:** Automatically suggests your local IP address as a default for convenience.

## Requirements

* Python 3.x

* A Unix-like operating system (Linux, macOS) for native `curses` support.

## How to Run

1. **Save the script:** Save the provided Python code into a file named `network_utility_tui.py` (or any other `.py` name).

2. **Open your terminal or command prompt.**

3. **Navigate to the directory** where you saved the script.

4. **Run the script:**

```
python network_utility_tui.py
```
The TUI will start, and you will be prompted to enter the required network parameters:

* **IP address to listen on:** The IP address to bind to for listening (e.g., `127.0.0.1` for localhost, `0.0.0.0` to listen on all available interfaces).

* **Port number:** The port number to use (e.g., `8080`, `12345`).

* **Protocol:** `tcp` or `udp`.

* **Mode:** `listen` or `write`.

* **Display received data as:** `ascii` or `hex`.

## Usage Examples

Once the TUI starts, follow the prompts.

### Example 1: Listening on a TCP Port

1. Run: `python network_utility_tui.py`

2. Enter `0.0.0.0` for IP (or your local IP).

3. Enter `8080` for Port.

4. Enter `tcp` for Protocol.

5. Enter `listen` for Mode.

6. Enter `ascii` (or `hex`) for Display Format.

The utility will start listening. You can then use another tool (like `netcat`, `telnet`, or a simple client script) to send data to your machine's IP address on port 8080.

Example using `netcat` from another terminal:

```
echo "Hello from client!" | nc 127.0.0.1 8080
```
(Replace `127.0.0.1` with the IP address you entered if listening on a different interface).

### Example 2: Sending Messages via UDP

1. Run: `python network_utility_tui.py`

2. Enter `127.0.0.1` for IP (or the target IP).

3. Enter `12345` for Port.

4. Enter `udp` for Protocol.

5. Enter `write` for Mode.

6. Enter `ascii` (or `hex`) for Display Format.

The utility will connect (or prepare to send for UDP). You can then type messages at the `>>` prompt and press Enter to send them. Any received data will also be displayed.

## Troubleshooting

* **`_curses.error: addwstr() returned ERR` or `_curses.error: embedded null character`**: This error typically occurs when `curses` attempts to display a string containing a null character (`\x00`). The script now includes a `.replace('\x00', '.')` to mitigate this for ASCII display. If it persists, ensure the data you are sending does not contain unprintable characters that might cause rendering issues.

* **`curses.error: setupterm: could not find terminal`**: This means your terminal environment doesn't have `curses` properly configured. Ensure you are running in a compatible terminal (e.g., `xterm`, `gnome-terminal`, `iTerm2`). On Windows, ensure `windows-curses` is installed and you're using a compatible terminal like `cmd.exe` or PowerShell.

* **Cannot type in "write" mode**: This issue has been addressed by changing the input handling to a non-blocking character-by-character method. Ensure you are running the latest version of the script. If still unresponsive, check for very high CPU usage or other processes interfering with terminal input.

* **"Address already in use" error**: This means another process is already using the specified IP address and port. Choose a different port, or ensure no other applications are running on that port.

* **"Connection refused" error**: In `write` mode, this means the target IP/port does not have a listening server. Ensure the server application is running and accessible.

* **Exiting the TUI**: Press `Ctrl+C` at any time to gracefully exit the application.

## How it Works (Technical Overview)

The script leverages Python's `socket` module for network communication and the `curses` library for building the TUI.

* **`curses.wrapper`**: Initializes and deinitializes the `curses` environment safely.

* **Windows (`output_window`, `input_window`)**: The screen is divided into two main areas: `output_window` for displaying logs and received data, and `input_window` for user input.

* **Threading**: Network operations (listening for connections, receiving data) run in separate `threading.Thread` instances. This prevents the TUI from freezing while waiting for network events.

* **`curses_lock`**: A `threading.Lock` is used to ensure that only one thread attempts to update the `curses` screen at a time, preventing display corruption.

* **Non-blocking Input (`input_window.nodelay(True)`, `curses.noecho()`)**: For the "write" mode, user input is captured character by character in a non-blocking manner. This allows the main UI loop to remain responsive and redraw the input line as you type, even when network data is coming in.

* **Data Formatting**: Received raw bytes are either decoded to UTF-8 (with `errors='backslashreplace'` to show unprintable characters as `\xNN` escapes) for ASCII display or converted to a formatted hexadecimal string for hex dump display.

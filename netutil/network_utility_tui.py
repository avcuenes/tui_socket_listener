import socket
import argparse
import threading
import sys
import time
import curses

# --- Global Curses Variables and Lock ---
curses_lock = threading.Lock()
output_window = None
input_window = None
stdscr = None
display_format = "ascii" # Default display format

# --- Constants ---
BUFFER_SIZE = 4096

# --- Helper Functions ---

def display_message(message, level="INFO"):
    """
    Prints a formatted message to the curses output window.
    Uses a lock to ensure thread-safe updates to the curses screen.
    """
    with curses_lock:
        if output_window:
            color_pair = curses.color_pair(1)
            if level == "DATA":
                color_pair = curses.color_pair(2)
            elif level == "WARNING":
                color_pair = curses.color_pair(3)
            elif level == "ERROR" or level == "CRITICAL":
                color_pair = curses.color_pair(4)

            try:
                for line in message.splitlines():
                    output_window.addstr(f"[{level}] {line}\n", color_pair)
                output_window.scrollok(True)
                output_window.idlok(True)
                output_window.scroll(1)
                output_window.refresh()
            except curses.error:
                print(f"[{level}] {message}", file=sys.stderr)
        else:
            print(f"[{level}] {message}")

def get_local_ip():
    """
    Attempts to get the local machine's primary IP address.
    Falls back to '127.0.0.1' if unable to determine.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def format_hex_dump(data_bytes):
    """
    Formats a bytes object into a traditional hex dump string.
    Example:
    0000   f0 73 ae 00 84 61 6c 24  08 31 63 20 08 00 45 00  .s...al$.1c ..E.
    """
    lines = []
    for i in range(0, len(data_bytes), 16):
        chunk = data_bytes[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk[:8])
        if len(chunk) > 8:
            hex_part += '  ' + ' '.join(f'{b:02x}' for b in chunk[8:])
        else:
            hex_part += ' ' * (3 * (8 - len(chunk)) + 2)

        hex_part += ' ' * (3 * (16 - len(chunk)))

        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        lines.append(f'{i:04x}   {hex_part}  {ascii_part}')
    return "\n".join(lines)


# --- TCP Functions ---

def listen_tcp(ip, port):
    """
    Listens for incoming TCP connections and data.
    Displays received data in the curses output window based on display_format.
    """
    display_message(f"Starting TCP listener on {ip}:{port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((ip, port))
            sock.listen(5)
            display_message(f"TCP listener active. Waiting for connections on {ip}:{port}...")

            while True:
                conn, addr = sock.accept()
                with conn:
                    display_message(f"Accepted TCP connection from {addr[0]}:{addr[1]}")
                    try:
                        while True:
                            data = conn.recv(BUFFER_SIZE)
                            if not data:
                                display_message(f"Client {addr[0]}:{addr[1]} disconnected.")
                                break
                            
                            global display_format # Access the global variable
                            if display_format == "hex":
                                formatted_data = format_hex_dump(data)
                                display_message(f"Received from {addr[0]}:{addr[1]}:\n{formatted_data}", level="DATA")
                            else: # ascii
                                decoded_data = data.decode('utf-8', errors='backslashreplace')
                                decoded_data = decoded_data.replace('\x00', '.')
                                display_message(f"Received from {addr[0]}:{addr[1]}: '{decoded_data}'", level="DATA")

                    except ConnectionResetError:
                        display_message(f"Client {addr[0]}:{addr[1]} forcibly closed the connection.", level="WARNING")
                    except Exception as e:
                        display_message(f"Error handling TCP connection from {addr[0]}:{addr[1]}: {e}", level="ERROR")
    except OSError as e:
        if "Address already in use" in str(e):
            display_message(f"Port {port} is already in use. Please choose a different port.", level="ERROR")
        else:
            display_message(f"OS Error starting TCP listener: {e}", level="ERROR")
    except Exception as e:
        display_message(f"Error starting TCP listener: {e}", level="ERROR")

def write_tcp(ip, port):
    """
    Connects to a TCP server and sends user input received via curses.
    Also receives and displays data from the server based on display_format.
    """
    display_message(f"Attempting to connect to TCP server at {ip}:{port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, port))
            display_message(f"Successfully connected to TCP server at {ip}:{port}.")
            display_message("Enter messages to send (type 'exit' to quit):")

            def receive_tcp_data():
                try:
                    while True:
                        data = sock.recv(BUFFER_SIZE)
                        if not data:
                            display_message("Server disconnected.", level="WARNING")
                            break
                        
                        global display_format # Access the global variable
                        if display_format == "hex":
                            formatted_data = format_hex_dump(data)
                            display_message(f"Received from server:\n{formatted_data}", level="DATA")
                        else: # ascii
                            decoded_data = data.decode('utf-8', errors='backslashreplace')
                            decoded_data = decoded_data.replace('\x00', '.')
                            display_message(f"Received from server: '{decoded_data}'", level="DATA")

                except ConnectionResetError:
                    display_message("Server forcibly closed the connection.", level="WARNING")
                except OSError as e:
                    if "Bad file descriptor" not in str(e):
                        display_message(f"Error receiving TCP data: {e}", level="ERROR")
                except Exception as e:
                    display_message(f"Error in TCP receive thread: {e}", level="ERROR")
                finally:
                    display_message("TCP receive thread stopped.")

            recv_thread = threading.Thread(target=receive_tcp_data, daemon=True)
            recv_thread.start()

            current_input_line = ""
            # Set input_window to non-blocking for manual character processing
            input_window.nodelay(True) 
            curses.noecho() # Ensure curses doesn't echo characters automatically

            while True:
                try:
                    # Get character input (non-blocking)
                    ch = input_window.getch()

                    if ch != -1: # If a character was pressed
                        if ch == curses.KEY_ENTER or ch == 10: # Enter key (10 is ASCII for newline)
                            message_to_send = current_input_line.strip()
                            if message_to_send.lower() == 'exit':
                                break
                            if message_to_send:
                                sock.sendall(message_to_send.encode('utf-8'))
                                display_message(f"Sent: '{message_to_send}'", level="INFO")
                            current_input_line = "" # Clear input after sending
                        elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8: # Backspace/Delete (127 is ASCII DEL, 8 is ASCII BS)
                            current_input_line = current_input_line[:-1]
                        elif 32 <= ch <= 126: # Printable ASCII characters
                            current_input_line += chr(ch)
                        # Redraw input line after any key press
                        with curses_lock:
                            input_window.move(1, 0)
                            input_window.clrtoeol()
                            input_window.addstr(1, 0, ">> ", curses.color_pair(5))
                            input_window.addstr(current_input_line, curses.color_pair(5))
                            input_window.refresh()
                    
                    time.sleep(0.01) # Small delay to prevent busy-waiting and allow other threads to run

                except BrokenPipeError:
                    display_message("Connection lost to server (Broken Pipe).", level="ERROR")
                    break
                except curses.error:
                    # This can happen during resize or other curses-related issues.
                    # We just continue, the main UI loop will handle resize events.
                    time.sleep(0.01) # Small delay to prevent busy-waiting
                    continue
                except Exception as e:
                    display_message(f"Error sending TCP data: {e}", level="ERROR")
                    break
            
            # Re-enable echo and blocking for get_tui_input if needed after loop breaks
            curses.echo()
            input_window.nodelay(False)

    except ConnectionRefusedError:
        display_message(f"Connection refused by {ip}:{port}. Is the server running?", level="ERROR")
    except socket.timeout:
        display_message(f"Connection timed out to {ip}:{port}.", level="ERROR")
    except Exception as e:
        display_message(f"Error connecting to TCP server: {e}", level="ERROR")

# --- UDP Functions ---

def listen_udp(ip, port):
    """
    Listens for incoming UDP datagrams.
    Displays received data in the curses output window based on display_format.
    """
    display_message(f"Starting UDP listener on {ip}:{port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((ip, port))
            display_message(f"UDP listener active. Waiting for datagrams on {ip}:{port}...")

            while True:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                
                global display_format # Access the global variable
                if display_format == "hex":
                    formatted_data = format_hex_dump(data)
                    display_message(f"Received from {addr[0]}:{addr[1]}:\n{formatted_data}", level="DATA")
                else: # ascii
                    decoded_data = data.decode('utf-8', errors='backslashreplace')
                    decoded_data = decoded_data.replace('\x00', '.')
                    display_message(f"Received from {addr[0]}:{addr[1]}: '{decoded_data}'", level="DATA")

    except OSError as e:
        if "Address already in use" in str(e):
            display_message(f"Port {port} is already in use. Please choose a different port.", level="ERROR")
        else:
            display_message(f"OS Error starting UDP listener: {e}", level="ERROR")
    except Exception as e:
        display_message(f"Error starting UDP listener: {e}", level="ERROR")

def write_udp(ip, port):
    """
    Sends UDP datagrams to a specified address and port using curses input.
    """
    display_message(f"Preparing to send UDP datagrams to {ip}:{port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            display_message("Enter messages to send (type 'exit' to quit):")
            current_input_line = ""
            # Set input_window to non-blocking for manual character processing
            input_window.nodelay(True)
            curses.noecho() # Ensure curses doesn't echo characters automatically

            while True:
                try:
                    ch = input_window.getch()

                    if ch != -1: # If a character was pressed
                        if ch == curses.KEY_ENTER or ch == 10: # Enter key
                            message_to_send = current_input_line.strip()
                            if message_to_send.lower() == 'exit':
                                break
                            if message_to_send:
                                sock.sendto(message_to_send.encode('utf-8'), (ip, port))
                                display_message(f"Sent: '{message_to_send}'", level="INFO")
                            current_input_line = "" # Clear input after sending
                        elif ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8: # Backspace/Delete
                            current_input_line = current_input_line[:-1]
                        elif 32 <= ch <= 126: # Printable ASCII characters
                            current_input_line += chr(ch)
                        # Redraw input line after any key press
                        with curses_lock:
                            input_window.move(1, 0)
                            input_window.clrtoeol()
                            input_window.addstr(1, 0, ">> ", curses.color_pair(5))
                            input_window.addstr(current_input_line, curses.color_pair(5))
                            input_window.refresh()
                    
                    time.sleep(0.01) # Small delay to prevent busy-waiting

                except curses.error:
                    time.sleep(0.01)
                    continue
                except Exception as e:
                    display_message(f"Error sending UDP data: {e}", level="ERROR")
                    break
            
            # Re-enable echo and blocking for get_tui_input if needed after loop breaks
            curses.echo()
            input_window.nodelay(False)

    except Exception as e:
        display_message(f"Error setting up UDP sender: {e}", level="ERROR")

# --- Curses UI Initialization and Main Loop ---

def get_tui_input(prompt_message, validation_func=None, default_value=""):
    """Helper function to get validated input from the curses input window."""
    while True:
        with curses_lock:
            input_window.clear()
            input_window.addstr(0, 0, prompt_message, curses.color_pair(5))
            input_window.addstr(1, 0, f">> {default_value}", curses.color_pair(5))
            input_window.move(1, 3 + len(default_value))
            input_window.refresh()

        try:
            curses.echo()
            user_input_bytes = input_window.getstr(1, 3, 200)
            curses.noecho()
            user_input = user_input_bytes.decode('utf-8', errors='ignore').strip()

            if not user_input and default_value:
                user_input = default_value

            if validation_func:
                if validation_func(user_input):
                    return user_input
                else:
                    display_message(f"Invalid input: '{user_input}'. Please try again.", level="ERROR")
            else:
                return user_input
        except curses.error:
            time.sleep(0.1)
        except Exception as e:
            display_message(f"Error getting input: {e}", level="ERROR")
            time.sleep(1)

def main_curses(stdscr_obj):
    """
    Initializes the curses TUI and manages the main UI loop.
    This function is wrapped by curses.wrapper to handle setup and teardown.
    """
    global stdscr, output_window, input_window, display_format
    stdscr = stdscr_obj
    stdscr.clear()
    stdscr.refresh()

    # Set up colors for messages
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)

    # Calculate window sizes based on terminal dimensions
    height, width = stdscr.getmaxyx()
    input_height = 3
    output_height = height - input_height

    # Create curses windows
    output_window = curses.newwin(output_height, width, 0, 0)
    input_window = curses.newwin(input_height, width, output_height, 0)

    # Configure output window for scrolling
    output_window.scrollok(True)
    output_window.idlok(True)

    # Display initial application info
    output_window.addstr(f"--- Network Utility Started ---\n", curses.A_BOLD)
    output_window.addstr(f"Please provide the network parameters.\n\n")
    output_window.refresh()

    # --- Get parameters from user via TUI ---
    current_ip = get_local_ip()

    

    port = int(get_tui_input("Enter Port number (e.g., 8080, 12345):",
                             lambda x: x.isdigit() and 1 <= int(x) <= 65535))
    ip_address = get_tui_input(f"Enter IP address to listen on (e.g., 127.0.0.1, 0.0.0.0) [Default: {current_ip}]:",
                               lambda x: True,
                               default_value=current_ip)

    protocol = get_tui_input("Enter Protocol (tcp or udp):",
                             lambda x: x.lower() in ['tcp', 'udp']).lower()

    mode = get_tui_input("Enter Mode (listen or write):",
                         lambda x: x.lower() in ['listen', 'write']).lower()

    display_format = get_tui_input("Display received data as (ascii or hex) [Default: ascii]:",
                                   lambda x: x.lower() in ['ascii', 'hex'],
                                   default_value="ascii").lower()


    # Re-draw initial info with collected parameters
    output_window.clear()
    output_window.addstr(f"--- Network Utility Started ---\n", curses.A_BOLD)
    output_window.addstr(f"IP: {ip_address}\n")
    output_window.addstr(f"Port: {port}\n")
    output_window.addstr(f"Protocol: {protocol.upper()}\n")
    output_window.addstr(f"Mode: {mode.capitalize()}\n")
    output_window.addstr(f"Display Format: {display_format.upper()}\n")
    output_window.addstr(f"-------------------------------\n\n")
    output_window.refresh()

    # Start the network operation (listen or write) in a separate thread
    network_thread = None
    if protocol == 'tcp':
        if mode == 'listen':
            network_thread = threading.Thread(target=listen_tcp, args=(ip_address, port), daemon=True)
        else: # mode == 'write'
            network_thread = threading.Thread(target=write_tcp, args=(ip_address, port), daemon=True)
    elif protocol == 'udp':
        if mode == 'listen':
            network_thread = threading.Thread(target=listen_udp, args=(ip_address, port), daemon=True)
        else: # mode == 'write'
            network_thread = threading.Thread(target=write_udp, args=(ip_address, port), daemon=True)

    if network_thread:
        network_thread.start()

    # Main UI loop to handle terminal events (like resize) and keep the TUI alive
    display_message("Press Ctrl+C to exit.", level="INFO")
    stdscr.nodelay(True)
    while True:
        try:
            ch = stdscr.getch()
            if ch == curses.KEY_RESIZE:
                height, width = stdscr.getmaxyx()
                output_height = height - input_height
                with curses_lock:
                    output_window.resize(output_height, width)
                    input_window.resize(input_height, width)
                    input_window.mvwin(output_height, 0)
                    input_window.clear()
                    input_window.addstr(0, 0, "Enter message (Ctrl+C to quit): ", curses.color_pair(5))
                    input_window.addstr(1, 0, ">> ", curses.color_pair(5))
                    input_window.refresh() # Refresh input window after resize and redraw
                display_message("Window resized.", level="INFO")
            elif ch == 3: # ASCII value for Ctrl+C
                break
            time.sleep(0.05)
        except curses.error:
            pass
        except KeyboardInterrupt:
            break

    display_message("Shutting down network utility...", level="INFO")
    time.sleep(0.5)
    display_message("--- Network Utility Stopped ---", level="INFO")

# --- Main Program Entry Point ---

def main():
    """
    Initiates the curses TUI. Command-line arguments are no longer used for network params.
    """
    try:
        curses.wrapper(main_curses)
    except Exception as e:
        print(f"\nAn error occurred with curses: {e}", file=sys.stderr)
        print("Please ensure your terminal supports curses, or install 'windows-curses' on Windows if applicable.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

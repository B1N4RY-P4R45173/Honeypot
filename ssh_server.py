import paramiko
import socket
import threading
import logging
import os
import sys
# from paramiko.py3compat import u


# Constants
PORT = 2200
USERNAME = 'admin'
PASSWORD = 'password'
PRIVATE_KEY_PATH = 'server_key'
LOG_FILE = 'ssh_server.log'

# Set up logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SSHServer(paramiko.ServerInterface):
    def __init__(self, username, password):
        self.event = threading.Event()
        self.username = username
        self.password = password
        self.authenticated = False

    def check_channel_request(self, kind, channel):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.REJECT

    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            self.authenticated = True
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True

def decode_unicode_or_bytes(s, encoding='utf8'):
    """ decodes bytes or unicode to unicode"""
    if isinstance(s, str):
        return s
    elif isinstance(s, bytes):
        return s.decode(encoding)
    raise TypeError("{!r} is not unicode or byte".format(s))


def interactive_shell(chan):
    if has_termios:
        posix_shell(chan)
    else:
        windows_shell(chan)

def posix_shell(chan):
    import select
    import termios
    import tty

    oldtty = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        chan.settimeout(0.0)

        while True:
            r, w, e = select.select([chan, sys.stdin], [], [])
            if chan in r:
                try:
                    x = decode_unicode_or_bytes(chan.recv(1024))
                    if len(x) == 0:
                        sys.stdout.write("\r\n*** EOF\r\n")
                        break
                    sys.stdout.write(x)
                    sys.stdout.flush()
                except socket.timeout:
                    pass
            if sys.stdin in r:
                x = sys.stdin.read(1)
                if len(x) == 0:
                    break
                chan.send(x)

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

def windows_shell(chan):
    import threading

    sys.stdout.write(
        "Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n"
    )

    def writeall(sock):
        while True:
            data = sock.recv(256)
            if not data:
                sys.stdout.write("\r\n*** EOF ***\r\n\r\n")
                sys.stdout.flush()
                break
            sys.stdout.write(data.decode())  # Decode bytes to string
            sys.stdout.flush()

    writer = threading.Thread(target=writeall, args=(chan,))
    writer.start()

    try:
        while True:
            d = sys.stdin.read(1)
            if not d:
                break
            chan.send(d.encode())  # Encode string to bytes
    except EOFError:
        pass


# Check if the system has termios module (Unix-like) or not (Windows)
try:
    import termios
    import tty
    has_termios = True
except ImportError:
    has_termios = False

def handle_connection(client_sock):
    try:
        transport = paramiko.Transport(client_sock)
        server_key = paramiko.RSAKey(filename="server_key")
        transport.add_server_key(server_key)
        
        ssh_server = SSHServer(username="admin", password="password")
        
        transport.start_server(server=ssh_server)
        
        ssh_server.event.wait(10)
        
        if not ssh_server.authenticated:
            raise Exception("Authentication failed.")
        
        channel = transport.accept(20)
        if channel is None:
            raise Exception("No channel.")
        
        channel.send("Welcome to the SSH server! Type 'exit' to disconnect.\r\n")
        
        interactive_shell(channel)
                
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        transport.close()
        client_sock.close()

def main():
    # Create a new socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Allow the socket to be reused
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind the socket to a port
    server_sock.bind(("", PORT))
    
    # Listen for incoming connections
    server_sock.listen(5)

    logging.info(f"Server is listening on port {PORT}")
    
    while True:
        # Accept an incoming connection
        client_sock, client_addr = server_sock.accept()
        
        logging.info(f"Client connected from: {client_addr}")
        
        # Create a new thread to handle the connection
        t = threading.Thread(target=handle_connection, args=(client_sock,))
        t.start()

if __name__ == "__main__":
    main()

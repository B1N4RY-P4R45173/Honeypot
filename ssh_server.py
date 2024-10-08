import paramiko
import socket
import threading
import logging
import os
import subprocess

# Constants
PORT = 2200
USERNAME = 'admin'
PASSWORD = 'password'
PRIVATE_KEY_PATH = 'server_key'
LOG_FILE = 'ssh_server.log'
CHROOT_DIR = '/var/chroot/ssh'  # Adjust to your chroot directory

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
            logging.info(f"User {username} authenticated successfully")
            return paramiko.AUTH_SUCCESSFUL
        logging.info(f"Authentication failed for user {username}")
        return paramiko.AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

def interactive_shell(chan):
    chan.send("Welcome to the SSH honeypot! Type 'exit' to disconnect.\r\n$ ")

    while True:
        command = ""
        while True:
            data = chan.recv(1).decode('utf-8')
            if data == '\r':  # Enter key
                break
            elif data == '\x08' or data == '\x7f':  # Backspace key
                if command:
                    command = command[:-1]
                    chan.send('\r\n' + ' ' * len(command) + '\r' + '$ ' + command)
            else:
                command += data
                chan.send(data)
        
        chan.send('\r\n')
        
        if command.lower() == 'exit':
            chan.send("Goodbye!\r\n")
            logging.info("User exited")
            break
        if command:
            logging.info(f"User executed command: {command}")
            try:
                # Execute command in chroot environment
                proc = subprocess.Popen(
                    ["chroot", CHROOT_DIR, "bash", "-c", command],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                stdout, stderr = proc.communicate()
                
                # Send output and error to channel
                for line in stdout.splitlines():
                    chan.send(line + '\r\n')
                for line in stderr.splitlines():
                    chan.send("Error: " + line + '\r\n')
                chan.send('\r\n')  # Send an extra newline after the output
            except Exception as e:
                chan.send(f"Error: {str(e)}\r\n".encode('utf-8'))
                logging.error(f"Error executing command: {command} - {str(e)}")
        chan.send("$ ")

def handle_connection(client_sock):
    try:
        transport = paramiko.Transport(client_sock)
        server_key = paramiko.RSAKey(filename=PRIVATE_KEY_PATH)
        transport.add_server_key(server_key)
        
        ssh_server = SSHServer(username=USERNAME, password=PASSWORD)
        
        transport.start_server(server=ssh_server)
        
        ssh_server.event.wait(10)
        
        if not ssh_server.authenticated:
            raise Exception("Authentication failed.")
        
        channel = transport.accept(20)
        if channel is None:
            raise Exception("No channel.")
        
        interactive_shell(channel)
                
    except Exception as e:
        logging.error(f"Error: {str(e)}")
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

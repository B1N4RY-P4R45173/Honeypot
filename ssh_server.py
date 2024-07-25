#!/usr/bin/env python

# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA.

import paramiko
import socket
import threading
import logging
import os

PORT = 2200
USERNAME = 'admin'
PASSWORD = 'password'
PRIVATE_KEY_PATH = 'server_key'
LOG_FILE = 'ssh_server.log'

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

    # def check_channel_shell_request(self, channel):
    #     if self.authenticated:
    #         return paramiko.OPEN_SUCCEEDED
    #     return paramiko.REJECT

    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            self.authenticated = True
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    # def check_auth_publickey(self, username, key):
    #     return paramiko.AUTH_FAILED
    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True


def handle_connection(client_sock):
    try:
        transport = paramiko.Transport(client_sock)
        server_key = paramiko.RSAKey.from_private_key_file(PRIVATE_KEY_PATH)
        transport.add_server_key(server_key)
        
        ssh_server = SSHServer(USERNAME, PASSWORD)
        transport.start_server(server=ssh_server)

        logging.info('SSH server started successfully')

        while True:
            channel = transport.accept(20)
            if channel is None:
                continue

            logging.info(f'Connection established with {channel.getpeername()}')
            channel.send('Welcome to the SSH server! Type "exit" to disconnect.\n')

            while True:
                channel.send(b'> ')
                command = channel.recv(1024).decode().strip()
                if command.lower() == 'exit':
                    channel.send('Exiting...\n')
                    break
                output = os.popen(command).read()
                channel.send(output.encode())

    except Exception as e:
        logging.error(f'Error handling connection: {e}')
    finally:
        transport.close()
        logging.info('Connection closed')

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("", PORT))
    server_sock.listen(5)

    logging.info(f"Server is listening on port {PORT}")
    while True:
        client_sock, client_addr = server_sock.accept()
        logging.info(f"Client connected from: {client_addr}")
        t = threading.Thread(target=handle_connection, args=(client_sock,))
        t.start()

if __name__ == "__main__":
    main()

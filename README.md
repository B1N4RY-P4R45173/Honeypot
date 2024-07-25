# Python SSH Honeypot

This project implements a basic SSH honeypot in Python using the `paramiko` library. The honeypot accepts SSH connections, authenticates users, and allows them to execute commands on the server, logging all activity for monitoring and analysis.

## Features

- SSH connection using RSA key-based authentication
- Password authentication
- Command execution with output returned to the client
- Logging of all commands executed by the user

## Requirements

- Python 3.6 or higher
- `paramiko` library

## Setup

### 1. Install Dependencies

First, install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

### 2. Generate Server Key

Generate an RSA key pair for the server:

```bash
ssh-keygen -t rsa -b 2048 -f server_key
```

This will create two files: server_key (private key) and server_key.pub (public key).

### 3. Run the SSH Honeypot
Run the SSH honeypot script:

```bash
python ssh_honeypot.py
```

### 4. Connect to the SSH Honeypot
Use an SSH client to connect to the honeypot:

```bash
ssh admin@localhost -p 2200
```

The default username is `admin` and the password is `password`.

# Logging
All commands executed by the user are logged in honeypot.log for monitoring and analysis.

# Troubleshooting
Ensure the paramiko library is installed.

Verify that the server key files are generated and available in the script's directory.

Check that the honeypot is running and listening on the correct port.

# Known Issues
-> Problems/ Issues handling commands and setting up PTY. 

# License
This project is licensed under the MIT License.

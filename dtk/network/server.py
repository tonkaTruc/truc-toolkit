import logging
import socket


class SimpleServer:

    def __init__(self, host, port):
        self.log = logging.getLogger("__name__")
        self.host = host
        self.port = int(port)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.s.bind((self.host, self.port))
        except socket.error:
            self.log.error(f"Could not bind {self.host}:{self.port}")
            raise

        self.log.info(f"Successfully bound {self.host}:{self.port}")

    def serve(self, number_of_connections=1, timeout=60):
        self.s.listen(number_of_connections)
        self.s.settimeout(timeout)
        self.log.info(f"Socket is listening on {self.host}:{self.port}")

        conn, addr = self.s.accept()
        self.log.info(f"[!!!] Connection from {addr[0]}:{addr[1]}")

        try:
            while True:
                data = conn.recv(1024)
                reply = b". " + data
                if not data:
                    break
                conn.sendall(reply)
                conn.close()
        except socket.timeout:
            self.log.error("Nothing received within timeout")

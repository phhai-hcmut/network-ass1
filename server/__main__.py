import logging
import sys

from .rtsp_server import start_server

if __name__ == '__main__':
    if len(sys.argv) < 2:
        script = sys.argv[0]
        sys.exit(f"Usage: python {script} <server_port>")
    logging.basicConfig(level=logging.INFO)
    server_port = int(sys.argv[1])
    start_server(server_port)

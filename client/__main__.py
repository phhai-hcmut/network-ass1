import argparse
import logging

from .gui import Client

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('server_addr')
    parser.add_argument('server_port', type=int)
    parser.add_argument('rtp_port', type=int)
    parser.add_argument('file_name')
    args = parser.parse_args()

    logging_format = "{asctime}:{levelname}:{message}"
    logging.basicConfig(level=logging.DEBUG, format=logging_format, style='{')

    # Create a new client
    app = Client(**vars(args))
    app.master.title("RTPClient")
    app.mainloop()

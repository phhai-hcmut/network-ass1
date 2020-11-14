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

    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(message)s"
    )

    # Create a new client
    app = Client(**vars(args))
    app.title("RTPClient")
    app.mainloop()

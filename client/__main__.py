import argparse
import logging

from .gui import Client, SimpleClient

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('server_addr')
    parser.add_argument('server_port', type=int)
    parser.add_argument('rtp_port', type=int)
    parser.add_argument('filename')
    parser.add_argument('--simple', action='store_true', help="use simple GUI")
    args = vars(parser.parse_args())

    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(message)s"
    )

    # Create a new client
    simple = args.pop('simple')
    if simple:
        app = SimpleClient(**args)
    else:
        app = Client(**args)
    app.title("RTPClient")
    app.mainloop()

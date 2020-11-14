import argparse
import logging

from .gui import Client,Client2

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('server_addr')
    parser.add_argument('server_port', type=int)
    parser.add_argument('rtp_port', type=int)
    parser.add_argument('file_name')
    parser.add_argument('-simple',action='store_true',help='use simple GUI')
    
    args = parser.parse_args()
    simple = args.simple


    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(message)s"
    )

    # Create a new client
    arg_dict = vars(args)
    arg_dict.pop('simple')
    app = Client2(**arg_dict) if simple else Client(**arg_dict)
    app.title("RTPClient")
    app.mainloop()

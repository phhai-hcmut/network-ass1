import sys
from tkinter import Tk

from .gui import Client

if __name__ == '__main__':
    if len(sys.argv) < 5:
        script = sys.argv[0]
        sys.exit("Usage: python3 -m client <server_addr> <server_port> <rtp_port> <video_file>")

    server_addr = sys.argv[1]
    server_port = int(sys.argv[2])
    rtp_port = int(sys.argv[3])
    file_name = sys.argv[4]

    root = Tk()

    # Create a new client
    app = Client(root, server_addr, server_port, rtp_port, file_name)
    app.master.title("RTPClient")
    root.mainloop()

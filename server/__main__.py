import glob
import logging
import os
import sys

from .rtsp_server import start_server

if __name__ == '__main__':
    if len(sys.argv) < 2:
        script = sys.argv[0]
        sys.exit(f"Usage: python {script} <server_port>")

    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(message)s"
    )
    server_port = int(sys.argv[1])
    os.chdir('video')
    video_files = glob.glob('*.mjpeg')
    start_server(server_port, video_files=video_files)

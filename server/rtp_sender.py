import logging
import threading
import time
import socket


RTP_PT_JPEG = 26


class RTPSender(threading.Thread):
    VERSION = 2
    PADDING = 0
    EXTENSION = 0
    CC = 0
    MARKER = 0
    SSRC = 0

    def __init__(self, recv_addr, video_stream):
        super().__init__()
        # Create a new socket for RTP/UDP
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_addr = recv_addr
        self.video_stream = video_stream
        self.is_playing = threading.Event()
        self._closed = False

    def run(self):
        while self.is_playing.wait() and not self._closed:
            data = self.video_stream.read()
            if data:
                packet = self.make_rtp(data, self.video_stream.frame_num)
                try:
                    logging.debug(
                        "Send frame #%d of %d bytes to %s:%d",
                        self.video_stream.frame_num, len(packet), *self.recv_addr
                    )
                    self._socket.sendto(packet, self.recv_addr)
                except socket.error as err:
                    logging.warning(err)
                    print("Connection Error")
            # else:
            #     # Reach end of stream
            #     self.pause()
            #     continue
            time.sleep(1 / self.video_stream.frame_rate)

        self._socket.close()

    def make_rtp(self, payload, seqnum):
        """RTP-packetize the video data."""
        # Get timestamp in microsecond
        timestamp = round(time.monotonic() * 1000)
        headers = bytes([
            self.VERSION << 6 | self.PADDING << 5 | self.EXTENSION << 4 | self.CC,
            self.MARKER << 7 | RTP_PT_JPEG,
            (seqnum >> 8) & 0xFF,
            seqnum & 0xFF,
            (timestamp >> 24) & 0xFF,
            (timestamp >> 16) & 0xFF,
            (timestamp >> 8) & 0xFF,
            timestamp & 0xFF,
            (self.SSRC >> 24) & 0xFF,
            (self.SSRC >> 16) & 0xFF,
            (self.SSRC >> 8) & 0xFF,
            self.SSRC & 0xFF,
        ])
        return headers + payload

    def play(self):
        self.is_playing.set()

    def pause(self):
        self.is_playing.clear()

    def close(self):
        """Stop the RTP sender"""
        self._closed = True
        self.is_playing.set()

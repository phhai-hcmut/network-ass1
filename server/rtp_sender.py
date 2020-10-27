import logging
import threading
import time
import socket


class RTPSender(threading.Thread):
    VERSION = 2
    PADDING = 0
    EXTENSION = 0
    CC = 0
    MARKER = 0
    PT = 26  # MJPEG type
    SSRC = 0

    def __init__(self, client_addr, video_stream):
        super().__init__()
        # Create a new socket for RTP/UDP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_addr = client_addr
        self.video_stream = video_stream
        self.is_playing = threading.Event()

    def run(self):
        self.is_playing.set()
        while True:
            if not self.closed:
                if not self.is_playing.wait(1 / self.video_stream.frame_rate):
                    continue
            else:
                self.socket.close()
                return

            data = self.video_stream.get_next_frame()
            if data:
                packet = self.make_rtp(data, self.video_stream.frame_num)
                try:
                    self.socket.sendto(packet, self.client_addr)
                except socket.error as err:
                    logging.warn(err)
                    # print("Connection Error")
            else:
                # Reach end of stream
                break
            time.sleep(1 / self.video_stream.frame_rate)

    def make_rtp(self, payload, framenum):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = framenum
        ssrc = 0

        rtp_packet = RTPPacket()
        rtp_packet.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
        return rtp_packet.get_packet()

    def play(self):
        self.is_playing.set()

    def pause(self):
        self.is_playing.clear()

    def close(self):
        self.closed = True


class RTPPacket:
    def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload):
        # Get timestamp in microsecond
        timestamp = round(time.monotonic() * 1000)
        headers = bytearray([
            version << 6 | padding << 5 | extension << 4 | cc,
            marker << 7 | pt,
            (seqnum >> 8) & 0xFF,
            seqnum & 0xFF,
            (timestamp >> 24) & 0xFF,
            (timestamp >> 16) & 0xFF,
            (timestamp >> 8) & 0xFF,
            timestamp & 0xFF,
            (ssrc >> 24) & 0xFF,
            (ssrc >> 16) & 0xFF,
            (ssrc >> 8) & 0xFF,
            ssrc & 0xFF,
        ])
        self.packet = headers + payload

    def get_packet(self):
        return self.packet

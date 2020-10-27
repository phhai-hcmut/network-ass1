import time


class RtpPacket:
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

    def getPacket(self):
        return self.packet

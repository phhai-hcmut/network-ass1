import logging
import socket
import threading
import time


HEADER_SIZE = 12


class RTPReceiver(threading.Thread):
    def __init__(self, listen_port, callback, timeout=0.5):
        super().__init__()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('localhost', listen_port))
        self.socket.settimeout(timeout)
        self.data = []
        self.callback = callback
        self.is_playing = threading.Event()
        self.closed = False

    def run(self):
        """Return data of a RTP packet."""
        # UDP is a message-based protocol, so each time we call recvfrom(),
        # we get the whole packet. It is important to set the buffer large enough
        # to store all the content of the packet
        while self.is_playing.wait():
            try:
                packet, sender_addr = self.socket.recvfrom(1 << 15)
            except socket.timeout:
                # When pausing the client, the socket will just timeout and stop, no big deal.
                logging.info("Socket timeout")
                # break
            seqnum = (packet[2] << 8) + packet[3]
            logging.debug(
                "Receive frame #%d of %d bytes from %s:%s",
                seqnum, len(packet), *sender_addr
            )
            # Skip header
            payload = packet[HEADER_SIZE:]
            self.callback(payload)
            self.data.append((time.time(), len(payload)))

    def play(self):
        self.is_playing.set()

    def pause(self):
        self.is_playing.clear()

    def close(self):
        if self.data:
            with open('stats2.csv', 'w') as f:
                f.write('time,size\n')
                start_time = self.data[0][0]
                for ptime, size in self.data:
                    f.write(f'{ptime - start_time},{size}\n')
        self.socket.close()

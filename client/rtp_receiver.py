import logging
import socket


class RTPReceiver:
    def __init__(self, listen_port, timeout=0.5):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('localhost', listen_port))
        self.socket.settimeout(timeout)

    def read(self):
        """Return data of a RTP packet."""
        # UDP is a message-based protocol, so each time we call recvfrom(),
        # we get the whole packet. It is important to set the buffer large enough
        # to store all the content of the packet
        packet, sender_addr = self.socket.recvfrom(1 << 15)
        logging.debug("Receive %d bytes from %s:%s", len(packet), *sender_addr)
        # Skip header
        return packet[12:]

    def close(self):
        self.socket.close()

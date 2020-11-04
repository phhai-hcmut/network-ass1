import socket


class RTPReceiver:
    def __init__(self, listen_port, timeout=0.5):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('localhost', listen_port))
        self.socket.settimeout(timeout)
        print('RTPRev Inited at: ', listen_port)

    def get_data(self):
        """Return data of a RTP packet."""
        # UDP is a message-based protocal, so each time we call recvfrom(),
        # we get the whole packet. It is important to set the buffer large enough
        # to store all the content of the packet
        packet, _ = self.socket.recvfrom(1<<15)
        # Skip header
        return packet[12:]

    def close(self):
        self.socket.close()

import logging
import socket
import time


class RTPReceiver:
    HEADER_SIZE = 12

    def __init__(self, listen_port, timeout=0.5):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(('localhost', listen_port))
        self._socket.settimeout(timeout)
        self.data = []

    def read(self):
        """Return data of a RTP packet."""
        # UDP is a message-based protocol, so each time we call recvfrom(),
        # we get the whole packet. It is important to set the buffer large enough
        # to store all the content of the packet
        try:
            packet, sender_addr = self._socket.recvfrom(1 << 20)
        except socket.timeout:
            # When pausing the client, the socket will just timeout and stop, no big deal.
            # print('socket timeout')
            return
        seqnum = (packet[2] << 8) + packet[3]
        logging.debug(
            "Receive frame #%d of %d bytes from %s:%s",
            seqnum,
            len(packet),
            *sender_addr,
        )
        # Skip header
        payload = packet[self.HEADER_SIZE:]
        self.data.append((time.time(), len(payload)))
        return payload

    def close(self):
        if self.data:
            with open('stats.csv', 'w') as f:
                f.write('time,size\n')
                start_time = self.data[0][0]
                for ptime, size in self.data:
                    f.write(f'{ptime - start_time},{size}\n')
        self._socket.close()

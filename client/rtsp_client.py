from enum import Enum
import socket


RTSPState = Enum('RTSPState', ['INIT', 'READY', 'PLAYING'])


class RTSPClientException(Exception):
    pass


class RTSPError(RTSPClientException):
    """A RTSP error occurred."""
    pass


class InvalidMethodError(RTSPClientException):
    """Issue a method not valid in a state."""
    def __init__(self, state, method):
        state = state.name.title()
        method = method.upper()
        self.message = f"Method {method} not valid in state {state}"


class RTSPClient:
    RTSP_VERSION = 'RTSP/1.0'

    def __init__(self, server_addr):
        # Open a TCP connection to the server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(server_addr)

        self.state = RTSPState.INIT
        self.seq_num = 1
        self.session_id = None

    def setup(self, file_name, rtp_port):
        self.file_name = file_name
        header = f'Transport: RTP/UDP; client_port= {rtp_port}'
        resp = self._request('SETUP', header)

        self.session_id = resp['Session']
        self.state = RTSPState.READY

    def play(self):
        if self.state == RTSPState.INIT:
            raise InvalidMethodError(self.state, 'PLAY')
        elif self.state == RTSPState.READY:
            self._request('PLAY')
            self.state = RTSPState.PLAYING

    def pause(self):
        if self.state == RTSPState.INIT:
            raise InvalidMethodError(self.state, 'PLAY')
        elif self.state == RTSPState.PLAYING:
            self._request('PAUSE')
            self.state = RTSPState.READY

    def teardown(self):
        if self.state != RTSPState.INIT:
            self._request('TEARDOWN')
            self.session_id = None
            self.state = RTSPState.INIT

    def _request(self, method, headers=None):
        req_message = [
            # Request line
            f'{method} {self.file_name} {self.RTSP_VERSION}',
            # Sequence number for an RTSP request-response pair
            f'CSeq: {self.seq_num}',
        ]

        if method == 'SETUP':
            req_message.append(headers)
        else:
            req_message.append(f'Session: {self.session_id}')

        req_message = '\n'.join(req_message).encode()

        resp_message = self._send(req_message)
        self.seq_num += 1
        return self._process_response(resp_message)

    def _send(self, req_message):
        # Send a request message to the server
        self.socket.send(req_message)

        # Receive a reponse message from the server.
        # TCP is a stream-based protocol, so the data returned by recv()
        # is not guaranteed to be a complete response message from the server
        data = self.socket.recv(1024)
        return data

    def _process_response(self, message):
        resp = message.decode().splitlines()
        status_line = resp[0].split(' ')
        status_code = int(status_line[1])
        if status_code != 200:
            raise RTSPError(" ".join(status_line[1:]))

        def make_header(line):
            header_line = line.split(' ')
            header_name = header_line[0].strip(':')
            return (header_name, ' '.join(header_line[1:]))
        headers = dict([make_header(line) for line in resp[1:]])
        return headers

    def close(self):
        self.socket.close()

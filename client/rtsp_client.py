from enum import Enum
import logging
import socket


# def _parse_sdp(input):
#     def parse_line(line):
#         field, _, value = line.partition('=')
#         return (field, value)
#     parsed = list


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
        self.seq_num = 0
        self.session_id = None

    def describe(self, file_name):
        self.file_name = file_name
        header = 'Accept: application/sdp'
        _, msg = self._request('DESCRIBE', header)
        self.file_name = None
        return msg

    def setup(self, file_name, rtp_port):
        if self.state != RTSPState.INIT:
            raise InvalidMethodError(self.state, 'SETUP')
        self.file_name = file_name
        header = f'Transport: RTP/UDP; client_port= {rtp_port}'
        resp_headers, _ = self._request('SETUP', header)

        self.session_id = resp_headers['Session']
        self.state = RTSPState.READY
        logging.info("RTSP client in state %s", self.state)

    def play(self, begin=None, end=None):
        if self.state == RTSPState.INIT:
            raise InvalidMethodError(self.state, 'PLAY')
        else:
            headers = None
            if begin is not None:
                headers = f'Range: npt={begin}-'
                if end is not None:
                    headers += str(end)
            resp = self._request('PLAY', headers)[0]
            if int(resp['CSeq']) == self.seq_num and resp['Session'] == self.session_id:
                self.state = RTSPState.PLAYING
        logging.info("RTSP client in state %s", self.state)

    def pause(self):
        if self.state == RTSPState.INIT:
            raise InvalidMethodError(self.state, 'PAUSE')
        elif self.state == RTSPState.PLAYING:
            resp = self._request('PAUSE')[0]
            if int(resp['CSeq']) == self.seq_num and resp['Session'] == self.session_id:
                self.state = RTSPState.READY
                logging.info("RTSP client in state %s", self.state)
                # return self._parse_npt(resp['Range'])

    def teardown(self):
        if self.state != RTSPState.INIT:
            resp = self._request('TEARDOWN')[0]
            if int(resp['CSeq']) == self.seq_num and resp['Session'] == self.session_id:
                self.session_id = None
                self.state = RTSPState.INIT
        logging.info("RTSP client in state %s", self.state)

    def _request(self, method, headers=None):
        self.seq_num += 1
        req_message = [
            # Request line
            f'{method} {self.file_name} {self.RTSP_VERSION}',
            # Sequence number for an RTSP request-response pair
            f'CSeq: {self.seq_num}',
        ]

        if method not in ['SETUP', 'DESCRIBE']:
            req_message.append(f'Session: {self.session_id}')

        if headers:
            req_message.append(headers)

        req_message = '\n'.join(req_message).encode()

        resp_message = self._send(req_message)
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

        if '' in resp:
            # The response contains body
            body_idx = resp.index('') + 1
            headers = resp[1:body_idx - 1]
            body = resp[body_idx:]
        else:
            headers = resp[1:]
            body = None

        def make_header(line):
            header_line = line.split(' ')
            header_name = header_line[0].strip(':')
            return (header_name, ' '.join(header_line[1:]))
        headers = dict([make_header(line) for line in headers])
        logging.info("Receive %s", headers)
        return headers, body

    def close(self):
        self.socket.close()

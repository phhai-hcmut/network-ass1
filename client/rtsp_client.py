from enum import Enum
import logging
import socket


RTSPState = Enum('RTSPState', ['INIT', 'READY', 'PLAYING', 'SWITCH'])


class RTSPClientException(Exception):
    pass


class RTSPError(RTSPClientException):
    """A RTSP error occurred."""


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
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(server_addr)

        self._state = RTSPState.INIT
        self._filename = None
        self._seqnum = 0
        self._session_id = None

    @property
    def state(self):
        return self._state

    def describe(self, file_name):
        self._filename = file_name
        header = 'Accept: application/sdp'
        _, msg = self._request('DESCRIBE', header)
        return msg

    def setup(self, file_name, rtp_port):
        if self._state != RTSPState.INIT:
            raise InvalidMethodError(self._state, 'SETUP')
        self._filename = file_name
        header = f'Transport: RTP/UDP; client_port= {rtp_port}'
        resp_headers, _ = self._request('SETUP', header)

        self._session_id = resp_headers['Session']
        self._state = RTSPState.READY
        logging.info("RTSP client in state %s", self._state)

    def play(self, begin=None, end=None):
        if self._state == RTSPState.INIT:
            raise InvalidMethodError(self._state, 'PLAY')

        headers = None
        if begin is not None:
            headers = f'Range: npt={begin}-'
            if end is not None:
                headers += str(end)
        resp = self._request('PLAY', headers)[0]
        if int(resp['CSeq']) == self._seqnum and resp['Session'] == self._session_id:
            self._state = RTSPState.PLAYING
        logging.info("RTSP client in state %s", self._state)

    def switch(self, previous=False):
        if self._state == RTSPState.INIT:
            raise InvalidMethodError(self._state, 'SWITCH')

        if self._state == RTSPState.PLAYING:
            self.pause()

        resp = self._request('PREVIOUS')[0] if previous else self._request('NEXT')[0]
        if int(resp['CSeq']) == self._seqnum:
            self._filename = resp['New-Filename']
            self._state = RTSPState.SWITCH
            logging.info("RTSP client in state %s", self._state)
            return self._filename

    def pause(self):
        if self._state == RTSPState.INIT:
            raise InvalidMethodError(self._state, 'PAUSE')
        elif self._state == RTSPState.PLAYING:
            resp = self._request('PAUSE')[0]
            if (
                int(resp['CSeq']) == self._seqnum
                and resp['Session'] == self._session_id
            ):
                self._state = RTSPState.READY
                logging.info("RTSP client in state %s", self._state)
                # return self._parse_npt(resp['Range'])

    def teardown(self):
        if self._state != RTSPState.INIT:
            resp = self._request('TEARDOWN')[0]
            if (
                int(resp['CSeq']) == self._seqnum
                and resp['Session'] == self._session_id
            ):
                self._session_id = None
                self._state = RTSPState.INIT
        logging.info("RTSP client in state %s", self._state)

    def _request(self, method, headers=None):
        self._seqnum += 1
        req_message = [
            # Request line
            f'{method} {self._filename} {self.RTSP_VERSION}',
            # Sequence number for an RTSP request-response pair
            f'CSeq: {self._seqnum}',
        ]

        if method not in ['SETUP', 'DESCRIBE']:
            req_message.append(f'Session: {self._session_id}')

        if headers:
            req_message.append(headers)

        req_message = '\n'.join(req_message).encode()

        resp_message = self._send(req_message)
        logging.info("Receive of response message:\n%s", resp_message.decode())
        return self._process_response(resp_message)

    def _send(self, req_message):
        # Send a request message to the server
        self._socket.sendall(req_message)

        # Receive a reponse message from the server.
        # TCP is a stream-based protocol, so the data returned by recv()
        # is not guaranteed to be a complete response message from the server
        data = self._socket.recv(1024)
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
            headers = resp[1 : body_idx - 1]
            body = resp[body_idx:]
        else:
            headers = resp[1:]
            body = None

        def make_header(line):
            header_line = line.split(' ')
            header_name = header_line[0].strip(':')
            return (header_name, ' '.join(header_line[1:]))

        headers = dict(make_header(line) for line in headers)
        return headers, body

    def close(self):
        self._socket.close()

from enum import Enum
import logging
from random import randint
import socket
import threading

from .rtp_sender import RTPSender, MJPEG_TYPE
from .video_stream import VideoStream


def _parse_npt(string):
    begin, end = string.removeprefix('npt=').split('-')
    begin = float(begin)
    if end:
        end = float(end)
    else:
        end = None
    return begin, end


def start_server(listen_port, listen_addr=''):
    rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rtsp_socket.bind((listen_addr, listen_port))
    rtsp_socket.listen(5)

    while True:
        # Receive client info (address, port) through RTSP/TCP session
        worker_sock, client_addr_info = rtsp_socket.accept()
        logging.info("Accept new connection from %s:%d", *client_addr_info)
        server_worker = ServerWorker(worker_sock)
        server_worker.start()


RTSPState = Enum('RTSPState', ['INIT', 'READY', 'PLAYING'])


class RTSPResponse(Enum):
    """Enum class for RTSP status code and reason phrase"""
    OK = '200 OK'
    FILE_NOT_FOUND = '404 Not Found'
    CONN_ERR = '500 Connection Error'
    INVALID_METHOD = '455 Method Not Valid In This State'


class ServerWorker(threading.Thread):
    RTSP_VERSION = 'RTSP/1.0'

    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        self._state = RTSPState.INIT
        self._video_stream = None
        self._session_id = None
        self._rtp_sender = None
        self._seqnum = None

    @property
    def client_addr(self):
        """The address of connected client"""
        return self.socket.getpeername()

    def run(self):
        """Receive RTSP request from the client."""
        while True:
            data = self.socket.recv(1024)
            if data:
                logging.info("Data received:\n%s", data.decode())
                self._process_rtsp_request(data)
            else:
                # The client has closed connection
                logging.info("Client %s:%d disconnected", *self.client_addr)
                break
        self._cleanup()

    def _process_rtsp_request(self, data):
        """Process RTSP request sent from the client."""
        # Get the request type
        request = data.decode().splitlines()
        status_line = request[0].split(' ')
        request_method = status_line[0]

        # Get the media file name
        filename = request[0].split(' ')[1]

        def make_header(line):
            header_line = line.split(' ')
            header_name = header_line[0].strip(':')
            return (header_name, ' '.join(header_line[1:]))
        headers = dict(make_header(line) for line in request[1:])

        # Get the RTSP sequence number
        self._seqnum = int(headers['CSeq'])

        getattr(self, '_process_' + request_method.lower() + '_request')(filename, headers)

    def _process_describe_request(self, filename, headers):
        logging.info("Processing DESCRIBE request")
        try:
            video_stream = VideoStream(filename)
        except FileNotFoundError:
            self._reply_rtsp(RTSPResponse.FILE_NOT_FOUND)
            return

        body = '\n'.join([
            'v=0',
            'o=- {0} {0} IN IP4 {1}'.format(
                self._make_ntp_timestamp(), self.client_addr[0]
            ),
            's=RTSP Session',
            f'm=video 0 RTP/AVP {MJPEG_TYPE}',
            f'a=rtpmap:{MJPEG_TYPE} mjpeg/',
            f'a=framerate:{video_stream.frame_rate}',
            f'a=range:npt=0-{video_stream.duration}',
        ]).encode()
        headers = 'Content-Type: application/sdp'
        self._reply_rtsp(RTSPResponse.OK, headers, body)
        video_stream.close()

    @staticmethod
    def _make_ntp_timestamp():
        from datetime import datetime
        diff = datetime.utcnow() - datetime(1900, 1, 1, 0, 0, 0)
        timestamp = diff.days * 24 * 60 * 60 + diff.seconds
        return timestamp

    def _process_setup_request(self, filename, headers):
        logging.info("Processing SETUP request")
        if self._state == RTSPState.PLAYING:
            # We don't allow client to issue a SETUP request for a
            # stream that is already playing to change transport parameters
            self._reply_rtsp(RTSPResponse.INVALID_METHOD)
            return

        # Get the RTP/UDP port from Transport header
        rtp_port = int(headers['Transport'].split(' ')[2])

        try:
            video_stream = VideoStream(filename)
        except FileNotFoundError:
            self._reply_rtsp(RTSPResponse.FILE_NOT_FOUND)
            return

        if self._video_stream is not None:
            # Close old video_stream before open new one
            self._video_stream.close()
        self._video_stream = video_stream

        if self._rtp_sender is None:
            rtp_addr = (self.client_addr[0], rtp_port)
            try:
                rtp_sender = RTPSender(rtp_addr, self._video_stream)
            except socket.error:
                pass
            else:
                self._rtp_sender = rtp_sender
                # Create a new thread and start sending RTP packets
                self._rtp_sender.start()
        else:
            # Send new video stream
            self._rtp_sender.video_stream = self._video_stream

        # Generate a randomized RTSP session ID
        self._session_id = randint(100000, 999999)

        self._reply_rtsp(RTSPResponse.OK)
        self._state = RTSPState.READY

    def _process_play_request(self, filename, headers):
        logging.info("Processing PLAY request")
        if self._state == RTSPState.INIT:
            # Client must call SETUP method before PLAY method
            self._reply_rtsp(RTSPResponse.INVALID_METHOD)
            return

        play_range = headers.get('Range', None)
        if play_range is not None:
            begin, _ = _parse_npt(play_range)
            self._video_stream.set_time(begin)

        self._rtp_sender.play()
        self._reply_rtsp(RTSPResponse.OK)
        self._state = RTSPState.PLAYING

    def _process_pause_request(self, filename, headers):
        logging.info("Processing PAUSE request")
        if self._state == RTSPState.INIT:
            self._reply_rtsp(RTSPResponse.INVALID_METHOD)
        else:
            self._rtp_sender.pause()
            self._reply_rtsp(RTSPResponse.OK)
            self._state = RTSPState.READY

    def _process_teardown_request(self, filename, headers):
        logging.info("Processing TEARDOWN request")
        self._cleanup()
        self._session_id = None
        self._reply_rtsp(RTSPResponse.OK)
        self._state = RTSPState.INIT

    def _reply_rtsp(self, resp, headers=None, body=None):
        """Send RTSP reply to the client."""
        resp = resp.value
        reply = [
            f'{self.RTSP_VERSION} {resp}',  # status line
            f'CSeq: {self._seqnum}',
            f'Session: {self._session_id}',
        ]

        if headers:
            reply.append(headers)
        resp_msg = '\n'.join(reply).encode()
        if body:
            resp_msg += f'\nContent-Length: {len(body)}\n\n'.encode() + body
        sent_msg = self.socket.send(resp_msg)
        logging.info("Sent %d out of %d bytes", sent_msg, len(resp_msg))

    def _cleanup(self):
        if self._video_stream is not None:
            self._video_stream.close()
            self._video_stream = None

        if self._rtp_sender is not None:
            self._rtp_sender.close()
            self._rtp_sender.join()
            self._rtp_sender = None

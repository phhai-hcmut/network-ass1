from enum import Enum
import logging
from random import randint
import socket
import threading

from .rtp_sender import RTPSender, RTP_PT_JPEG
from .video_stream import VideoStream


def _make_ntp_timestamp():
    from datetime import datetime
    diff = datetime.utcnow() - datetime(1900, 1, 1, 0, 0, 0)
    timestamp = diff.days * 24 * 60 * 60 + diff.seconds
    return timestamp


def start_server(listen_port, listen_addr='', video_files=None):
    rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rtsp_socket.bind((listen_addr, listen_port))
    rtsp_socket.listen(5)

    while True:
        # Receive client info (address, port) through RTSP/TCP session
        worker_sock, client_addr_info = rtsp_socket.accept()
        logging.info("Accept new connection from %s:%d", *client_addr_info)
        server_worker = ServerWorker(worker_sock, video_files)
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

    def __init__(self, rtsp_socket, video_files):
        super().__init__()
        self._socket = rtsp_socket
        self._state = RTSPState.INIT
        self.video_files = video_files
        self._cur_idx = None
        self._video_stream = None
        self._session_id = None
        self._rtp_sender = None
        self._seqnum = None

    @property
    def client_addr(self):
        """The address of connected client"""
        return self._socket.getpeername()

    def run(self):
        """Receive RTSP request from the client."""
        while True:
            data = self._socket.recv(1024)
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

        getattr(self, f'_process_{request_method.lower()}_request')(filename, headers)

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
                _make_ntp_timestamp(), self.client_addr[0]
            ),
            's=RTSP Session',
            f'm=video 0 RTP/AVP {RTP_PT_JPEG}',
            f'a=rtpmap:{RTP_PT_JPEG} mjpeg',
            f'a=framerate:{video_stream.frame_rate}',
            f'a=range:npt=0-{video_stream.duration}',
        ]).encode()
        headers = 'Content-Type: application/sdp'
        self._reply_rtsp(RTSPResponse.OK, headers, body)
        video_stream.close()

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

        if self.video_files:
            self._cur_idx = self.video_files.index(filename)
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
            begin, _ = play_range.removeprefix('npt=').split('-')
            self._video_stream.set_time(float(begin))

        self._rtp_sender.play()
        self._reply_rtsp(RTSPResponse.OK)
        self._state = RTSPState.PLAYING

    def _process_next_request(self, filename, headers):
        logging.info("Processing NEXT request")
        self._process_switch_request()

    def _process_previous_request(self, filename, headers):
        logging.info("Processing PREVIOUS request")
        self._process_switch_request(previous=True)

    def _process_switch_request(self, previous=False):
        if self._state != RTSPState.READY:
            self._reply_rtsp(RTSPResponse.INVALID_METHOD)
        else:
            offset = -1 if previous else 1
            self._cur_idx = (self._cur_idx + offset) % len(self.video_files)
            new_filename = self.video_files[self._cur_idx]
            headers = 'New-Filename: ' + new_filename
            self._video_stream = VideoStream(new_filename)
            self._rtp_sender.video_stream = self._video_stream
            self._reply_rtsp(RTSPResponse.OK, headers)
            self._state = RTSPState.READY

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
        self._socket.sendall(resp_msg)
        logging.info("Sent reponse message of %d bytes", len(resp_msg))

    def _cleanup(self):
        if self._rtp_sender is not None:
            self._rtp_sender.close()
            self._rtp_sender.join()
            self._rtp_sender = None

        if self._video_stream is not None:
            self._video_stream.close()
            self._video_stream = None

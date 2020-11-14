from enum import Enum
import logging
import os.path
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
        server_worker = ServerWorker(worker_sock, client_addr_info)
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

    def __init__(self, socket, client_addr_info):
        super().__init__()
        self.socket = socket
        self.client_addr = client_addr_info
        self.state = RTSPState.INIT
        self.video_stream = None
        self.session_id = None
        self.rtp_sender = None
        self.seqnum = None

    def run(self):
        """Receive RTSP request from the client."""
        while True:
            data = self.socket.recv(1024)
            if data:
                logging.info("Data received:\n%s", data.decode())
                self.process_rtsp_request(data)
            else:
                # The client has closed connection
                break
        logging.info("Client %s:%d disconnected", *self.client_addr)

    def process_rtsp_request(self, data):
        """Process RTSP request sent from the client."""
        # Get the request type
        request = data.decode().splitlines()
        status_line = request[0].split(' ')
        request_method = status_line[0]

        # Get the RTSP sequence number
        self.seqnum = request[1].split(' ')[1]

        getattr(self, '_process_' + request_method.lower() + '_request')(request)

    def _process_describe_request(self, request):
        logging.info("Processing DESCRIBE request")
        filename = request[0].split(' ')[1]
        try:
            video_stream = VideoStream(filename)
        except FileNotFoundError:
            self.reply_rtsp(RTSPResponse.FILE_NOT_FOUND)
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
        self.reply_rtsp(RTSPResponse.OK, headers, body)
        video_stream.close()

    @staticmethod
    def _make_ntp_timestamp():
        from datetime import datetime
        diff = datetime.utcnow() - datetime(1900, 1, 1, 0, 0, 0)
        timestamp = diff.days * 24 * 60 * 60 + diff.seconds
        return timestamp

    def _process_setup_request(self, request):
        logging.info("Processing SETUP request")
        if self.state == RTSPState.PLAYING:
            # We don't allow client to issue a SETUP request for a
            # stream that is already playing to change transport parameters
            self.reply_rtsp(RTSPResponse.INVALID_METHOD)
        else:
            # Get the media file name
            filename = request[0].split(' ')[1]

            # Get the RTP/UDP port from the last line
            self.rtp_port = int(request[2].split(' ')[3])

            if self.video_stream is not None:
                # Close old video_stream before open new one
                self.video_stream.close()
                self.video_stream = None

            try:
                video_stream = VideoStream(filename)
            except FileNotFoundError:
                self.reply_rtsp(RTSPResponse.FILE_NOT_FOUND)
            else:
                self.video_stream = video_stream

                # Generate a randomized RTSP session ID
                self.session_id = randint(100000, 999999)

                self.reply_rtsp(RTSPResponse.OK)
                self.state = RTSPState.READY

    def _set_stream_time(self, request):
        play_range = None
        for line in request:
            if line.startswith('Range:'):
                play_range = line.partition(' ')[2]
        if play_range:
            begin, _ = _parse_npt(play_range)
            self.video_stream.set_time(begin)

    def _process_play_request(self, request):
        logging.info("Processing PLAY request")
        if self.state == RTSPState.INIT:
            # Client must call SETUP method before PLAY method
            self.reply_rtsp(RTSPResponse.INVALID_METHOD)

        elif self.state == RTSPState.READY:
            if self.rtp_sender is None:
                try:
                    rtp_addr = (self.client_addr[0], self.rtp_port)
                    rtp_sender = RTPSender(rtp_addr, self.video_stream)
                except socket.error:
                    pass
                else:
                    self.rtp_sender = rtp_sender
                    # Create a new thread and start sending RTP packets
                    self.rtp_sender.start()
            self._set_stream_time(request)
            self.rtp_sender.play()
            self.reply_rtsp(RTSPResponse.OK)
            self.state = RTSPState.PLAYING

        elif self.state == RTSPState.PLAYING:
            self._set_stream_time(request)
            self.reply_rtsp(RTSPResponse.OK)

    def _process_pause_request(self, request):
        logging.info("Processing PAUSE request")
        if self.state == RTSPState.INIT:
            self.reply_rtsp(RTSPResponse.INVALID_METHOD)

        elif self.state == RTSPState.PLAYING:
            self.rtp_sender.pause()
            self.reply_rtsp(RTSPResponse.OK)
            self.state = RTSPState.READY

        elif self.state == RTSPState.READY:
            self.reply_rtsp(RTSPResponse.OK)

    def _process_teardown_request(self, request):
        logging.info("Processing TEARDOWN request")
        if self.video_stream is not None:
            self.video_stream.close()

        if self.rtp_sender is not None:
            # Close the RTP sender
            self.rtp_sender.close()
            self.rtp_sender.join()

        self.video_stream = None
        self.session_id = None
        self.rtp_sender = None
        self.reply_rtsp(RTSPResponse.OK)
        self.state = RTSPState.INIT

    def reply_rtsp(self, resp, headers=None, body=None):
        """Send RTSP reply to the client."""
        resp = resp.value
        reply = [
            f'{self.RTSP_VERSION} {resp}',  # status line
            f'CSeq: {self.seqnum}',
            f'Session: {self.session_id}',
        ]

        if headers:
            reply.append(headers)
        resp_msg = '\n'.join(reply).encode()
        if body:
            resp_msg += f'\nContent-Length: {len(body)}\n\n'.encode() + body
        sent_msg = self.socket.send(resp_msg)
        logging.info(f"Sent {sent_msg} out of {len(resp_msg)} bytes")

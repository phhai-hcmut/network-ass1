import socket

from client import RTSPClient, RTPReceiver

rtp_port = 2000
client = RTSPClient(('localhost', 20000))
client.setup('movie.Mjpeg', rtp_port)
client.teardown()
client.close()

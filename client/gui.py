import tkinter as tk

# from .rtsp import RTSPClient
# from .rtp import RTPReceiver


class Client(tk.Frame):
    """GUI interface for RTSP client"""
    def __init__(self, master, server_addr, server_port, rtp_port, file_name):
        self.master = master
        # self.rtsp_client = RTSPClient((server_addr, server_port))
        # self.rtp_port = rtp_port

    def setup(self):
        # self.rtp_recv = RTPReceiver(self.rtp_port)
        pass

    def play(self):
        # self.rtsp_client.play()
        pass

import logging
import tkinter as tk

from PIL import ImageTk, Image

from .rtsp_client import RTSPClient
from .rtp_receiver import RTPReceiver


class Client(tk.Frame):
    """GUI interface for RTSP client"""

    def __init__(self, server_addr, server_port, rtp_port, file_name):
        super().__init__()
        self.master.protocol('WM_DELETE_WINDOW', self.on_exit)
        self.rtsp_client = RTSPClient((server_addr, server_port))
        self.rtp_port = rtp_port
        self.file_name = file_name
        self.rtp_recv = None
        self.create_widgets()

    def create_widgets(self):
        # self.master.geometry("400x380")
        self.pack()
        placeholer_img = ImageTk.BitmapImage(Image.new('1', (384, 288)))
        self.image_frame = tk.Label(self, image=placeholer_img)
        self.image_frame.grid(row=0, column=0, columnspan=4)

        setup_button = tk.Button(
            self, text="Setup", command=self.setup, height=2, width=10
        )
        setup_button.grid(row=1, column=0)

        play_button = tk.Button(
            self, text="Play", command=self.play, height=2, width=10
        )
        play_button.grid(row=1, column=1)

        pause_button = tk.Button(
            self, text="Pause", command=self.pause, height=2, width=10
        )
        pause_button.grid(row=1, column=2)

        teardown_button = tk.Button(
            self, text="TearDown", command=self.teardown, height=2, width=10
        )
        teardown_button.grid(row=1, column=3)

    def setup(self):
        self.rtsp_client.setup(self.file_name, self.rtp_port)
        self.rtp_recv = RTPReceiver(self.rtp_port)

    def play(self):
        self.rtsp_client.play()

        while True:
            video_data = self.rtp_recv.read()
            if video_data:
                self.show_jpeg(video_data)
            else:
                break

    def pause(self):
        self.rtsp_client.pause()
        # when this happens the client socket will just timeout and stop, no big deal.

    def teardown(self):
        self.rtsp_client.teardown()
        self.on_exit()

    def show_jpeg(self, video_data):
        image = ImageTk.PhotoImage(data=video_data)
        self.image_frame.configure(image=image)
        self.image_frame.update()

    def on_exit(self):
        logging.info("Cleaning resources before exiting application...")
        self.rtsp_client.close()
        if self.rtp_recv is not None:
            self.rtp_recv.close()
        self.master.destroy()

import logging
import tkinter as tk
import tkinter.messagebox

from PIL import ImageTk, Image

from .rtsp_client import RTSPClient, RTSPState
from .rtp_receiver import RTPReceiver


class Client(tk.Frame):
    """GUI interface for RTSP client"""
    CONTROL_BUTTONS = ["Describe", "Set up", "Play", "Pause", "Tear down"]

    def __init__(self, master=None, *, server_addr, server_port, rtp_port, file_name):
        super().__init__()
        if master is None:
            # master is toplevel widget (tk.Tk)
            self.master.protocol('WM_DELETE_WINDOW', self.on_closing)
            self.pack()
        else:
            self.bind('<Destroy>', self.on_closing)
        self.rtsp_client = RTSPClient((server_addr, server_port))
        self.rtp_port = rtp_port
        self.file_name = file_name
        self.rtp_recv = None
        self.create_widgets()

    def create_widgets(self):
        placeholer_img = ImageTk.BitmapImage(Image.new('1', (384, 288)))
        self.image_frame = tk.Label(self, image=placeholer_img)
        self.image_frame.grid(row=0, column=0, columnspan=len(self.CONTROL_BUTTONS))

        for i, btn_text in enumerate(self.CONTROL_BUTTONS):
            method = btn_text.replace(" ", '').lower()
            button = tk.Button(
                self, text=btn_text, command=getattr(self, method),
                height=2, width=10
            )
            button.grid(row=1, column=i)

    def describe(self):
        message = "\n".join(self.rtsp_client.describe(self.file_name))
        if message:
            describe_frame = tk.Label(
                self, text=message, background='white',
                justify='left'
            )
            describe_frame.grid(row=2, column=0, columnspan=len(self.CONTROL_BUTTONS))

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

    def teardown(self):
        self.rtsp_client.teardown()
        self.on_closing()

    def show_jpeg(self, video_data):
        image = ImageTk.PhotoImage(data=video_data)
        self.image_frame.configure(image=image)
        self.image_frame.update()

    def on_closing(self, event=None):
        if self.rtsp_client.state != RTSPState.INIT:
            self.pause()
            if tk.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
                self.cleanup()
            else:
                # Continue playing video
                self.play()
                return

        if isinstance(self.master, tk.Tk):
            self.master.destroy()
        else:
            self.destroy()

    def cleanup(self):
        logging.info("Cleaning resources before exiting application...")
        self.rtsp_client.close()
        if self.rtp_recv is not None:
            self.rtp_recv.close()


class Client2(Client):
    """More user-friendly GUI interface for RTSP client"""
    CONTROL_BUTTONS = ["Play", "Pause", "Stop"]

    def play(self):
        super().setup()
        super().play()

    def stop(self):
        super().teardown()

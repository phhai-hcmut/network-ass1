class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'rb')
        self.frame_num = 0
        self.frame_rate = 20

    def get_next_frame(self):
        # Get the framelength from the first 5 bits
        data = self.file.read(5)
        if data:
            frame_length = int(data)

            # Read the current frame
            data = self.file.read(frame_length)
            self.frame_num += 1
        else:
            # Reach end of file
            self.file.close()
        return data

    def close(self):
        self.file.close()

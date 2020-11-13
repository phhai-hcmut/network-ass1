class VideoStream:
    def __init__(self, filename):
        self._file = open(filename, 'rb')
        self.frame_num = -1
        self._read_frames = []
        if filename == 'movie.Mjpeg':
            self.frame_rate = 20
            self.total_frames = 500

    def read(self):
        """Read a frame"""
        if self.frame_num >= self.total_frames:
            # We reached end of video stream
            return

        self.frame_num += 1
        if self.frame_num >= len(self._read_frames):
            self._get_frame(self.frame_num - len(self._read_frames) + 1)

        if self.frame_num >= len(self._read_frames):
            return

        return self._read_frames[self.frame_num]

    def _get_frame(self, num=1):
        for _ in range(num):
            # Get the framelength from the first 5 bits
            data = self._file.read(5)
            if data:
                frame_length = int(data)

                # Read the current frame
                data = self._file.read(frame_length)
                self._read_frames.append(data)
            else:
                # Reach end of file
                break

    def set_time(self, time):
        if time > self.duration:
            self.frame_num = -1

        self.frame_num = round(time * self.frame_rate)

    def close(self):
        """Close the video stream"""
        self._file.close()

    @property
    def duration(self):
        """Duration of the video stream"""
        return self.total_frames / self.frame_rate

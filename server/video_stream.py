import io


class VideoStream:
    def __init__(self, filename):
        self._file = open(filename, 'rb')
        self.frame_num = -1
        self._read_frames = []
        self.frame_rate = 20
        self.total_frames = self._count_frames()

    def read(self):
        """Read a frame"""
        if self.frame_num >= self.total_frames:
            # We reached end of video stream
            return

        self.frame_num += 1
        if self.frame_num >= len(self._read_frames):
            self._get_frames(self.frame_num - len(self._read_frames) + 1)

        if self.frame_num >= len(self._read_frames):
            return

        return self._read_frames[self.frame_num]

    def _get_frames(self, num=1):
        for _ in range(num):
            # Get the framelength from the first 5 bytes
            data = self._file.read(5)
            if data:
                frame_size = int.from_bytes(data, 'big')

                # Read the current frame
                data = self._file.read(frame_size)
                self._read_frames.append(data)
            else:
                # Reach end of file
                break

    def _count_frames(self):
        count = 0
        while True:
            # Get the framelength from the first 5 bytes
            data = self._file.read(5)
            if data:
                frame_size = int.from_bytes(data, 'big')

                # Skip the current frame
                self._file.seek(frame_size, io.SEEK_CUR)
                count += 1
            else:
                # Reach end of file
                break
        self._file.seek(0)
        return count

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

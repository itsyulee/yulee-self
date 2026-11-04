"""OS lock released even if the gateway crashes (Windows and Linux)."""
import os


class InstanceLock:
    def __init__(self, path):
        self.stream = open(path, 'a+b')
        if self.stream.tell() == 0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise RuntimeError('Một YULEESELF server khác đang dùng vùng dữ liệu này.') from None

    def close(self):
        self.stream.close()

import common
import threading
import struct
import zlib

class wildcat_receiver(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_receiver, self).__init__()
        self.allowed_loss = allowed_loss
        self.window_size = window_size
        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False

        self.receiver_window_start = 0
        self.receiver_window = {} # seq_num: payload
        self.wrap_around = 65536
    
    def parse_sender_msg(self, packet_byte_array):
        seq_num = struct.unpack("!H", packet_byte_array[:2])[0]
        checksum_received = struct.unpack("!H", packet_byte_array[-2:])[0]
        checksum_recomputed = zlib.crc32(packet_byte_array[:-2]) & 0xffff
        if checksum_received != checksum_recomputed:
            return None, None
        payload = packet_byte_array[2:-2]
        return seq_num, payload

    def build_ack(self, window_start, bitmap):
        first_two = struct.pack("!H", window_start)
        bitmap_bytes = bytearray()
        for i in range(0, len(bitmap), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bitmap):
                    byte |= (bitmap[i + j] << j)
            bitmap_bytes.append(byte)
        checksum = zlib.crc32(first_two + bitmap_bytes) & 0xffff
        last_two = struct.pack("!H", checksum)
        return first_two + bitmap_bytes + last_two

    def receive(self, packet_byte_array):
        seq_num, payload = self.parse_sender_msg(packet_byte_array)

        # Record packet in receiver window (if not corrupted)
        # We always send ack here, even for corrupted packets and for out-of-window packets
        if seq_num is not None:
            self.receiver_window[seq_num] = payload
        bitmap=[]

        # Go through window range and build bitmap
        for offset in range(self.window_size):
            seq_num = (self.receiver_window_start + offset) % self.wrap_around
            bitmap.append(1 if seq_num in self.receiver_window else 0)
        
        # Build and send ack, also log payload 
        ack = self.build_ack(self.receiver_window_start, bitmap)
        self.my_tunnel.magic_send(ack)

        # Update window start and commit in-order packets to logger (out of order packet buffered in window
        # but won't be committed to log until in-order, i.e. no gaps)
        if seq_num == self.receiver_window_start:
            while self.receiver_window_start in self.receiver_window:
                self.my_logger.commit(self.receiver_window[self.receiver_window_start])
                del self.receiver_window[self.receiver_window_start]
                self.receiver_window_start = (self.receiver_window_start + 1) % self.wrap_around

        

    def run(self):
        while not self.die:
            # TODO: your implementation comes here
            pass
            
    def join(self):
        self.die = True
        super().join()
import common
import threading
import queue
import struct 
import zlib
import time

class wildcat_sender(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_sender, self).__init__()
        self.allowed_loss = allowed_loss # a (rate between 0-100), receiver should receive at least (100-a)% of packets
        self.window_size = window_size # w (window size in packets) 
        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False

        self.window = [] # list of (seq_num, packet, timestamp)
        self.packet_queue = queue.Queue() # queue of packets to be sent
        self.next_seq_num = 0 # seq num of next packet to be sent
        self.window_start = 0 # seq num of first packet in sender window
        self.lock = threading.Lock() # lock for global variables

    def build_msg(self, payload, seq_num):
        seq_num = seq_num % 65536
        first_two = struct.pack("!H", seq_num)
        checksum = zlib.crc32(payload) & 0xffffffff
        last_two = struct.pack("!H", checksum)
        return first_two + payload + last_two
    
    def new_packet(self, packet_byte_array):
        self.lock.acquire()
        self.packet_queue.put(packet_byte_array)
        self.lock.release()
        

    def receive(self, packet_byte_array):
        # TODO: your implementation comes here
        pass
    
    def run(self):
        while not self.die:
            cur_time = time.time()
            while True: 
                with self.Lock: 
                    if len(self.window) < self.window_size and not self.packet_queue.empty():
                        packet = self.packet_queue.get()
                        msg = self.build_msg(packet, self.next_seq_num)
                        self.my_tunnel.magic_send(msg)
                        self.window.append( (self.next_seq_num, packet, cur_time) )
                        self.next_seq_num += 1
                    else: 
                        break
    
    def join(self):
        self.die = True
        super().join()
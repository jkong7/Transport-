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

        self.window = [] # list of (seq_num, packet, timestamp), holds packets in flight
        self.packet_queue = queue.Queue() # queue of packets to be sent
        self.next_seq_num = 0 # seq num of next packet to be sent
        self.window_start = 0 # seq num of first packet in sender window
        self.timeout_interval = 0.5 # allow 0.5s for timeout
        self.wrap_around = 65536 # seq num wrap around value
        self.lock = threading.Lock() # lock for global variables

    def build_msg(self, payload, seq_num):
        seq_num = seq_num % 65536
        first_two = struct.pack("!H", seq_num)
        checksum = zlib.crc32(first_two + payload) & 0xffff
        last_two = struct.pack("!H", checksum)
        return first_two + payload + last_two

    def parse_ack(self, ack_packet):
        receiver_window_start = struct.unpack("!H", ack_packet[:2])[0]
        checksum_received = struct.unpack("!H", ack_packet[-2:])[0]
        checksum_recomputed = zlib.crc32(ack_packet[:-2]) & 0xffff
        if checksum_received != checksum_recomputed:
            return None, None, None

        bitmap = ack_packet[2:-2]
        bits =[]
        for bytes in bitmap: 
            for i in range(8):
                if len(bits) < self.window_size:
                    bits.append((bytes >> i) & 1)
        return receiver_window_start, bits, checksum_received
    
    def new_packet(self, packet_byte_array):
        with self.lock: # Just acquire lock and enqueue packets
            self.packet_queue.put(packet_byte_array)
        

    def receive(self, packet_byte_array):
        receiver_window_start, bits, _ = self.parse_ack(packet_byte_array)
        if receiver_window_start is None: 
            return # corrupted ACK, no handling

        # Remove all packets acked by receiver (check bitmap)
        with self.lock: 
            to_remove = []
            for packet in sorted(self.window, key = lambda x: x[0]):
                seq_num, _, _ = packet
                relative_seq_num = (seq_num - receiver_window_start) % self.wrap_around
                if relative_seq_num < self.window_size:
                    if bits[relative_seq_num] == 1:
                        to_remove.append(packet)
            for packet in to_remove:
                self.window.remove(packet)
            
            # Window start should now be lowest seq num in window
            if self.window:
                self.window_start = self.window[0][0]
            # Or if everything acked, window start aligns to next seq num
            else: 
                self.window_start = self.next_seq_num 
    
    
    def run(self):
        while not self.die:
            cur_time = time.time()
            while True: 
                with self.lock: # Acquire lock as global variables are accessed
                    # If the window isn't full and there are packets to send, we continuously send
                    if len(self.window) < self.window_size and not self.packet_queue.empty():
                        # Pull from queue, build msg, send it, and add to window for bookkeeping
                        packet = self.packet_queue.get()
                        msg = self.build_msg(packet, self.next_seq_num)
                        self.my_tunnel.magic_send(msg)
                        self.window.append( (self.next_seq_num, packet, cur_time) )
                        self.next_seq_num = (self.next_seq_num + 1) % self.wrap_around
                    else: 
                        break # Otherwise, break out of sending loop and move on to checking timeouts

            with self.lock:
                for i in range(len(self.window)):
                    # Any timeouts, resend and update timestamp in window
                    seq_num, packet, timestamp = self.window[i]
                    if cur_time - timestamp > self.timeout_interval:
                        msg = self.build_msg(packet, seq_num)
                        self.my_tunnel.magic_send(msg)
                        self.window[i] = (seq_num, packet, cur_time) 

    
    def join(self):
        self.die = True
        super().join()
import common
import threading

class wildcat_receiver(threading.Thread):
    def __init__(self, allowed_loss, window_size, my_tunnel, my_logger):
        super(wildcat_receiver, self).__init__()
        self.allowed_loss = allowed_loss
        self.window_size = window_size
        self.my_tunnel = my_tunnel
        self.my_logger = my_logger
        self.die = False
        self.buffer = [] * window_size # buffer to hold out-of-order packets
        self.next_expected_seq_num = 0

    def receive(self, packet_byte_array):
        # TODO: your implementation comes here
        seq_num = int.from_bytes(packet_byte_array[0:2], byteorder='big')
        
        pass

    def run(self):
        while not self.die:
            # TODO: your implementation comes here
            pass
            
    def join(self):
        self.die = True
        super().join()
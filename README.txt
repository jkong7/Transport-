Jonathan Kong (dwa0713)
Ethan Hamilton (lvl6015)


Run instructions 

Start the receiver: 

python3 start_receiver.py <PORT> <ALLOWED_LOSS> <WINDOW_SIZE> <LOSS_RATE> <CORRUPT_RATE>

EX: python3 start_receiver.py 8000 20 20 20 20

Start the sender: 

python3 start_sender.py localhost 8000 20 20 20 20

EX: python3 start_sender.py localhost 8000 20 20 20 20

To run automated tests: 

python3 test.py


Design overview: 

This implementation is a selective repeat algorithm over UDP. 

Sender: The sender keeps a window, packet queue, and next sequence number as global state. 
It has three interface functions. Starting with new packet, which simply enqueues packets into
the packet queue. Then, for the run loop, this attempts to send packets to the receiver whenever 
it can. This happens when the packet queue is both not empty and the window isn't full. In this case, 
the correct message format with bytes (payload + checksum/seq num) is sent and pushed into the window 
as well. The window holds packets that are currently in flight and have the timestamp they were sent. 
Then, run will move on to check in flight packets and resend any that are timed out (0.5) through 
the window. Lastly, the sender's receive will check that the ACK wasn't corrupted (if it was, drop).
Then, go through the window and delete any packets whose seq num corresponds with a 1 in the ack bitmap.
The window start also gets updated accordingly. Note that each of these three functions read/write 
the global variables so a global lock is needed before accesses. 

Receiver: The receiver interface interacts with just the receive function which is used as a callback.
The state variables track the receiver window and the receiver window start. The receiver will 
ALWAYS send an ack, no matter if the incoming message got lost/corrupted or it's outside the current
window. The bitmap + window start ack message will always be a source of truth to the sender so as 
long as that's correct, there is no problem with this. The receive puts the incoming packet into the 
window and then builds a bitmap of what's currently in the receiver window starting from the base and 
going forward window size. Parsing and building incoming and outgoing messages are put into helpers. After 
sending the ack, the receiver slides the window start forward, commits packets in order, and deletes sent 
packets from the window. 

Extra considerations: This design uses per-packet timers. Each packet, when put into the sender window, has a 
send timestamp associated with it so that timeout can later be checked in the run loop. In the ack bitmap, 1s are 
used in the receiver ack message to represent a good/acked packet whereas a 0 means it should be retransmitted. 
Checksums are recomputed for incoming messages and compared to the given checksum to determine corruption. Wrap around
handling for all int states are handled with modulo around 2^16. Sender states are sending,
waiting (window full, waiting for acks), retransmitting (timed out packets). Receiver states are
receiving (buffering to window), delivering (sending acks, sliding window + logging). 

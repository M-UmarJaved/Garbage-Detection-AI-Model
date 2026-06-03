import socket

UDP_IP = "192.168.4.2"
UDP_PORT = 1234

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    input("Press Enter")

    sock.sendto(b"HELLO", (UDP_IP, UDP_PORT))

    print("Sent HELLO")
import struct

import utime
from machine import Pin, SPI
from micropython import const

from nrf24l01 import NRF24L01

# Responder pause between receiving data and checking for further packets.
_RX_POLL_DELAY = const(2)
# Responder pauses an additional _RESPONER_SEND_DELAY ms after receiving data and before
# transmitting to allow the (remote) initiator time to get into receive mode. The
# initiator may be a slow device. Value tested with Pyboard, ESP32 and ESP8266.
_RESPONDER_SEND_DELAY = const(10)

# Addresses are in little-endian format. They correspond to big-endian
# 0xf0f0f0f0e1, 0xf0f0f0f0d2
pipes = (b"\xe1\xf0\xf0\xf0\xf0", b"\xd2\xf0\xf0\xf0\xf0")


def initialise_nrf(sck_pin, mosi_pin, miso_pin, csn_pin, ce_pin, payload_size):
    spi = SPI(0, sck=Pin(sck_pin), mosi=Pin(mosi_pin), miso=Pin(miso_pin))
    nrf = NRF24L01(spi, Pin(csn_pin), Pin(ce_pin), payload_size=payload_size)
    return nrf


def chunk(data, chunk_size):
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


def pack_chunks(unpacked_chunks):
    return [struct.pack(f"!II", len(unpacked_chunks), i) + bytes(c, 'utf-8') for i, c in enumerate(unpacked_chunks, start=1)]


def unpack_chunk(packed_chunk):
    return struct.unpack(f"!II{len(packed_chunk) - 8}s", packed_chunk)


def calc_missing(chunks, total_chunks):
    return set(range(1, total_chunks + 1)) - set([c[0] for c in chunks])


def wait_for_packet(nrf):
    while not nrf.any():
        utime.sleep_ms(_RX_POLL_DELAY)


def recvall(nrf):
    chunks = []

    first = unpack_chunk(nrf.recv())
    chunks.append((first[1], first[2]))

    total_chunks = first[0]
    print(f"{total_chunks=}")
    for i in range(total_chunks - 1):
        wait_for_packet(nrf)
        c = unpack_chunk(nrf.recv())
        print(f"{c[1]=}")
        chunks.append((c[1], c[2]))

    # Check for missing chunks
    # generate range(1, total_chunks), then subtract the chunks we have
    tries = 0
    missing = calc_missing(chunks, total_chunks)
    print(f"{missing=}")
    while len(missing) > 0:
        print(f"Entered loop, tries={tries}")
        if tries == 3:
            print("[!] Too many tries, aborting")
            break

        tries += 1
        # Ask for missing chunks
        nrf.stop_listening()
        nrf.send(struct.pack(f"!{len(missing)}I", *missing))
        nrf.start_listening()
        # Receive missing chunks
        for i in missing:
            c = unpack_chunk(nrf.recv())
            chunks.append((c[1], c[2]))

        missing = calc_missing(chunks, total_chunks)

    nrf.stop_listening()
    nrf.send(struct.pack('!i', -1))
    nrf.start_listening()

    # Sort chunks by index
    chunks.sort(key=lambda x: x[0])
    return b"".join([c[1] for c in chunks])


def send(nrf, data):
    print(f"[*] Sending data: {data}")
    chunks = chunk(data, 8)
    packed_chunks = pack_chunks(chunks)
    print(f"{len(packed_chunks)=} {packed_chunks=}")

    for c in packed_chunks:
        nrf.send(c)

    print("[*] Sent all chunks, waiting for response...")
    nrf.start_listening()

    first = nrf.recv()
    print(f"{first=}")
    unpacked = struct.unpack(f'!i', first)
    print(f"{unpacked=}")

    missing_chunks = unpacked[0]
    if missing_chunks == -1:
        print("[*] No missing chunks")
    else:
        while missing_chunks:
            print(f"[-] Missing chunks: {missing_chunks}")
            nrf.stop_listening()
            for c in [packed_chunks[i-1] for i in missing_chunks]:
                nrf.send(c)
            nrf.start_listening()

            missing_chunks = struct.unpack('!i', nrf.recv())[0]


def initiator():
    nrf = initialise_nrf(18, 19, 16, 13, 17, 16)

    nrf.open_tx_pipe(pipes[0])
    nrf.open_rx_pipe(1, pipes[1])
    nrf.start_listening()
    nrf.stop_listening()

    data = "Hello, world! Lorem ipsum dolor sit amet, consectetur adipiscing elit."

    for _ in range(1000):
        send(nrf, data)
        utime.sleep_ms(15)


def responder():
    nrf = initialise_nrf(18, 19, 16, 13, 17, 16)

    nrf.open_tx_pipe(pipes[1])
    nrf.open_rx_pipe(1, pipes[0])
    nrf.start_listening()

    print("NRF24L01 responder mode, waiting for packets... (ctrl-C to stop)")

    while True:
        if nrf.any():
            data = recvall(nrf)
            print("[*] Received:", data.decode('utf-8'))

import random
import struct

import utime
from machine import Pin, SPI
from micropython import const

from nrf24l01 import NRF24L01

# Responder pause between receiving data and checking for further packets.
_RX_POLL_DELAY = const(10)
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


def wait_for_packet(nrf):
    while not nrf.any():
        utime.sleep_ms(_RX_POLL_DELAY)


def recvall(nrf, packing_format):
    wait_for_packet(nrf)
    data = nrf.recv()
    return struct.unpack(packing_format, data)[0]


def send(nrf, packing_format, data):
    packed_data = struct.pack(packing_format, data)
    nrf.send(packed_data)


def initiator():
    nrf = initialise_nrf(18, 19, 16, 13, 17, 16)

    nrf.open_tx_pipe(pipes[0])
    nrf.open_rx_pipe(1, pipes[1])

    return nrf


def responder():
    nrf = initialise_nrf(18, 19, 16, 13, 17, 16)

    nrf.open_tx_pipe(pipes[1])
    nrf.open_rx_pipe(1, pipes[0])
    nrf.start_listening()

    return nrf


def responder_test():
    nrf = initialise_nrf(18, 19, 16, 13, 17, 16)

    nrf.open_tx_pipe(pipes[1])
    nrf.open_rx_pipe(1, pipes[0])
    nrf.start_listening()

    print("NRF24L01 responder mode, waiting for packets... (ctrl-C to stop)")

    packet_count = 0
    start_time = utime.ticks_ms()
    while True:
        wait_for_packet(nrf)
        data = recvall(nrf, '!d')
        packet_count += 1

        # Calculate time elapsed in seconds
        current_time = utime.ticks_ms()
        elapsed_seconds = (current_time - start_time) // 1000

        # If one second has passed, print the packet count and reset counters
        if elapsed_seconds >= 1:
            print(f"Packets received in the last second: {packet_count}")
            packet_count = 0
            start_time = current_time

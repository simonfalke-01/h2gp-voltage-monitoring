import radio_ng as radio
from machine import Pin

LIGHT_PIN = 7


def main():
    nrf = radio.responder()
    led = Pin(LIGHT_PIN, Pin.OUT)

    try:
        while True:
            radio.wait_for_packet(nrf)
            data = radio.recvall(nrf, '!I')
            led.value(data)
    finally:
        led.value(0)


if __name__ == "__main__":
    main()

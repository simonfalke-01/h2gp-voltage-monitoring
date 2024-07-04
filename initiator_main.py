import radio_ng as radio
from machine import Pin
from picozero import Button

BUTTON_PIN = 6
LIGHT_PIN = 7


def main():
    nrf = radio.initiator()
    button = Button(BUTTON_PIN)
    led = Pin(LIGHT_PIN, Pin.OUT)

    try:
        while True:
            if button.is_active:
                radio.send(nrf, '!I', 1)
                led.value(1)
            else:
                radio.send(nrf, '!I', 0)
                led.value(0)
    finally:
        radio.send(nrf, '!I', 0)
        led.value(0)


if __name__ == "__main__":
    main()

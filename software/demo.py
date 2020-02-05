from __future__ import print_function

import random
import time

import serial
import serial.tools.list_ports

from transport import SerialTransport, EspLinkTransport

from splitflap import Splitflap, MockSplitflap


def run():
    transport = None

    port = ask_for_serial_port()
    if port is not None:
        transport = SerialTransport(port, 38400)
    else:
        esp_link_address = ask_for_esp_link_address()
        if esp_link_address is not None and len(esp_link_address) > 0:
            transport = EspLinkTransport(esp_link_address)

    def show_words(s):
        num_modules = s.get_num_modules()

        with open('words.txt') as word_file:
            words = []

            def char_map(char):
                char = char.lower()
                if not s.is_in_alphabet(char):
                    return ' '
                else:
                    return char

            while True:
                word = word_file.readline()
                if len(word) == 0:
                    break

                word = word.strip()

                if len(word) == num_modules:
                    word = "".join(map(char_map, word))
                    words.append(word)

        while True:
            word = random.choice(words)
            print('Going to {}'.format(word))
            status = s.set_text(word)
            print_status(status)
            time.sleep(4)

    print('Starting...')
    if transport is None:
        show_words(MockSplitflap(12))
    else:
        with transport as t:
            show_words(Splitflap(t))


def ask_for_esp_link_address():
    return input('What is the ESP-link network address? ')


def ask_for_serial_port():
    print('Available ports:')
    ports = sorted(
        filter(
            lambda p: p.description != 'n/a',
            serial.tools.list_ports.comports(),
        ),
        key=lambda p: p.device,
    )
    for i, port in enumerate(ports):
        print('[{: 2}] {} - {}'.format(i, port.device, port.description))
    print()
    value = input('Use which port (or <enter> to specify an ESP-link address)? ')
    if len(value) > 0:
        port_index = int(value)
        assert 0 <= port_index < len(ports)
        return ports[port_index].device
    else:
        return None


def print_status(status):
    for module in status:
        state = ''
        if module['state'] == 'panic':
            state = '!!!!'
        elif module['state'] == 'look_for_home':
            state = '...'
        elif module['state'] == 'sensor_error':
            state = '????'
        elif module['state'] == 'normal':
            state = module['flap']
        print('{:4}  {: 4} {: 4}'.format(state, module['count_missed_home'], module['count_unexpected_home']))


if __name__ == '__main__':
    run()

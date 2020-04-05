import json

_ALPHABET = {
    ' ',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    '.',
    ',',
    '\'',
}

def is_in_alphabet(letter):
    return letter in _ALPHABET

def validate_text(text):
    for letter in text:
        assert is_in_alphabet(letter), 'Unexpected letter: {!r}. Must be one of {!r}'.format(
            letter,
            list(_ALPHABET),
        )


class SplitflapBase(object):
    def __init__(self):
        self._last_status = None
        self._num_modules = None

    # noinspection PyMethodMayBeStatic
    def is_in_alphabet(self, letter):
        return is_in_alphabet(letter)

    def get_status(self):
        return self._last_status

    def get_num_modules(self):
        return self._num_modules

    def set_text(self, text, force_refresh):
        pass

    def clear_text(self):
        text = ''.ljust(self.get_num_modules())
        return self.set_text(text, True)


class MockSplitflap(SplitflapBase):
    def __init__(self, num_modules):
        super().__init__()
        self._num_modules = num_modules
        self._last_status = []

        for module_index in range(0, num_modules):
            status = {
                'state': 'normal',
                'flap': ' ',
                'count_missed_home': 0,
                'count_unexpected_home': 0
            }
            self._last_status.append(status)


    def set_text(self, text, force_refresh):
        print(f'MockSplitflap.set_text (force={force_refresh}): {text}')
        validate_text(text)

        for module_index in range(0, self._num_modules):
            if len(text) > module_index:
                self._last_status[module_index]['flap'] = text[module_index]

        return self._last_status

    def recalibrate_all(self):
        return self._last_status


class Splitflap(SplitflapBase):
    def __init__(self, transport):
        super().__init__()
        self._transport = transport

        self._has_inited = False
        self._num_modules = 0
        self._last_command = None
        self._last_status = None
        self._exception = None

        self._loop_for_status()

    def _loop_for_status(self):
        while True:
            line = self._transport.readline()
            line = line.lstrip('\0').rstrip('\n')
            data = json.loads(line)
            t = data['type']
            if t == 'init':
                if self._has_inited:
                    raise RuntimeError('Unexpected re-init!')
                self._has_inited = True
                self._num_modules = data['num_modules']
            elif t == 'move_echo':
                if not self._has_inited:
                    raise RuntimeError('Got move_echo before init!')
                if self._last_command is None:
                    raise RuntimeError('Unexpected move_echo response from controller')
                if self._last_command != data['dest']:
                    raise RuntimeError('Bad response from controller. Expected {!r} but got {!r}'.format(
                        self._last_command,
                        data['dest'],
                    ))
            elif t == 'status':
                if not self._has_inited:
                    raise RuntimeError('Got status before init!')
                if len(data['modules']) != self._num_modules:
                    raise RuntimeError('Wrong number of modules in status update. Expected {} but got {}'.format(
                        self._num_modules,
                        len(data['modules']),
                    ))
                self._last_status = data['modules']
                return self._last_status
            elif t == 'no_op':
                pass
            else:
                raise RuntimeError('Unexpected message: {!r}'.format(data))

    def _change_text(self, op_code, text):
        validate_text(text)

        self._last_command = text
        self._transport.write('{}{}\n'.format(op_code, text))

        return self._loop_for_status()

    def set_text(self, text, force_refresh):
        if force_refresh:
            return self._change_text('=', text)
        else:
            return self._change_text('+', text)

    def recalibrate_all(self):
        self._transport.write('@')
        return self._loop_for_status()

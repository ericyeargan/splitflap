import os

from flask import Flask
from flask import request
from flask import make_response

from transport import EspLinkTransport
from splitflap import Splitflap


class SplitflapService:
    def __init__(self, splitflap):
        self._current_message = ''
        self._splitflap = splitflap

    def set_message(self, message):
        normal_module_count = 0
        module_statuses = self._splitflap.get_status()
        for module_status in module_statuses:
            if module_status['state'] == "normal":
                normal_module_count += 1

        if normal_module_count == 0:
            raise RuntimeError('all modules in error state')

        def map_to_valid_char(char):
            char = char.lower()
            if not self._splitflap.is_in_alphabet(char):
                return ' '
            else:
                return char

        # convert unsupported characters to spaces
        normalized_message = "".join(map(map_to_valid_char, message))
        # remove redundant spaces
        normalized_message = " ".join(normalized_message.split())
        normalized_message = normalized_message[0: self._splitflap.get_num_modules()]
        module_statuses = self._splitflap.set_text(normalized_message)

        self._current_message = ''
        for module_status in module_statuses:
            self._current_message += (module_status['flap'])

        return self._current_message


transport = EspLinkTransport(os.environ.get('SPLITFLAP_ESP_LINK_HOST'))
transport.open()
splitflap = Splitflap(transport)

service = SplitflapService(splitflap)

app = Flask(__name__)

@app.route('/api/message', methods=['PUT'])
def message():
    m = request.get_data(as_text=True)

    current_message = service.set_message(m)
    return make_response(current_message, 200)

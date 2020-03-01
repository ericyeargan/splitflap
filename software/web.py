import os
import asyncio
import logging

import datetime
from asyncio import CancelledError

from quart import Quart, request, make_response


class SplitflapClock:
    def __init__(self, splitflap):
        self._splitflap = splitflap
        self._clock_task = None
        self._current_text = None

    def select(self):
        pass

    def _on_clock_task_done(self, task):
        try:
            task.exception()
        except CancelledError as e:
            pass
        except Exception as e:
            logging.error(f'exception thrown from clock task: {repr(e)}')

    def enter(self):
        self._clock_task = asyncio.create_task(self._run_clock())
        self._clock_task.add_done_callback(self._on_clock_task_done)
        pass

    async def exit(self):
        if self._clock_task is not None:
            self._clock_task.cancel()
            await self._clock_task
        self._current_text = None

    def _tick(self, force_refresh=False):
        now = datetime.datetime.now()
        text = now.strftime('%m.%H.%M.%S').rjust(self._splitflap.get_num_modules()).lower()

        if text != self._current_text:
            self._current_text = text
            if force_refresh:
                self._splitflap.set_text(text)
            else:
                self._splitflap.update_text(text)

    async def _run_clock(self):
        while True:
            self._tick()
            await asyncio.sleep(0.25)


class SplitflapMessenger:
    def __init__(self, splitflap):
        self._current_message = ''
        self._splitflap = splitflap

    def select(self):
        self._splitflap.clear_text()

    def enter(self):
        pass

    def exit(self):
        pass

    def _check_module_status(self):
        normal_module_count = 0
        module_statuses = self._splitflap.get_status()
        for module_status in module_statuses:
            if module_status['state'] == "normal":
                normal_module_count += 1

        if normal_module_count == 0:
            raise RuntimeError('all modules in error state')

    def _update_current_message(self, module_statuses):
        self._current_message = ''
        for module_status in module_statuses:
            self._current_message += (module_status['flap'])

    def _format_message(self, message):
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
        # pad or trim to width
        normalized_message = normalized_message[0: self._splitflap.get_num_modules()].ljust(self._splitflap.get_num_modules())

        return normalized_message

    def set_message(self, message):
        self._check_module_status()
        self._update_current_message(self._splitflap.set_text(self._format_message(message)))
        return self._current_message

    def update_message(self, message):
        self._check_module_status()
        self._update_current_message(self._splitflap.update_text(self._format_message(message)))
        return self._current_message


def handle_exception(loop, context):
    # context["message"] will always be there; but context["exception"] may not
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.info("Shutting down...")
    asyncio.create_task(shutdown(loop))


if __name__ == '__main__':
    splitflap_host = os.environ.get('SPLITFLAP_ESP_LINK_HOST')
    splitflap_device = os.environ.get('SPLITFLAP_DEV')
    splitflap = None
    if splitflap_host is not None:
        from transport import EspLinkTransport
        from splitflap import Splitflap

        transport = EspLinkTransport(splitflap_host)
        transport.open()
        splitflap = Splitflap(transport)
    elif splitflap_device is not None:
        from transport import SerialTransport
        from splitflap import Splitflap

        transport = SerialTransport(splitflap_device, 38400)
        transport.open()
        splitflap = Splitflap(transport)
    else:
        from splitflap import MockSplitflap

        splitflap = MockSplitflap(12)

    MESSAGE_MODE_NAME = 'message'
    CLOCK_MODE_NAME = 'clock'

    modes = {
        MESSAGE_MODE_NAME: SplitflapMessenger(splitflap),
        CLOCK_MODE_NAME: SplitflapClock(splitflap)
    }

    active_mode = None
    active_mode_name = None

    app = Quart(__name__)

    async def _activate_mode(mode_name):
        global active_mode

        if active_mode_name == mode_name:
            return None

        if mode_name not in modes:
            raise AssertionError('invalid mode name')

        new_mode = modes[mode_name]

        if active_mode is not None:
            exit_task = active_mode.exit()
            if exit_task is not None:
                await exit_task

        active_mode = new_mode
        active_mode.enter()

        return active_mode

    @app.route('/api/mode', methods=['PUT'])
    async def select_mode():
        mode_name = await request.get_data()
        new_mode = await _activate_mode(mode_name.decode("utf-8"))
        if new_mode is not None:
            new_mode.select()

        return await make_response(mode_name, 200)

    @app.route('/api/message', methods=['PUT', 'POST', 'GET'])
    async def api_message_request():
        m = await request.get_data()

        if active_mode_name != MESSAGE_MODE_NAME:
            await _activate_mode(MESSAGE_MODE_NAME)

        message_text = m.decode("utf-8")

        if request.method == 'PUT':
            current_message = active_mode.set_message(message_text)
        elif request.method == 'POST':
            current_message = active_mode.update_message(message_text)
        elif request.methd == 'GET':
            current_message = active_mode.get_message()
        else:
            raise(AssertionError('unexpected request type'))

        return await make_response(current_message, 200)



    app.run()

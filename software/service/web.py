import os
import asyncio
import logging
import datetime
from asyncio import CancelledError, shield

from quart import Quart, request, make_response

from quart_cors import cors

from service.message_formatter import MessageFormatter


class SplitflapClock:
    def __init__(self, splitflap):
        self._splitflap = splitflap
        self._clock_task = None
        self._current_text = None

    def select(self):
        pass

    @staticmethod
    def _on_clock_task_done(task):
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

    async def _run_clock(self):
        while True:
            now = datetime.datetime.now()
            text = now.strftime('%m.%H.%M.%S').rjust(self._splitflap.get_num_modules()).lower()
            if text != self._current_text:
                self._current_text = text
                if False:
                    self._splitflap.set_text(text)
                else:
                    self._splitflap.update_text(text)
            await asyncio.sleep(0.25)


class SplitflapMessenger:
    def __init__(self, splitflap):
        self._splitflap = splitflap
        self._formatter = MessageFormatter(self._splitflap.get_num_modules(),
                                           lambda char: self._splitflap.is_in_alphabet(char))
        self._message_task = None
        self._message_task_cancel = False
        self._force_refresh = False
        self._message_text = ''

    def select(self):
        self._splitflap.clear_text()

    def enter(self):
        pass

    def exit(self):
        if self._message_task is not None:
            self._message_task_cancel = True

    def _check_module_status(self):
        normal_module_count = 0
        module_statuses = self._splitflap.get_status()
        for module_status in module_statuses:
            if module_status['state'] == "normal":
                normal_module_count += 1

        if normal_module_count == 0:
            raise RuntimeError('all modules in error state')

    def _on_display_message_task_done(self, task):
        self._message_task = None
        # noinspection PyBroadException
        try:
            task.exception()
        except CancelledError as e:
            pass
        except Exception as e:
            logging.error(f'exception thrown from clock task: {repr(e)}')

    async def _display_message(self, message):
        for line in message:
            if self._message_task_cancel:
                return

            self._check_module_status()
            self._splitflap.set_text(line, self._force_refresh)
            await asyncio.sleep(2)

    async def set_message(self, message, force_refresh):
        if self._message_task is not None:
            # since we've shielded our task from cancellation, set the cancel flag and wait for it to complete
            # TODO: this means that we may have to wait up to the inter-line interval before we can set the message
            self._message_task_cancel = True
            await self._message_task

        self._check_module_status()

        message = self._formatter.format(message)

        self._message_task_cancel = False
        # need to shield so that the task doesn't get canceled with the request
        self._message_task = shield(asyncio.create_task(self._display_message(message)))
        self._message_task.add_done_callback(self._on_display_message_task_done)

        self._message_text = '\n'.join(message).upper() + '\n'
        self._force_refresh = force_refresh

        return self._message_text

    def get_message(self):
        return self._message_text


if __name__ == '__main__':
    splitflap_host = os.environ.get('SPLITFLAP_ESP_LINK_HOST')
    splitflap_device = os.environ.get('SPLITFLAP_DEV')
    splitflap = None
    if splitflap_host is not None:
        from splitflap.transport import EspLinkTransport
        from splitflap.splitflap import Splitflap

        print(f'connecting to ESP-Link at address: {splitflap_host}' )

        transport = EspLinkTransport(splitflap_host)
        transport.open()
        splitflap = Splitflap(transport)
    elif splitflap_device is not None:
        from splitflap.transport import SerialTransport
        from splitflap.splitflap import Splitflap

        print(f'connecting to serial port: {splitflap_device}' )

        transport = SerialTransport(splitflap_device, 38400)
        transport.open()
        splitflap = Splitflap(transport)
    else:
        from splitflap.splitflap import MockSplitflap

        print(f'using mock splitflap' )

        splitflap = MockSplitflap(12)

    MESSAGE_MODE_NAME = 'message'
    CLOCK_MODE_NAME = 'clock'

    modes = {
        MESSAGE_MODE_NAME: SplitflapMessenger(splitflap),
        CLOCK_MODE_NAME: SplitflapClock(splitflap)
    }

    active_mode = None
    active_mode_name = None

    app = Quart(__name__, static_url_path='', static_folder=os.environ.get('WEBAPP_BUILD_PATH'))
    app = cors(app, allow_origin="*")

    async def _activate_mode(mode_name):
        global active_mode
        global active_mode_name

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
        active_mode_name = mode_name

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
            current_message = await active_mode.set_message(message_text, True)
        elif request.method == 'POST':
            current_message = await active_mode.set_message(message_text, False)
        elif request.method == 'GET':
            current_message = active_mode.get_message()
        else:
            raise(AssertionError('unexpected request type'))

        return await make_response(current_message, 200)

    app.run(host='0.0.0.0')

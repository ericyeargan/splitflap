import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from service.message_formatter import MessageFormatter


def is_valid_char(char):
    if char == '@':
        return False
    return True


class MessageFormatterTestCase(unittest.TestCase):
    def setUp(self):
        self._formatter = MessageFormatter(4, is_valid_char)

    def test_padding(self):
        lines = self._formatter.format('foo')
        self.assertEqual(1, len(lines))
        self.assertEqual('foo ', lines[0])

    def test_invalid_char_replacement(self):
        lines = self._formatter.format('foo@')
        self.assertEqual(1, len(lines))
        self.assertEqual('foo ', lines[0])

    def test_lower_cased(self):
        lines = self._formatter.format('FOO')
        self.assertEqual(1, len(lines))
        self.assertEqual('foo ', lines[0])

    def test_redundant_spaces_removed(self):
        lines = self._formatter.format('f  o')
        self.assertEqual(1, len(lines))
        self.assertEqual('f o ', lines[0])

    def test_break_on_newline(self):
        lines = self._formatter.format('fo\nob')
        self.assertEqual(2, len(lines))
        self.assertEqual('fo  ', lines[0])
        self.assertEqual('ob  ', lines[1])

    def test_break_on_space(self):
        lines = self._formatter.format('foo bar')
        self.assertEqual(2, len(lines))
        self.assertEqual('foo ', lines[0])
        self.assertEqual('bar ', lines[1])

    def test_break_on_space_and_newline(self):
        lines = self._formatter.format('foo\nbar baz')
        self.assertEqual(3, len(lines))
        self.assertEqual('foo ', lines[0])
        self.assertEqual('bar ', lines[1])
        self.assertEqual('baz ', lines[2])

    def test_single_word_break(self):
        # lines = self._formatter.format('foobar')
        # self.assertEqual(
        #     ['foob', 'ar  '],
        #     lines)

        lines = self._formatter.format('fo foobar')
        self.assertEqual(
            ['fo f', 'ooba', 'r   '],
            lines)


if __name__ == '__main__':
    unittest.main()
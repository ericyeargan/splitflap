import re
from collections import deque


class MessageFormatter:
    def __init__(self, line_length, char_validator_func):
        self._line_length = line_length
        self._char_validator_func = char_validator_func

    def _break_line(self, line):
        # break on newlines
        lines = line.split('\n')

        broken_lines = []

        for line in lines:
            if len(line) <= self._line_length:
                broken_lines.append(line)
            else:
                words = deque(line.split(' '))
                line = ''
                word = words.popleft()
                while word is not None:
                    if len(word) > self._line_length:
                        if len(line) > 0:
                            line += ' '

                        break_index = self._line_length - len(line)
                        first_part = word[0: break_index]
                        second_part = word[break_index:]
                        line += first_part
                        broken_lines.append(line)
                        line = ''
                        word = second_part
                    else:
                        if len(line) + len(word) <= self._line_length:
                            if len(line) > 0:
                                line += ' '
                            line += word
                        else:
                            broken_lines.append(line)
                            line = word

                        if len(words) > 0:
                            word = words.popleft()
                        else:
                            word = None

                if len(line) > 0:
                    broken_lines.append(line)

        return broken_lines

    def format(self, message):
        def map_to_valid_char(char):
            char = char.lower()
            if not self._char_validator_func(char):
                return ' '
            else:
                return char

        # convert unsupported characters to spaces
        normalized_message = "".join(map(map_to_valid_char, message))
        # remove redundant spaces
        normalized_message = re.sub("\s\s+", " ", normalized_message)

        # split = normalized_message.split(' ')
        # normalized_message = ' '.join(split)

        lines = self._break_line(normalized_message)

        # pad to width
        for i in range(0, len(lines)):
            lines[i] = lines[i][0: self._line_length].ljust(self._line_length)

        return lines

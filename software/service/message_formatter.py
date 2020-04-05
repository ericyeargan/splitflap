import re
from collections import deque


class MessageFormatter:
    def __init__(self, line_length, char_validator_func):
        self._line_length = line_length
        self._char_validator_func = char_validator_func

    def _break_line(self, line):
        broken_lines = []

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
                    if len(line) + len(word) < self._line_length:
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
        # break on newlines
        lines = message.split('\n')

        formatted_lines = []

        for line in lines:
            leading_colon = False
            trailing_colon = False

            if len(line) > 0:
                if line[0] is ':':
                    leading_colon = True
                    line = line[1:]
                if line[-1] is ':':
                    trailing_colon = True
                    line = line[:-1]

            def map_to_valid_char(char):
                char = char.lower()
                if not self._char_validator_func(char):
                    return ' '
                else:
                    return char

            # convert unsupported characters to spaces
            normalized_line = "".join(map(map_to_valid_char, line))
            # remove redundant spaces
            normalized_line = re.sub("\s\s+", " ", normalized_line)

            broken_lines = self._break_line(normalized_line)

            # pad to width
            for i in range(0, len(broken_lines)):
                trimmed_line = broken_lines[i][0: self._line_length]
                if leading_colon and not trailing_colon:
                    broken_lines[i] = trimmed_line.rjust(self._line_length)
                elif leading_colon and trailing_colon:
                    broken_lines[i] = trimmed_line.center(self._line_length)
                else:
                    broken_lines[i] = trimmed_line.ljust(self._line_length)

            formatted_lines.extend(broken_lines)

        return formatted_lines

# coding: utf-8

from __future__ import unicode_literals

import random
import re
from pprint import pprint

import numpy as np
from transliterate import translit

EMPTY = 0
SHIP = 1
BLOCKED = 2
HIT = 3
MISS = 4

EDGE = -1 #(-1 100)

SEARCH = 1
HUNT = 2

HORIZONTAL = 1
VERTICAL = 2



class BaseGame(object):
    position_patterns = [re.compile('^([a-zа-я]+)(\d+)$', re.UNICODE),  # a1
                         re.compile('^([a-zа-я]+)\s+(\w+)$', re.UNICODE),  # a 1; a один
                         re.compile('^(\w+)\s+(\w+)$', re.UNICODE),  # a 1; a один; 7 10
                         ]

    str_letters = ['а', 'б', 'в', 'г', 'д', 'е', 'ж', 'з', 'и', 'к']
    str_numbers = ['один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять', 'десять']

    letters_mapping = {
        'the': 'з',
        'за': 'з',
        'уже': 'ж',
        'трень': '3',
    }

    default_ships = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]

    def __init__(self):
        self.size = 0
        self.ships = None
        self.field = []




        self.ships_count = 0

        self.mode = SEARCH
        self.enemy_direction = None
        self.enemy_field = []
        self.enemy_ships_count = 0
        self.enemy_ships = {4:1, 3:2, 2:3, 1:4}
        self.enemy_cur_ship = []

        self.last_shot_position = None
        self.last_enemy_shot_position = None
        self.numbers = None

    def start_new_game(self, size=10, field=None, ships=None, numbers=None):
        assert(size <= 10)
        assert(len(field) == size ** 2 if field is not None else True)

        self.size = size
        self.numbers = numbers if numbers is not None else False

        if ships is None:
            self.ships = self.default_ships
        else:
            self.ships = ships

        if field is None:
            self.generate_field()
        else:
            self.field = field

        self.enemy_field = [EMPTY] * self.size ** 2

        self.ships_count = self.enemy_ships_count = len(self.ships)

        self.last_shot_position = None
        self.last_enemy_shot_position = None




        self.mode = SEARCH
        self.enemy_direction = None
        self.enemy_ships = {4:1, 3:2, 2:3, 1:4}
        self.enemy_cur_ship = []



    def generate_field(self):
        raise NotImplementedError()

    def move_right(self, index):
        new_index = index + 1
        if index / self.size == new_index / self.size:
            if self.check_enemy_index(new_index):
                return new_index


    def move_left(self, index):
        new_index = index - 1
        if index / self.size == new_index / self.size:
            if self.check_enemy_index(new_index):
                return new_index

    def move_up(self, index):
        new_index = index - 10
        if new_index >= 0:
            if self.check_enemy_index(new_index):
                return new_index

    def move_down(self, index):
        new_index = index + 10
        if new_index <= self.size**2 - 1:
            if self.check_enemy_index(new_index):
                return new_index

    def print_field(self):
        mapping = ['0', '1', 'x']

        print '-' * (self.size + 2)
        for y in range(self.size):
            print '|%s|' % ''.join(mapping[x] for x in self.field[y * self.size: (y + 1) * self.size])
        print '-' * (self.size + 2)

    def handle_enemy_shot(self, position):
        index = self.calc_index(position)

        if self.field[index] in (SHIP, HIT):
            self.field[index] = HIT

            if self.is_dead_ship(index):
                self.ships_count -= 1
                return 'kill'
            else:
                return 'hit'
        else:
            return 'miss'

    def is_dead_ship(self, last_index):
        x, y = self.calc_position(last_index)
        x -= 1
        y -= 1

        def _line_is_dead(line, index):
            def _tail_is_dead(tail):
                for i in tail:
                    if i == HIT:
                        continue
                    elif i == SHIP:
                        return False
                    else:
                        return True
                return True

            return _tail_is_dead(line[index:]) and _tail_is_dead(line[index::-1])

        return (
            _line_is_dead(self.field[x::self.size], y) and
            _line_is_dead(self.field[y * self.size:(y + 1) * self.size], x)
        )

    def is_end_game(self):
        return self.is_victory() or self.is_defeat()

    def is_victory(self):
        return self.enemy_ships_count < 1

    def is_defeat(self):
        return self.ships_count < 1

    def do_shot(self):
        raise NotImplementedError()

    def repeat(self):
        return self.convert_from_position(self.last_shot_position, numbers=True)

    def reset_last_shot(self):
        self.last_shot_position = None

    def handle_enemy_reply(self, message):
        if self.last_shot_position is None:
            return

        index = self.calc_index(self.last_shot_position)
        if message in ['hit', 'kill']:
            self.enemy_field[index] = SHIP
            self.enemy_cur_ship.append(self.last_shot_position)

        if message == 'kill':
            self.enemy_ships_count -= 1
            self._add_blocked()
            self.enemy_cur_ship = []
            self.mode = SEARCH
            self.enemy_direction = None

        elif message == 'hit':
            self.set_enemy_direction()
            self.mode = HUNT

        elif message == 'miss':
            self.enemy_field[index] = MISS

    def set_enemy_direction(self):
        if not self.enemy_direction:
            if abs(self.enemy_cur_ship[0] - self.enemy_cur_ship[1]) == 1:
                self.enemy_direction = HORIZONTAL
            else:
                self.enemy_direction = VERTICAL

    def _add_blocked(self):
        for point in self.enemy_cur_ship:
            for shift in [1, -1, 10, -10]:
                shifted = shift + point
                if self.check_enemy_index(shifted):
                        self.enemy_field[shifted] = BLOCKED

    def calc_index(self, position):
        x, y = position

        if x > self.size or y > self.size:
            raise ValueError('Wrong position: %s %s' % (x, y))

        return (y - 1) * self.size + x - 1

    def check_enemy_index(self, index):
        if 0 <= index <= self.size**2 - 1 and self.enemy_field[index] == EMPTY:
                return True
        else:
            return False

    def calc_position(self, index):
        y = index / self.size + 1
        x = index % self.size + 1

        return x, y

    def convert_to_position(self, position):
        position = position.lower()
        for pattern in self.position_patterns:
            match = pattern.match(position)

            if match is not None:
                break
        else:
            raise ValueError('Can\'t parse entire position: %s' % position)

        bits = match.groups()

        def _try_letter(bit):
            # проверяем особые случаи неправильного распознования STT
            bit = self.letters_mapping.get(bit, bit)

            # преобразуем в кириллицу
            bit = translit(bit, 'ru')

            try:
                return self.str_letters.index(bit) + 1
            except ValueError:
                raise

        def _try_number(bit):
            # проверяем особые случаи неправильного распознования STT
            bit = self.letters_mapping.get(bit, bit)

            if bit.isdigit():
                return int(bit)
            else:
                try:
                    return self.str_numbers.index(bit) + 1
                except ValueError:
                    raise

        x = bits[0].strip()
        try:
            x = _try_letter(x)
        except ValueError:
            try:
                x = _try_number(x)
            except ValueError:
                raise ValueError('Can\'t parse X point: %s' % x)

        y = bits[1].strip()
        try:
            y = _try_number(y)
        except ValueError:
            raise ValueError('Can\'t parse Y point: %s' % y)

        return x, y

    def convert_from_position(self, position, numbers=None):
        numbers = numbers if numbers is not None else self.numbers

        if numbers:
            x = position[0]
        else:
            x = self.str_letters[position[0] - 1]

        y = position[1]

        return '%s, %s' % (x, y)


class Game(BaseGame):
    """Реализация игры с ипользованием обычного random"""

    def generate_field(self):
        """Метод генерации поля"""
        self.field = [0] * self.size ** 2

        for length in self.ships:
            self.place_ship(length)

        for i in range(len(self.field)):
            if self.field[i] == BLOCKED:
                self.field[i] = EMPTY

    def place_ship(self, length):

        def _try_to_place(index=None):
            if length == 1:
                x = random.randint(1, self.size)
                y = random.randint(1, self.size)

                direction = random.choice([1, self.size])

                index = self.calc_index((x, y))
            else:
                if index < self.size ** 2 / 2:
                    index = index + 1
                else:
                    index = index - 1
                ##################self.check_index(index)
                direction = 1
                ##################

            values = self.field[index:None if direction != 1 else index + self.size - index % self.size:direction][
                     :length]

            if len(values) < length or any(values):
                return False, index

            for i in range(0, length):
                current_index = index + direction * i

                for j in [0, 1, -1]:
                    if (current_index % self.size in (0, self.size - 1)
                        and (current_index + j) % self.size in (0, self.size - 1)):
                        continue

                    for k in [0, self.size, -self.size]:
                        neighbour_index = current_index + k + j

                        if (neighbour_index < 0
                            or neighbour_index >= len(self.field)
                            or self.field[neighbour_index] == SHIP):
                            continue

                        self.field[neighbour_index] = BLOCKED

                self.field[current_index] = SHIP

            return True, index

        index = EDGE
        while 1:
            result, index = _try_to_place(index)
            if result:
                break

    def predict_enemy_ships(self, ship_size):
        field = []
        valid_ships = []

        ship_normalized = [(x * self.size) for x  in range(ship_size)]
        for j in range(self.size):
            last_in_line = (self.size - 1) * self.size + j
            for i in range(self.size):
                index = i * self.size + j
                valid_ship = self._get_ship(index, last_in_line, ship_size, ship_normalized)
                if valid_ship:
                    valid_ships.append(valid_ship)

        ship_normalized = range(ship_size)

        for i in range(self.size):
            last_in_line = (i+1) * self.size
            for j in range(self.size):
                index = i * self.size + j
                valid_ship = self._get_ship(index, last_in_line, ship_size, ship_normalized)
                if valid_ship:
                    valid_ships.append(valid_ship)

        return valid_ships

    def _get_ship(self, index, last_in_line, ship_size, ship_parts):
        valid_ship = []
        valid_ship = []
        for ship_part in ship_parts:
            ship_index = index + ship_part
            if self.check_enemy_index(index) and \
                            ship_index < last_in_line:  # EMPTY
                valid_ship.append(ship_index)
            else:
                valid_ship = []
        return valid_ship


    def get_cumulative_value(self, index, predicted_ships):
        cum = 0
        for ship in predicted_ships:
            if index in ship:
                cum += 1
        return cum


    def get_max_prob_move(self, ship_size):
        predicted_ships = self.predict_enemy_ships(ship_size=ship_size)
        cum_values = []
        if predicted_ships:
            for index in range(self.size ** 2 - 1):
                if self.enemy_field[index] == 0:
                    cum_values.append(self.get_cumulative_value(index, predicted_ships))
            cum_values = np.array(cum_values)
            max_index = cum_values.argmax()
            # if max_indexs:
            #     m = max_indexs[0]

            return max_index
        else:
            print("no moves")

    def hunt(self, direction):
        if direction == VERTICAL:
            index = self.move_down(self.last_shot_position)
            if index == None:
                index = self.move_up(self.last_shot_position)
        if direction == HORIZONTAL:
                index = self.move_left(self.last_shot_position)
                if index == None:
                    index = self.move_right(self.last_shot_position)
        if direction == None:
            index = self.move_down(self.last_shot_position)
            if index == None:
                index = self.move_up(self.last_shot_position)
            if index == None:
                index = self.move_left(self.last_shot_position)
            if index == None:
                index = self.move_right(self.last_shot_position)
        return index

    def do_shot(self):
        # EMPTY = 0
        # SHIP = 1
        # BLOCKED = 2
        # HIT = 3
        # MISS = 4
        """Метод выбора координаты выстрела.

        """
        if self.mode == SEARCH:
            ship_size = max(filter(lambda x: self.enemy_ships[x] > 0, self.enemy_ships.keys()))
            index = self.get_max_prob_move(ship_size)
        else:  # HUNT!
            index = self.hunt(self.enemy_direction)

        print("NEWINDEX", index)

        # index = random.choice([i for i, v in enumerate(self.enemy_field) if v == EMPTY])
        #
        self.last_shot_position = self.calc_position(index)
        return self.convert_from_position(self.last_shot_position)

# #
# if __name__ == "__main__":
#     g = Game()
#     g.start_new_game()
#     g.generate_field()
#     g.print_field()
#
#
#     g.mode = SEARCH
#     print("newpos={}".format(g.do_shot()))
#     #
#     # g.mode = HUNT
#     # g.enemy_direction = HORIZONTAL
#     # g.enemy_ships_count = 0
#     # g.enemy_ships = {4: 1, 3: 2, 2: 3, 1: 4}
#     # g.enemy_cur_ship = [35]
#     #
#     # g.last_shot_position = 35
#     #
#     #
#     #
#     #
#     # print(g.do_shot())
#     #print(g.do_shot())

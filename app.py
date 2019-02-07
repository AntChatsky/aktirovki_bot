# -*- coding: UTF-8 -*-.

import time
from time import localtime
import re
from random import randrange
import logging
import logging.config
import vk_api
from vk_api.vk_api import VkApiMethod
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from get_info import get_
from DO_NOT_PUSH_TO_GIT import vk_token, admin_id


class Container(object):
    def __init__(self, file_path):
        self.file_path = file_path
        self.storage = self.get_variables()

    def get_variables(self) -> list:
        """
        Read variables from file, which path was given in declaration
        of Container object.
        """
        result = []
        with open(self.file_path, "r") as f:
            for line in f:
                if line[-1:] == "\n":
                    result.append(line[:-1])
                else:
                    result.append(line)

        return result

    def add(self, item) -> bool:
        """
        Adds new string with variable to the file.
        """
        # TODO Use SQLite database
        string = str(item)

        # If item hadn't been added before
        if string not in self.storage:
            with open(self.file_path, "a") as f:
                f.write(string + "\n")

            self.storage.append(str(item))

            return True

        else:
            return False

    def delete(self, item):
        """
        Deletes string from file and storage.
        """
        string = str(item)

        with open(self.file_path, "r+") as f:
            lines = f.readlines()
            f.seek(0)

            i = 0
            for line in lines:
                if line != "":
                    if string not in line:
                        f.write(line)
                        i += 1

                    else:
                        self.storage.pop(i)

            f.truncate()

    def includes(self, item) -> bool:
        """
        Checks every storage cell for a given item.
        :param item:
        :return:
        """
        for i in self.storage:
            if str(item) in i:
                return True
        return False

    def __len__(self):
        return len(self.storage)

    def __getitem__(self, i):
        return self.storage[i]

    def __iter__(self):
        yield from self.storage

    def __bool__(self):
        if self.storage:
            return True

        return False


class Bot(object):
    def __init__(self, vk_session):
        self.logger_root = logging.getLogger("bot")
        self.logger_root.info("Bot was created")

        self.logger_messages = logging.getLogger("messages")

        self.vk_session = vk_session
        self.vk = self.vk_session.get_api()

        self.vk_methods = VkApiMethod(self.vk)

        self.longpoll = VkLongPoll(self.vk_session)

        self.peer_container = Container("containers/peer.txt")

        self.months = ["января", "февраля", "марта", "апреля", "мая",
                       "июня", "июля", "августа", "сентября", "октября",
                       "ноября", "декабря"]
        self.shifts = {"Первая смена": "1", "Вторая смена": "2"}

        self.irrelevant_data_message = "Нет актуальной информации. Попробуй " \
                                       "проверить позже, она обновляется в " \
                                       "6 и 11 часов до полудня."

        self.help_message = "Хочешь воспользоваться моими командами? Выбери " \
                            "одну из них при помощи клавиатуры или напиши " \
                            'мне "список команд".'

        self.list_of_commands = "Напиши мне команду, чтобы " \
                                "воспользоваться ей. \n" \
                                "Cписок и описание моих команд:\n" \
                                '"Получать уведомления"' \
                                "- я предложу вам выбрать смену, в " \
                                "которой вы обучаетесь, чтобы информировать " \
                                "вас об актировках при появлении информации " \
                                "о них.\n" \
                                '"Больше не получать"' \
                                "- я больше не буду присылать вам " \
                                "уведомления 😢😢😢\n" \
                                '"Актуальная информация"' \
                                "- я сообщу вам самую свежую информацию об " \
                                "актировках сегодня для обоих смен."

        self.last_update = []

        self.messages_callback = {"Получать уведомления об актировках":
                                      self.get_shift,
                                  "Получать уведомления": self.get_shift,
                                  "Первая смена": self.add_to_inform,
                                  "Вторая смена": self.add_to_inform,
                                  "Больше не получать уведомления":
                                      self.exclude_from_informing,
                                  "Больше не получать":
                                      self.exclude_from_informing,
                                  "Актуальная информация": self.inform_event
                                  }
        self.messages_answers = {"Список команд": self.list_of_commands}

        self.messages_callback = {self.text_processing(key): value
                                  for key, value
                                  in self.messages_callback.items()}

        self.messages_answers = {self.text_processing(key): value
                                 for key, value
                                 in self.messages_answers.items()}

    def listen(self):
        """
        Checks every event which bot can get, answers on messages
        """
        for event in self.longpoll.check():
            if event.type == VkEventType.MESSAGE_NEW and event.text \
                    and event.to_me:
                self.logger_messages.info(
                    "New message from %s" % str(event.peer_id))

                text = self.text_processing(event.text)

                if text in self.messages_callback:
                    self.messages_callback[text](event)
                elif text in self.messages_answers:
                    self.send_message(event, self.messages_answers[text])
                else:
                    self.help(event)

    def send_message(self, event, text):
        try:
            self.vk.messages.send(
                peer_id=event.peer_id,
                message=text,
                random_id=self.get_random_id()
            )

        except Exception as exception:
            self.emergency(exception)

    def send_keyboard(self, event, message_, keyboard_):
        try:
            self.vk.messages.send(
                peer_id=event.peer_id,
                message=message_,
                keyboard=keyboard_,
                random_id=self.get_random_id()
            )

        except Exception as exception:
            self.emergency(exception)

    def help(self, event):
        """
        Sends user keyboard with main commands.
        """
        keyboard_ = VkKeyboard(one_time=False)

        keyboard_.add_button("Получать уведомления об актировках",
                             color=VkKeyboardColor.PRIMARY)

        keyboard_.add_line()
        keyboard_.add_button("Больше не получать уведомления")

        keyboard_.add_line()
        keyboard_.add_button("Актуальная информация",
                             color=VkKeyboardColor.PRIMARY)

        self.send_keyboard(event, self.help_message, keyboard_.get_keyboard())

    def get_shift(self, event):
        keyboard_ = VkKeyboard(one_time=True)
        keyboard_.add_button("Первая смена")
        keyboard_.add_button("Вторая смена", color=VkKeyboardColor.PRIMARY)

        self.send_keyboard(event, "Выбери смену, в которой ты учишься",
                           keyboard_.get_keyboard())

    def add_to_inform(self, event):
        """
        Adds chat's or user's id to container file.
        """
        self.logger_messages.info("Attempt. Add user to inform list")

        success_message = """Теперь вы будете получать уведомления об 
        актировках."""
        decline_message = """Вы уже получаете уведомления об 
        актировках."""

        request = str(event.peer_id) + " " + self.shifts[event.text]
        if request not in self.peer_container:
            self.logger_messages.info("The attempt was successful.")
            self.peer_container.add(request)
            self.send_message(event, success_message)

        else:
            self.logger_messages.info("Declined.")
            self.send_message(event, decline_message)

    def inform(self, update, shift):
        """
        Sends information message to every user/chat who/which had subscribed.
        """
        self.logger_root.info("Informing %s shift." % str(shift))

        if shift:
            date = update[0]
            date[1] = self.months[date[1] - 1]
            date = " ".join([str(i) for i in date])

            for item in self.peer_container:
                user = [int(i) for i in item.split()]
                user = {"id": user[0], "shift": user[1]}

                if user["shift"] == shift:
                    # Prevents sending message to user, who has banned bot
                    try:
                        self.vk.messages.send(
                            peer_id=user["id"],
                            message=date + "\n" + update[shift],
                            random_id=self.get_random_id()
                        )

                    except vk_api.ApiError as exception:
                        self.logger_root.error(
                            msg="Error: %s\n"
                                "User was excluded "
                                "from informing" % exception.__str__())

                        # If user has banned bot, deletes his if from storage
                        self.peer_container.delete(user["id"])
                        continue

    def inform_event(self, event):
        """
        Sends information message for one certain user/chat.
        """
        self.logger_messages.info("Information was requested")
        date = self.last_update[0] if self.last_update else False

        flag = False
        if [localtime()[2], localtime()[1]] == date:
            flag = True

        # If information is relevant
        if flag:
            """
            Message:
            1. <1st shift text>
            2. <2nd shift text>
            """
            message = self.last_update[1] + "\n" + self.last_update[2]
            self.send_message(event, message)

        else:
            self.send_message(event, self.irrelevant_data_message)

    def exclude_from_informing(self, event):
        """
        Delete chat's or user's id from container file.
        """
        self.logger_messages.info("User was excluded from informing")

        success_message = "Вы больше не будете получать уведомления об " \
                          "актировках."
        decline_message = "Вы и так не получаете уведомления."

        if self.peer_container.includes(event.peer_id):
            self.peer_container.delete(event.peer_id)
            self.send_message(event, success_message)

        else:
            self.send_message(event, decline_message)

    def emergency(self, exception):
        """
        Sends emergency message to the creator.
        Also prints it and writes in file
        """
        self.logger_root.error(logging.exception(exception=exception,
                                                 msg=" "))

        self.vk.messages.send(
            user_id=admin_id,
            message="Помоги своему чаду! Всё сломалось! "
                    "Вот тип ошибки: "
                    "{err_type}\n Вот сообщение ошибки:{err_msg}".format(
                     err_type=type(exception).__name__,
                     err_msg=exception.__str__()),
            random_id=self.get_random_id()
        )

    @staticmethod
    def get_random_id():
        return randrange(0, 10**6)

    @staticmethod
    def key_by_value(dictionary, value):
        """
        If the dictionary contains two and more keys linked with given value,
        function returns first key.
        :return: key
        """

        return list(dictionary.keys())[list(dictionary.values()).index(value)]

    @staticmethod
    def text_processing(text):
        """
        Deletes spaces and punctuation marks from given text and
        :return: processed text
        """
        punctuation_marks = [".", ",", "-", "_", "!", "?", ";", ":", "'", '"']

        text = text.lower()
        # Delete spaces from lowercase text
        text = text.replace(" ", "")

        for mark in punctuation_marks:
            text = text.replace(mark, "")

        return text


class Manager(object):
    def __init__(self, vk_session):
        self.logger = logging.getLogger("manager")
        self.logger.info("Manager was created")

        self.bot = Bot(vk_session)

        # Time, when info does update in hours
        self.first_shift_time = 6
        # Same time, but in minutes
        self.first_shift_time *= 60
        self.first_shift_update = False

        self.second_shift_time = 11
        self.second_shift_time *= 60
        self.second_shift_update = False

        self.last_iteration_time = 0

        # This phrase must be in update's text to pass check
        self.key_phrase = "отменяются"

    def hold(self):
        """
        Function, which contains main loop
        """
        try:
            while True:
                # If day have passed
                if localtime()[3] == 0:
                    # Updates every flag
                    self.first_shift_update = False
                    self.second_shift_update = False

                self.check_updates()
                self.bot.listen()

        except Exception as exception:
            self.bot.emergency(exception)

            self.hold()

    def check_updates(self):
        """
        If it's time to check, checks website with demanded information
        for any updates. If they do exist, it transfers them to bot.
        """
        # If bot doesn't have any information
        if not self.bot.last_update:
            date, shift1, shift2 = get_()
            date = self.process_date(date)

            shift1 = self.check_data(date, shift1, shift=1)
            shift2 = self.check_data(date, shift2, shift=2)

            if not shift1:
                shift1 = "Первая смена: " + self.bot.irrelevant_data_message
            if not shift2:
                shift2 = "Вторая смена: " + self.bot.irrelevant_data_message

            # If anything, expect boolean 0 was returned from function
            if date:
                self.logger.info("Bot 'last_updates' array was filled")

                self.bot.last_update = [date, shift1, shift2]

        # Variable, which contains real time in minutes
        time_now = localtime()[3] * 60 + localtime()[4]

        # If one minute passed
        if (time_now - self.last_iteration_time) >= 1:
            # Updates iterator
            self.last_iteration_time = time_now

            # If data hasn't updated yet
            if not self.first_shift_update \
                    and (self.first_shift_time - time_now) < 30 \
                    and (time_now - self.first_shift_time) < 30:
                self.logger.info("Update first shift information attempt")

                date, shift1, shift2 = get_()

                date = self.process_date(date)
                shift1 = self.check_data(date, shift1, shift=1)

                # If anything, except False was returned
                if date and shift1:
                    self.logger.info("The attempt was successful. Data: %s"
                                     % shift1)

                    # Updates flag
                    self.first_shift_update = True

                    self.bot.inform([date, shift1, False], shift=1)
                    self.bot.last_update[1] = shift1

            if not self.second_shift_update \
                    and (self.second_shift_time - time_now < 30) \
                    and (time_now - self.second_shift_time < 30):
                self.logger.info("Update second shift information attempt")

                date, shift1, shift2 = get_()

                date = self.process_date(date)
                shift2 = self.check_data(date, shift2, shift=2)

                # If anything, except False was returned
                if date and shift2:
                    self.logger.info("The attempt was successful. Data: %s"
                                     % shift1)

                    # Updates flag
                    self.second_shift_update = True

                    self.bot.inform([date, False, shift2], shift=2)
                    self.bot.last_update[2] = shift2

    def check_data(self, date, text, shift):
        """
        Checks data, which was read from website by several criteria.
        Returns processed data if data is correct, boolean 0
        for every incoming variable if it's incorrect.
        """
        # Given date must contain [Day of the week, date]
        if not date:
            return False

        # 0: day, 1: month
        date_now = [localtime()[2], localtime()[1]]

        # Compares real date with date given as an argument
        # and checks the text for the key phrase
        if date_now == date and self.key_phrase in text:
            from_, to = re.findall("\d{1,2}", text)

            text = "Первая смена" if shift == 1 else "Вторая смена"
            text += ": занятия отменяются с " \
                    + from_ + " до " + to + " класса."

            return text

        return False

    @staticmethod
    def process_date(date):
        """
        :param date: <day of the week>, day.month.year
        :return: list(day, month)
        """
        if len(date.split(" ")) == 2:
            date = date.split(" ")[-1].split(".")
            date.pop()
            date = [int(i) for i in date]
            return date

        else:
            return False


if __name__ == '__main__':
    # Here VkApi object is created and logged in with group token
    start = time.time()
    logging.config.fileConfig("logs/logging.conf")
    logger = logging.getLogger("root")
    logger.critical("Start: \n")

    try:
        vk_session = vk_api.VkApi(token=vk_token)
        manager = Manager(vk_session)
        manager.hold()

    except Exception as exception:
        finish = time.time()
        logger.critical("Finish %s\n" % str(finish - start))
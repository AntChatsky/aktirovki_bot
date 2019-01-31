# -*- coding: UTF-8 -*-.

from time import localtime
import re
import vk_api
from random import randrange
from vk_api.longpoll import VkLongPoll, VkEventType
from get_info import get_
from DO_NOT_PUSH_TO_GIT import vk_token, admin_id


class Container(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self.storage = self.get_variables()

    def get_variables(self):
        """
        Read variables from file, which name was given in declaration
        of Container object.
        """
        result = []
        with open(self.file_name, "r") as f:
            for line in f:
                if line[-1:] == "\n":
                    result.append(line[:-1])
                else:
                    result.append(line)

        return result

    def add(self, elem):
        """
        Adds new string with variable to the file.
        """
        # If element hadn't been added before
        if str(elem) not in self.storage:
            with open(self.file_name, "a") as f:
                f.write(str(elem) + "\n")

            self.storage.append(str(elem))

            return True

        else:
            return False


class Bot(object):
    # TODO fix chats
    # TODO memorizing users' shifts
    def __init__(self, vk_session):
        self.vk_session = vk_session
        self.vk = self.vk_session.get_api()

        self.longpoll = VkLongPoll(self.vk_session)

        self.users_container = Container("users.txt")
        self.chats_container = Container("chats.txt")

        self.months = ["января", "февраля", "марта", "апреля", "мая",
                       "июня", "июля", "августа", "сентября", "октября",
                       "ноября", "декабря"]

        self.last_update = []
        self.old_data_message = "Нет достоверной информации."

        self.messages_callback = {"Я хочу получать уведомления об актировках.":
                                  self.add_to_inform,
                                  "Что по актировкам?": self.inform_event
                                  }
        self.messages_answers = {}

    def listen(self):
        """
        Checks every event which bot can get, answers on messages
        """
        for event in self.longpoll.check():
            print(event.type)
            print("***")
            if event.type == VkEventType.MESSAGE_NEW and event.text \
                    and event.to_me:
                if event.text in self.messages_callback:
                    self.messages_callback[event.text](event)

                elif event.text in self.messages_answers:
                    self.send_message(event, self.messages_answers[event.text])

                else:
                    self.send_message(event, "Прости, я тебя не понимаю")

    def send_message(self, event, text):
        if event.from_user:
            self.vk.messages.send(
                user_id=event.user_id,
                message=text,
                random_id=self.get_random_id()
            )

        elif event.from_chat:
            self.vk.messages.send(
                chat_id=event.chat_id,
                message=text,
                random_id=self.get_random_id()
            )

    def add_to_inform(self, event):
        """
        Adds chat's or user's id to container file.
        """
        sucess_message = """Теперь вы будете получать уведомления об 
        актировках."""
        decline_message = """Вы уже получаете уведомления об 
        актировках."""

        if event.from_user:
            # If user's already been added to database
            if not self.users_container.add(event.user_id):
                self.send_message(event, sucess_message)

            else:
                self.send_message(event, decline_message)

        elif event.from_chat:
            if not self.chats_container.add(event.chat_id):
                self.send_message(event, sucess_message)

            else:
                self.send_message(event, decline_message)

    def inform(self, users, chats):
        """
        Sends information message to every user which had subscribed.
        :param users: array, which contains users' id
        :param chats: array, which contains chats' id
        """
        if self.last_update:
            date = self.last_update[0]
            shift1 = self.last_update[1]
            shift2 = self.last_update[2]

            if [localtime()[2], localtime()[1]] == date:
                text = str(date[0]) + " " + self.months[date[1] - 1] + "\n" \
                       + shift1 + "\n" + shift2

            else:
                text = self.old_data_message
        else:
            text = self.old_data_message

        if users:
            for id_ in users:
                # Prevents sending message to user, who has banned bot
                try:
                    self.vk.messages.send(
                        user_id=int(id_),
                        message=text,
                        random_id=self.get_random_id()
                    )
                except vk_api.exceptions.ApiError:
                    continue

        if chats:
            for id_ in chats:
                try:
                    self.vk.messages.send(
                        user_id=int(id_),
                        message=text,
                        random_id=self.get_random_id()
                    )
                except vk_api.exceptions.ApiError:
                    continue

    def inform_event(self, event):
        """
        Directs demanded information from event to main inform function
        """
        if event.from_user:
            self.inform([event.user_id], False)

        elif event.from_chat:
            self.inform([event.chat_id], False)

    def emergency(self, exception):
        """
        Sends emergency message to the creator
        """
        self.vk.messages.send(
            user_id=admin_id,
            message="Помоги своему чаду! Всё сломалось! "
                    "Вот тип ошибки:" + type(exception).__name__,
            random_id=self.get_random_id()
        )

    @staticmethod
    def get_random_id():
        return randrange(0, 30 * (10**4))


class Manager(object):
    def __init__(self, vk_session):
        self.bot = Bot(vk_session)

        updates_schedule_hours = [6, 11, 17]
        self.updates_schedule = [i*60 for i in updates_schedule_hours]
        self.updates_happened = [False for i in self.updates_schedule]
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
                    for i in range(len(self.updates_happened)):
                        self.updates_happened[i] = False

                self.check_updates()
                self.bot.listen()

        except Exception as exception:
            self.bot.emergency(exception)
            raise exception

    def check_updates(self):
        """
        If it's time to check, checks website with demanded information
        for any updates. If they do exist, it transfers them to bot.
        """
        # Variable, which contains real time in minutes
        time_now = localtime()[3] * 60 + localtime()[4]
        if (time_now - self.last_iteration_time) >= 1:
            # Updates iterator
            self.last_iteration_time = time_now

            # Checks if it's time to update data
            for i in range(len(self.updates_schedule)):
                # If data hasn't updated yet
                if not self.updates_happened[i]:
                    update_time = self.updates_schedule[i]
                    # If data's going to update soon
                    if (update_time - time_now) < 30 \
                            and (time_now - update_time) < 30:
                        date, shift1, shift2 = get_()

                        date = date.split(" ")[-1]
                        date, shift1, shift2 = self.check_data(
                            date, shift1, shift2)

                        # If anything was, expect boolean 0 was
                        # returned from function
                        if date:
                            # Updates flag
                            self.updates_happened[i] = True
                            self.bot.last_update = [date, shift1, shift2]
                            self.bot.inform(self.bot.users_container.storage,
                                            self.bot.chats_container.storage)

                        break

    def check_data(self, date, shift1, shift2):
        """
        Checks data, which was read from website by several criteria.
        Returns processed data if data is correct, boolean 0
        for every incoming variable if it's incorrect.
        """

        # 0: day, 1: month
        date_now = [localtime()[2], localtime()[1]]

        date = date.split(".")
        date.pop()
        date = [int(i) for i in date]

        # Compares real date with date given as an argument
        # and checks the text for the key phrase
        if date_now == date and (self.key_phrase in shift1
                                 or self.key_phrase in shift2):
            if self.key_phrase in shift1:
                from_, to = re.findall("\d{1,2}", shift1)
                shift1 = "Первая смена: занятия отменяются с " \
                         + from_ + " до " + to + " класса."

            if self.key_phrase in shift2:
                from_, to = re.findall("\d{1,2}", shift2)
                shift2 = "Вторая смена: занятия отменяются с " \
                         + from_ + " до " + to + " класса."

            return date, shift1, shift2

        return False, False, False


if __name__ == '__main__':
    # Here VkApi object is created and logged in with group token
    vk_session = vk_api.VkApi(token=vk_token)
    manager = Manager(vk_session)
    manager.hold()


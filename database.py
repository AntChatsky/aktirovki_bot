# -*- coding: UTF-8 -*-.
import sqlite3


class Database(object):
    def __init__(self, database, table_name):
        self.database = database

        self.table_name = table_name

        self.columns = None
        self.connection = None
        self.cursor = None

    def get_column(self, column):
        self.connect()

        self.cursor.execute("SELECT {name} FROM {tn}"
                            .format(name=column, tn=self.table_name)
                            )

        self.disconnect()

    def total_rows(self):
        self.connect()

        self.cursor.execute("SELECT COUNT(*) FROM {tn}"
                            .format(tn=self.table_name)
                            )
        count = self.cursor.fetchall()

        self.disconnect()

        return count[0][0]

    def create_table(self, table_name):
        self.connect()

        columns = ",".join(self.columns)
        self.cursor.execute("CREATE TABLE IF NOT EXISTS {tn} ({values})"
                            .format(tn=table_name, values=columns)
                            )

        self.disconnect()

    def add_column(self, name, values_type, default_value=""):
        self.connect()

        self.cursor.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct} "
                            "DEFAULT '{df}'".format(
            tn=self.table_name, cn=name, ct=values_type, df=default_value)
        )

        self.disconnect()

    def connect(self, cursor_class=False):
        self.connection = sqlite3.connect(self.database)

        self.cursor = self.connection.cursor(cursor_class) if cursor_class \
            else self.connection.cursor()

    def disconnect(self):
        self.connection.commit()
        self.connection.close()

        self.connection = None
        self.cursor = None


class UsersDatabase(Database):
    def __init__(self, database):
        super(UsersDatabase, self).__init__(database, "users")

        self.shifts = {1: "first_shift", 2: "second_shift"}

        self.columns = ["ID INTEGER PRIMARY KEY",
                        self.shifts[1] + " TEXT",
                        self.shifts[2] + " TEXT"]
        self.create_table("users")

    def get_all(self):
        self.connect()

        self.cursor.execute("SELECT * FROM {tn}".format(tn=self.table_name))

        self.disconnect()

    def get_user(self, peer_id):
        self.connect()

        self.cursor.execute("SELECT {idf}, {idl} FROM {tn} where ID={peer_id}"
                            .format(idf=self.shifts[1], idl=self.shifts[2],
                                    tn=self.table_name, peer_id=peer_id)
                            )

        fetch = self.cursor.fetchall()

        self.disconnect()

        if not fetch:
            return False
        else:
            fetch = list(fetch[0])

        if fetch[0] == "+":
            fetch[0] = True
        else:
            fetch[0] = False

        if fetch[1] == "+":
            fetch[1] = True
        else:
            fetch[1] = False

        return fetch

    def add_user(self, peer_id):
        self.connect()

        try:
            self.cursor.execute("INSERT INTO {tn} (ID) VALUES ({peer_id})"
                                .format(tn=self.table_name, peer_id=peer_id)
                                )

        except sqlite3.IntegrityError:
            print("IntegrityError with id " + str(peer_id))

            self.disconnect()
            return False

        self.disconnect()
        return True

    def delete(self, peer_id):
        self.connect()

        self.cursor.execute("DELETE from {tn} WHERE ID={peer_id};"
                            .format(tn=self.table_name, peer_id=peer_id)
                            )

        self.disconnect()

    def subscribe(self, peer_id, shift):
        self.connect()

        self.cursor.execute("UPDATE {tn} SET {shift} = '+' WHERE ID={peer_id}"
                            .format(tn=self.table_name,
                                    shift=self.shifts[shift],
                                    peer_id=peer_id)
                            )

        self.disconnect()

    def unsubscribe(self, peer_id, shift):
        self.connect()

        self.cursor.execute("UPDATE {tn} set {shift} = '-' where ID={peer_id}"
                            .format(tn=self.table_name,
                                    shift=self.shifts[shift],
                                    peer_id=peer_id)
                            )

        fetch = self.get_user(peer_id)

        # Delete user if it's not subscribed
        if not fetch[0] and not fetch[1]:
            self.delete(peer_id)

        self.disconnect()
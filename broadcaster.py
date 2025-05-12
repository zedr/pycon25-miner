#!/usr/bin/env python3
import asyncio
import argparse
import logging
import re
import uuid
import random
import sqlite3
from dataclasses import dataclass
import datetime as dt
from typing import Generator, Optional

from cheat.irc_client import IrcClient
from miner import validate

BROADCASTER_NAME = "broadcaster"
PEOPLE_NAMES = ("Alice", "Bob", "Eve", "Carol", "Craig", "Erin", "Sybil")

line_rxp = re.compile(r"^(?P<cmd>[a-z]{1,2}) ?(?P<args>.*)$")
src_rxp = re.compile(r"^:(?P<nick>\w+)!(?P<user>\w+)")
mine_rxp = re.compile(
    r"^:INV:"
    r"(?P<difficulty>[0-9]{1,2}):"
    r"(?P<message_id>[0-9a-f]{8}):"
    r"(?P<nonce>[0-9]+)$"
)


def generate_random_message() -> str:
    first = random.choice(PEOPLE_NAMES)
    second = random.choice(list(set(PEOPLE_NAMES) - {first}))
    amount = random.randint(1, 100_000_000)
    return f"{first} sends {amount} to {second}"


@dataclass
class Transaction:
    """A transaction message"""

    id: Optional[int]
    message_id: str
    difficulty: int
    message: str
    created_at: Optional[dt.datetime] = None

    def __str__(self):
        return f"TX:{self.message_id}:{self.difficulty}:{self.message}"

    @classmethod
    def create_random(cls, difficulty: int = 0) -> "Transaction":
        return cls(
            id=None,
            message_id=uuid.uuid4().hex[:8],
            difficulty=difficulty,
            message=generate_random_message(),
        )


class RateLimitDatabase:
    """An in-memory SQLite database for rate limiting requests"""

    seconds_between_requests: int = 5

    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._setup()

    def _setup(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                user_nick TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS index_user_nick ON attempts (user_nick)
            """,
        ]
        for stmt in statements:
            self._conn.execute(stmt)
        self._conn.commit()

    def check(self, user_nick: str) -> bool:
        """Check and update the last time the user made an attempt.

        Returns True if the user is allowed to make a request,
        False if they are rate limited.
        """
        cur = self._conn.cursor()
        cur.execute(
            """
                    SELECT id, updated_at FROM attempts
                    WHERE user_nick = ?
                """,
            (user_nick,),
        )
        row = cur.fetchone()

        now = dt.datetime.now(tz=dt.timezone.utc)

        if row:
            uid, val = row
            last_attempt = dt.datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
            last_attempt = last_attempt.replace(tzinfo=dt.timezone.utc)
            delta = (now - last_attempt).total_seconds()
            if delta < self.seconds_between_requests:
                return False  # Too soon

            # Update the timestamp of the existing row
            cur.execute(
                """
                    UPDATE attempts
                    SET updated_at = ?
                    WHERE id = ?
                    """,
                (now.strftime("%Y-%m-%d %H:%M:%S"), uid),
            )
        else:
            # Insert new attempt if none exists
            cur.execute(
                """
                    INSERT INTO attempts (user_nick)
                    VALUES (?)
                    """,
                (user_nick,),
            )

        self._conn.commit()
        return True


class TransactionDatabase:
    """A SQLite database for transactions and related awards"""

    def __init__(self, name: str = ":memory:"):
        self._conn = sqlite3.connect(name)
        self._setup()

    def _setup(self) -> None:
        """Set up the database where necessary"""
        statements = """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                message_id CHAR(8) NOT NULL UNIQUE,
                difficulty INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            
            CREATE INDEX IF NOT EXISTS index_message_id ON transactions (message_id)
            
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                user_nick TEXT NOT NULL,
                transaction_id INTEGER NOT NULL,
                nonce INTEGER NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE NO ACTION
            )
            
            CREATE INDEX IF NOT EXISTS index_transaction_id ON awards (transaction_id)
            
            CREATE INDEX IF NOT EXISTS index_user_nick ON awards (user_nick)
        """
        for stmt in (txt.strip() for txt in re.split("\n +\n", statements)):
            self._conn.execute(stmt)

    def add_transaction(self, tr: Transaction) -> None:
        """Add a transaction to the database"""
        self._conn.execute(
            """
            INSERT INTO transactions (message_id, difficulty, message)
            VALUES (?, ?, ?)
            """,
            (tr.message_id, tr.difficulty, tr.message),
        )
        self._conn.commit()

    def get_transactions(
        self, message_id: str = None
    ) -> Generator[Transaction, None, None]:
        stmt = """
        SELECT * FROM transactions
        """
        if message_id:
            stmt += f' WHERE message_id = "{message_id}"'
        cur = self._conn.execute(stmt)
        for tup in cur.fetchall():
            yield Transaction(*tup)

    def get_transaction(self, message_id: str) -> Optional[Transaction]:
        try:
            return next(self.get_transactions(message_id))
        except StopIteration:
            return None

    def check_award_exists(self, transaction: Transaction) -> bool:
        """Check if this transaction has already been mined and awarded"""
        cur = self._conn.execute(
            "SELECT * FROM awards WHERE transaction_id = ?", (transaction.id,)
        )
        if cur.fetchone():
            return True
        else:
            return False

    def create_award(self, user_nick: str, message_id: str, nonce: int) -> bool:
        """Add a transaction to the database"""
        tr = self.get_transaction(message_id)
        if not tr:
            logging.error("No transaction in database for %s", message_id)
            return False

        if self.check_award_exists(tr):
            logging.info("%s was too late for %s", message_id, user_nick)
            return False

        self._conn.execute(
            """
            INSERT INTO awards (user_nick, transaction_id, nonce)
            VALUES (?, ?, ?)
            """,
            (user_nick, tr.id, nonce),
        )
        self._conn.commit()
        return True

    def get_scores(self):
        cur = self._conn.execute(
            """
            SELECT user_nick, COUNT(user_nick) FROM awards GROUP BY user_nick
            """
        )
        for tup in cur.fetchall():
            yield tup


class Game:
    def __init__(self, db: TransactionDatabase, difficulty: int):
        self.db = db
        self.difficulty = difficulty

    def create_transaction(self) -> Transaction:
        """Create a new transaction"""
        tr = Transaction.create_random(self.difficulty)
        self.db.add_transaction(tr)
        return tr

    def get_transactions(self) -> Generator[Transaction, None, None]:
        """Get all the transactions"""
        yield from self.db.get_transactions()

    def get_transaction(self, message_id: str) -> Optional[Transaction]:
        """Get a transaction with a given message_id"""
        return self.db.get_transaction(message_id)

    def create_award(self, user_nick: str, message_id: str, nonce: int) -> bool:
        """Award a successful mined transaction to a user"""
        return self.db.create_award(user_nick, message_id, nonce)

    def get_scores(self):
        """Get the scores for each user"""
        yield from self.db.get_scores()


class Broadcaster(IrcClient):
    """The broadcaster"""

    def __init__(self, db_name: str = ":memory:", difficulty: int = 0):
        super().__init__()
        self.channel = "pycon"
        self.game = Game(db=TransactionDatabase(db_name), difficulty=difficulty)
        self.attempt_database = RateLimitDatabase()

    async def send_user_message(self, user_nick: str, message: str) -> None:
        """Send a message to the given channel"""
        await self.send(f"PRIVMSG {user_nick} :{message}")

    async def process_inv(self, user_nick: str, msg: str) -> None:
        """Process the INV message"""
        match = mine_rxp.match(msg)
        if match:
            difficulty, message_id, _nonce = match.groups()
            try:
                nonce = int(_nonce)
            except ValueError:
                pass
            else:
                tr = self.game.get_transaction(message_id)
                if validate(nonce, tr.message, tr.difficulty):
                    if self.game.create_award(user_nick, message_id, nonce):
                        msg = f"{user_nick} successfully mined {message_id}"
                        logging.info(msg)
                        await self.send_message(self.channel, msg)
                else:
                    logging.info(
                        "%s failed nonce validation for %s", user_nick, message_id
                    )

    async def process(self, src: str, cmd: str, msgs: list[str]) -> None:
        if cmd == "PRIVMSG":
            first, msg = msgs
            channel_name = first.lstrip("#")
            if self.channel == channel_name and msg.startswith(":INV:"):
                src_match = src_rxp.match(src)
                if src_match:
                    user_nick = src_match.group(1)
                    if self.attempt_database.check(user_nick):
                        await self.process_inv(user_nick, msg)
                    else:
                        await self.send_user_message(user_nick, "Observe speed limit!")


async def async_input(prompt: str = "") -> str:
    """
    Asynchronous wrapper around the built-in input function.
    """
    return await asyncio.get_event_loop().run_in_executor(
        None,
        input,
        prompt,
    )


def cancel_other_tasks():
    """Cancel all the running tasks in the current loop except the current"""
    for task in asyncio.all_tasks(asyncio.get_event_loop()):
        if task is not asyncio.current_task:
            task.cancel()


async def cli(client: Broadcaster) -> None:
    """Command line interface to the Broadcaster"""
    await client.join_channel(client.channel)

    while True:
        try:
            line = await async_input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if matched := line_rxp.match(line):
            cmd, *args = matched.groups()
            match cmd:
                case "ct":
                    # Create transaction
                    tr = client.game.create_transaction()
                    await client.send_message(client.channel, str(tr))
                    print(f"Created {tr.message_id} with difficulty {tr.difficulty}")
                case "lt":
                    # List transactions
                    for tr in client.game.get_transactions():
                        print(tr.message_id)
                case "ls":
                    # List scores
                    scores = client.game.get_scores()
                    for pos, (name, score) in enumerate(scores, 1):
                        print(f"{pos}. {name}: {score}")
                case "q":
                    break
                case "pd":
                    # Print game difficulty
                    print(client.game.difficulty)
                case "cd":
                    # Communicate game difficulty
                    await client.send_message(
                        client.channel,
                        f"The current difficulty is {client.game.difficulty}",
                    )
                case "pt":
                    # Print transaction
                    message_id = args[0]
                    tr = client.game.get_transaction(message_id)
                    print(tr)
                case "ct":
                    # Communicate transaction
                    message_id = args[0]
                    tr = client.game.get_transaction(message_id)
                    await client.send_message(client.channel, str(tr))
                case "sd":
                    # Set difficulty
                    try:
                        new_difficulty = int(args[0])
                    except (ValueError, IndexError):
                        print(f"!!! Bad command: {line}")
                    else:
                        client.game.difficulty = new_difficulty
                        await client.send_message(
                            client.channel,
                            f"The difficulty is now {client.game.difficulty}",
                        )
                case _:
                    print("!!! Unknown command")
    print("Quitting...")
    cancel_other_tasks()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", default="localhost", help="IRC server host to connect to"
    )
    parser.add_argument("-c", "--channel", default="pycon", help="IRC channel to join")
    parser.add_argument(
        "-d",
        "--database",
        default=":memory:",
        help="SQLite database file or memory namespace to use",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="Be verbose"
    )
    parser.add_argument(
        "-D", "--difficulty", default=1, type=int, help="Starting difficulty to use"
    )
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    client = Broadcaster(db_name=args.database, difficulty=args.difficulty)
    await client.connect(server_host=args.host)
    await client.set_user(BROADCASTER_NAME)
    await client.set_nick(BROADCASTER_NAME)
    logging.info("Connected to %s:%s", args.host, args.channel)
    try:
        await asyncio.gather(
            client.handle_forever(
                handlers=(client.handle_ping, client.process, client.echo)
            ),
            cli(
                client,
            ),
            return_exceptions=False,
        )
    except asyncio.CancelledError:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

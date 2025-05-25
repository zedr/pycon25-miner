import asyncio
import unittest
import datetime as dt

from broadcaster import (
    Transaction,
    RateLimitDatabase,
    TransactionDatabase,
    Game,
    Broadcaster,
    cancel_other_tasks
)
from miner import validate


class TransactionTests(unittest.TestCase):
    def test_create_random_transaction(self):
        tx = Transaction.create_random(3)
        self.assertEqual(tx.difficulty, 3)
        self.assertEqual(len(tx.message_id), 8)
        self.assertIn("sends", tx.message)
        self.assertIsNone(tx.id)
        self.assertIsInstance(str(tx), str)


class RateLimitDatabaseTests(unittest.TestCase):
    def test_check_rate_limit(self):
        db = RateLimitDatabase()
        user = "testuser"
        self.assertTrue(db.check(user))  # First time is allowed
        self.assertFalse(db.check(user))  # Second time too soon
        # Manually modify timestamp to simulate delay
        cursor = db._conn.cursor()
        cursor.execute("UPDATE attempts SET updated_at = ?", (
            (dt.datetime.now() - dt.timedelta(seconds=10)).strftime(
                "%Y-%m-%d %H:%M:%S"),))
        db._conn.commit()
        self.assertTrue(db.check(user))  # Should now be allowed again


class TransactionDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = TransactionDatabase()

    def test_add_and_get_transaction(self):
        tx = Transaction.create_random(1)
        self.db.add_transaction(tx)
        found = self.db.get_transaction(tx.message_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.message_id, tx.message_id)

    def test_awards(self):
        tx = Transaction.create_random(2)
        self.db.add_transaction(tx)
        tx = self.db.get_transaction(
            tx.message_id)  # Refresh to get the `id` set
        self.assertFalse(self.db.check_award_exists(tx))
        self.assertTrue(self.db.create_award("alice", tx.message_id, 42))
        self.assertTrue(self.db.check_award_exists(tx))
        self.assertFalse(
            self.db.create_award("bob", tx.message_id, 99))  # Already awarded
        scores = list(self.db.get_scores())
        self.assertEqual(scores[0][0], "alice")
        self.assertEqual(scores[0][1], 1)


class GameTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(TransactionDatabase(), difficulty=1)

    def test_transaction_lifecycle(self):
        tx = self.game.create_transaction()
        self.assertEqual(tx.difficulty, 1)
        found = self.game.get_transaction(tx.message_id)
        self.assertEqual(found.message_id, tx.message_id)

    def test_award_flow(self):
        tx = self.game.create_transaction()
        self.assertTrue(self.game.create_award("user1", tx.message_id, 123))
        self.assertFalse(self.game.create_award("user2", tx.message_id,
                                                456))  # Already mined

    def test_scores(self):
        tx = self.game.create_transaction()
        self.game.create_award("alice", tx.message_id, 1)
        scores = list(self.game.get_scores())
        self.assertEqual(scores, [("alice", 1)])


class BroadcasterLogicTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_inv_success_and_failure(self):
        broadcaster = Broadcaster()
        tx = broadcaster.game.create_transaction()
        valid_nonce = 0
        # Find a valid nonce
        while not validate(valid_nonce, tx.message, tx.difficulty):
            valid_nonce += 1
        msg = f":INV:{tx.difficulty}:{tx.message_id}:{valid_nonce}"
        await broadcaster.process_inv("user", msg)
        # Re-processing same INV should fail (already mined)
        await broadcaster.process_inv("user", msg)
        # Invalid nonce
        await broadcaster.process_inv("user",
                                      f":INV:{tx.difficulty}:{tx.message_id}:notanumber")

    async def test_rate_limit(self):
        broadcaster = Broadcaster()
        tx = broadcaster.game.create_transaction()
        valid_nonce = 0
        while not validate(valid_nonce, tx.message, tx.difficulty):
            valid_nonce += 1
        msg = f":INV:{tx.difficulty}:{tx.message_id}:{valid_nonce}"
        user = "spammer"
        # Allow first request
        await broadcaster.process(":nick!user", "PRIVMSG", ["#pycon", msg])
        # Second one gets rate-limited
        await broadcaster.process(":nick!user", "PRIVMSG", ["#pycon", msg])


class UtilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_input_and_cancel(self):
        # async_input just wraps input; not testing I/O but can test cancellation behavior
        task = asyncio.create_task(asyncio.sleep(10))
        with self.assertRaises(asyncio.exceptions.CancelledError):
            cancel_other_tasks()
            await asyncio.sleep(0.1)  # allow cancellation
        self.assertTrue(task.cancelled() or task.done())


if __name__ == "__main__":
    unittest.main()

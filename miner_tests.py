import hashlib
import unittest

from miner import sha256hash, verify, mine


class MinerTests(unittest.TestCase):
    """Tests for the mining algorithms"""

    def test_sha256hash(self):
        """Test hashing a string using SHA256

        Signature:
            sha256hash(s: str) -> str
        """
        hsh = sha256hash("pycon")
        self.assertEqual(
            "252c425e25465ed8d69b644be6575442c5de0cdd99f061cfef82206a425ad475",
            hsh
        )

    def test_verify(self):
        """Verify a hash against a given difficulty

        Signature:
            verify(hashed: str, difficulty: int) -> bool
        """
        self.assertTrue(
            verify(
                "002c425e25465ed8d69b644be6575442c5de0cdd99f061",
                2
            )
        )
        self.assertTrue(
            verify(
                "02c425e25465ed8d69b644be6575442c5de0cdd99f061",
                1
            )
        )
        self.assertFalse(
            verify(
                "02c425e25465ed8d69b644be6575442c5de0cdd99f061",
                2
            )
        )
        self.assertFalse(
            verify(
                "a2c425e25465ed8d69b644be6575442c5de0cdd99f061",
                1
            )
        )

    def test_mine(self):
        """Test the mining algorithm

        Signature:
            mine(text: str, difficulty: int, begin_nonce: int) -> tuple[int, str]
        """
        text = "A gives 42 to B"
        nonce, hsh = mine(text, 3, begin_nonce=1)
        expected = (
            "00088bae66363a0d358e263da39df5ffd1454594666a4b2b468ff561c055fbcb"
        )
        proof = hashlib.sha256(f"{nonce}:{text}".encode()).hexdigest()
        self.assertEqual(
            expected,
            proof
        )
        self.assertEqual(
            proof,
            hsh
        )


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from app.core.config import settings
from app.database import init_database
from app.services.assistant_session_memory import AssistantSessionMemory


class AssistantSessionMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_path = settings.DATABASE_PATH
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        settings.DATABASE_PATH = str(Path(self.directory.name) / "memory.sqlite3")
        init_database()
        self.memory = AssistantSessionMemory()

    def tearDown(self) -> None:
        settings.DATABASE_PATH = self.original_path
        self.directory.cleanup()

    def test_memory_is_isolated_by_user_and_session(self) -> None:
        self.memory.save_confirmed("user-a", "session-1", {"country": "越南"}, "VN", "M3", ["src-1"])
        self.assertEqual(self.memory.load("user-a", "session-1")["country_code"], "VN")
        self.assertIsNone(self.memory.load("user-b", "session-1"))
        self.assertIsNone(self.memory.load("user-a", "session-2"))


if __name__ == "__main__":
    unittest.main()

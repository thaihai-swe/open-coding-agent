import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.presentation.cli import parse_args, run


class TestCli(unittest.TestCase):
    def test_args(self) -> None:
        args = parse_args(["--session", "session-1", "--json"])
        self.assertEqual(args.session, "session-1")
        self.assertTrue(args.json_mode)
        self.assertFalse(args.debug)

    def test_debug_arg(self) -> None:
        self.assertTrue(parse_args(["--debug"]).debug)

    def test_missing_configuration_is_actionable(self) -> None:
        with patch.dict(os.environ, {"CONFIG_FILE": "/tmp/nonexistent-openai-config.json"}, clear=True):
            self.assertEqual(run([]), 2)


if __name__ == "__main__":
    unittest.main()

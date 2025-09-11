import unittest
import sys
from pathlib import Path

# Incluir src no sys.path para import local sem instalação
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

class TestImport(unittest.TestCase):
    def test_can_import_package(self):
        import safety_ai_app  # noqa: F401
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main(verbosity=2)

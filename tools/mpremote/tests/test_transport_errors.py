"""Host-only checks: python -m unittest discover -s tools/mpremote/tests -p test_transport_errors.py"""

import errno
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mpremote.transport import Transport, TransportExecError, _convert_filesystem_error


class FilesystemErrorTests(unittest.TestCase):
    def test_supported_errno_formats(self):
        cases = (
            ("OSError: 2", errno.ENOENT),
            ("OSError: [Errno 2] ENOENT", errno.ENOENT),
            ("OSError: [Errno 2]", errno.ENOENT),
            ("OSError: [Errno 2] No such file/directory", errno.ENOENT),
            ("OSError: [Errno 2] No such file/directory: /new.py", errno.ENOENT),
            ("OSError: [Errno 30] Read-only filesystem", errno.EROFS),
            ("OSError: [Errno 13] Permission denied", errno.EACCES),
            ("OSError: [Errno 2] Fichier absent: /caf\u00e9.py", errno.ENOENT),
        )
        for message, expected in cases:
            for ending in ("", "\n", "\r\n", "\r\r\n", "\r\n\r\n"):
                with self.subTest(message=message, ending=ending):
                    error = TransportExecError(
                        b"", "Traceback (most recent call last):\r\n" + message + ending
                    )
                    converted = _convert_filesystem_error(error, "/new.py")
                    self.assertIsInstance(converted, OSError)
                    self.assertEqual(converted.errno, expected)
                    self.assertEqual(converted.strerror, "/new.py")

    def test_unknown_or_malformed_error_is_preserved(self):
        for message in (
            "OSError: [Errno 99999] Unknown error",
            "OSError: [Errno -2] Invalid negative code",
            "OSError: [Errno 2x] Invalid code",
            "OSError: [Errno 2]trailing-junk",
            "OSError: [Errno 2",
            "ValueError: [Errno 2] No such file/directory",
            "OSError: [Errno 2] No such file/directory\nValueError: final exception",
            "",
            "\r\n",
        ):
            with self.subTest(message=message):
                error = TransportExecError(b"", message)
                self.assertIs(_convert_filesystem_error(error, "/new.py"), error)

    def test_missing_destination_checks_return_false(self):
        class MissingFileTransport(Transport):
            def exec(self, command):
                assert command == "import os"

            def eval(self, expression):
                raise TransportExecError(b"", "OSError: [Errno 2] No such file/directory\r\n")

        transport = MissingFileTransport()
        self.assertFalse(transport.fs_exists("/new.py"))
        self.assertFalse(transport.fs_isdir("/new.py"))


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import unittest
from unittest.mock import Mock

from rescue.nex_rescue import collect_report


class RescueInventoryTests(unittest.TestCase):
    def test_report_is_read_only_and_excludes_serials(self):
        payload = {
            "blockdevices": [
                {
                    "name": "nvme0n1",
                    "type": "disk",
                    "size": 1000,
                    "ro": "0",
                    "rm": "0",
                    "model": "Virtual Disk",
                    "serial": "must-not-appear",
                    "fstype": None,
                    "mountpoints": [None],
                    "children": [
                        {
                            "name": "nvme0n1p1",
                            "type": "part",
                            "size": 500,
                            "ro": "0",
                            "rm": "0",
                            "model": None,
                            "fstype": "vfat",
                            "mountpoints": ["/boot"],
                        }
                    ],
                },
                {
                    "name": "loop0",
                    "type": "loop",
                    "size": 123,
                    "ro": "1",
                    "rm": "0",
                },
            ]
        }
        runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=["lsblk"],
                returncode=0,
                stdout=json.dumps(payload),
                stderr="",
            )
        )

        report = collect_report(run=runner)

        self.assertFalse(report["write_operations_enabled"])
        self.assertEqual(report["mode"], "read-only")
        self.assertEqual(
            [device["name"] for device in report["devices"]],
            ["nvme0n1", "nvme0n1p1"],
        )
        self.assertEqual(report["devices"][1]["mountpoints"], ["/boot"])
        self.assertNotIn("serial", repr(report))
        runner.assert_called_once_with(
            [
                "lsblk",
                "--json",
                "--bytes",
                "--output",
                "NAME,TYPE,SIZE,RO,RM,MODEL,FSTYPE,MOUNTPOINTS",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_lsblk_error_propagates_without_other_commands(self):
        runner = Mock(side_effect=FileNotFoundError("lsblk"))
        with self.assertRaises(FileNotFoundError):
            collect_report(run=runner)
        runner.assert_called_once()


if __name__ == "__main__":
    unittest.main()

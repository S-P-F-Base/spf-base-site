import re
import subprocess
from enum import Enum
from typing import Literal


class ServerStatus(str, Enum):
    RUNNING = "running"
    DEAD = "dead"
    FAILED = "failed"
    START = "start"
    STOP = "stop"
    UNKNOWN = "unknown"


class ServerControl:
    @classmethod
    def get_status(cls) -> ServerStatus:
        try:
            res = subprocess.run(
                [
                    "/usr/bin/systemctl",
                    "status",
                    "gmod.service",
                    "--no-pager",
                    "--plain",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        except FileNotFoundError:
            return ServerStatus.UNKNOWN

        for line in res.stdout.splitlines():
            if line.strip().startswith("Active:"):
                match = re.search(r"\((.*?)\)", line)
                if match:
                    key = match.group(1).lower()
                    mapping = {
                        "running": ServerStatus.RUNNING,
                        "dead": ServerStatus.DEAD,
                        "exited": ServerStatus.DEAD,
                        "failed": ServerStatus.FAILED,
                        "start": ServerStatus.START,
                        "stop": ServerStatus.STOP,
                    }
                    return mapping.get(key, ServerStatus.UNKNOWN)

                break

        return ServerStatus.UNKNOWN

    @classmethod
    def perform_action(cls, action: Literal["start", "stop", "restart"]) -> None:
        subprocess.run(["/usr/bin/systemctl", action, "gmod.service"], check=False)

"""Run contract smoke tests against a disposable local PostgreSQL cluster."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


DATABASE_NAME = "working_actor_os_contract_test"


def available_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"{name} is required to run contract smoke tests")
    return path


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=env)


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    python = str(backend_dir / ".venv" / "bin" / "python")
    if not Path(python).exists():
        python = sys.executable
    initdb = require_binary("initdb")
    pg_ctl = require_binary("pg_ctl")
    createdb = require_binary("createdb")
    port = available_port()
    with tempfile.TemporaryDirectory(prefix="waos-contract-", dir="/tmp") as temp:
        root = Path(temp)
        data = root / "postgres"
        socket_dir = root / "socket"
        uploads = root / "uploads"
        socket_dir.mkdir()
        uploads.mkdir()
        run([initdb, "-D", str(data), "--auth=trust", "--no-locale", "--encoding=UTF8"])
        run(
            [
                pg_ctl,
                "-D",
                str(data),
                "-o",
                f"-h 127.0.0.1 -p {port} -k {socket_dir}",
                "-w",
                "start",
            ]
        )
        try:
            run([createdb, "-h", "127.0.0.1", "-p", str(port), DATABASE_NAME])
            env = os.environ.copy()
            env.update(
                {
                    "DATABASE_URL": f"postgresql+psycopg://127.0.0.1:{port}/{DATABASE_NAME}",
                    "ALLOW_TEST_DATABASE_RESET": "true",
                    "ENVIRONMENT": "contract_test",
                    "UPLOAD_DIR": str(uploads),
                    "OPENAI_API_KEY": "",
                    "PARALLEL_API_KEY": "",
                    "OPENROUTESERVICE_API_KEY": "",
                    "GOOGLE_MAPS_API_KEY": "",
                    "MAPBOX_ACCESS_TOKEN": "",
                    "WEB_SEARCH_PROVIDER": "none",
                    "TRAVEL_PROVIDER": "manual",
                    "SCHEDULER_ENABLED": "false",
                    "NOTIFICATIONS_ENABLED": "false",
                    "PUBLIC_PROFILE_IMPORT_ENABLED": "false",
                }
            )
            run([python, "-m", "alembic", "upgrade", "head"], env=env)
            return subprocess.run(
                [python, "-m", "pytest", "-m", "contract_smoke", *sys.argv[1:]],
                cwd=backend_dir,
                env=env,
            ).returncode
        finally:
            run([pg_ctl, "-D", str(data), "-m", "fast", "-w", "stop"])


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only identity of the deployed Edge for QA reports (which build did the tests actually run against?).

Uses the project's pinned read-only SSH observer: `docker inspect` of the selected Edge container (image id and
container creation time). Core exposes no version API, so its version stays unverified unless REPORT_CORE_VERSION
is supplied. Never raises: a missing observer configuration just means "not observed".
"""

from __future__ import annotations

import shlex


def edge_deployment_identity(ws_url: str) -> str | None:
    try:
        from utils.inbound_completion import EdgeSqliteReader
        reader = EdgeSqliteReader(ws_url)
    except Exception:
        return None
    try:
        command = ("sudo -S -p '' docker inspect --format '{{.Config.Image}}|{{.Created}}' "
                   + shlex.quote(reader.container))
        stdin, stdout, stderr = reader.client.exec_command(command, timeout=15)
        stdin.write(reader.password + "\n")
        stdin.flush()
        data = stdout.read().decode("utf-8", errors="replace").strip()
        stderr.read()
        if stdout.channel.recv_exit_status() != 0 or "|" not in data:
            return None
        image, created = data.split("|", 1)
        image = image.replace("sha256:", "sha256:")[:19] + "…" if image.startswith("sha256:") else image
        return f"container {reader.container}; image {image}; container created {created.strip()}"
    except Exception:
        return None
    finally:
        reader.close()

from __future__ import annotations

import os
import pathlib
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Sequence

import httpx
import structlog

from app.core.config import settings

LOGGER = structlog.get_logger(__name__)


ALLOWED_EXTRA_FLAGS = {
    "--flat-nodes",
    "--tag-transform-script",
}


@dataclass
class Osm2pgsqlOptions:
    database_name: str
    username: str
    password: str | None
    host: str
    port: int
    mode: str  # create | append
    slim: bool = True
    hstore: bool = True
    cache_mb: int = 2000
    number_processes: int = 4
    style_path: str | None = None
    input_path: str | None = None
    input_url: str | None = None
    extra_args: Sequence[str] = ()
    work_dir: pathlib.Path | None = None


def _ensure_local_source(options: Osm2pgsqlOptions) -> str:
    """Download remote PBF if needed and return local path."""
    if options.input_path:
        path = pathlib.Path(options.input_path)
        if not path.is_absolute():
            path = settings.filesystem.pbf_dir / path
        if not path.exists():
            raise FileNotFoundError(f"PBF not found at {path}")
        return str(path)

    if not options.input_url:
        raise ValueError("input_path or input_url required")

    url = options.input_url
    target_dir = settings.filesystem.pbf_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", url, timeout=None, follow_redirects=True) as response:
        response.raise_for_status()
        resolved_name = pathlib.Path(response.url.path).name or pathlib.Path(url).name
        target_path = target_dir / resolved_name
        LOGGER.info(
            "downloading_pbf",
            source=url,
            resolved=str(response.url),
            destination=str(target_path),
        )
        with target_path.open("wb") as fh:
            for chunk in response.iter_bytes():
                fh.write(chunk)

    return str(target_path)


def build_osm2pgsql_command(options: Osm2pgsqlOptions, input_path: str) -> list[str]:
    cmd = [
        "osm2pgsql",
        f"--database={options.database_name}",
        f"--user={options.username}",
        f"--host={options.host}",
        f"--port={options.port}",
        f"--number-processes={options.number_processes}",
        f"--cache={options.cache_mb}",
    ]

    if options.mode == "create":
        cmd.append("--create")
    else:
        cmd.append("--append")

    if options.slim:
        cmd.append("--slim")
    if options.hstore:
        cmd.append("--hstore")
    if options.style_path:
        cmd.extend(["--style", options.style_path])

    for extra in options.extra_args:
        if not any(extra.startswith(flag) for flag in ALLOWED_EXTRA_FLAGS):
            raise ValueError(f"Flag not allowed: {extra}")
        cmd.append(extra)

    cmd.append(input_path)
    return cmd


def run_osm2pgsql(
    options: Osm2pgsqlOptions,
    log_file: pathlib.Path,
    line_callback: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    source = _ensure_local_source(options)
    cmd = build_osm2pgsql_command(options, source)
    LOGGER.info("osm2pgsql_command", command=cmd, log_file=str(log_file))

    env = None
    if options.password:
        env = {**os.environ, "PGPASSWORD": options.password}

    with log_file.open("a", buffering=1) as log_handle:
        log_handle.write(f"# Started osm2pgsql at {time.asctime()}\n")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=options.work_dir or settings.filesystem.root,
            env=env,
        )
        assert process.stdout is not None
        for line in process.stdout:
            log_handle.write(line)
            if line_callback:
                line_callback(line.rstrip())
        process.wait()
        log_handle.write(f"# Finished with exit code {process.returncode} at {time.asctime()}\n")
    return (process.returncode or 0, source)

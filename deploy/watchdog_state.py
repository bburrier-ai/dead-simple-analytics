#!/usr/bin/env python3
"""Race-resistant state, lock, and failure-evidence handling for watchdog.sh."""

from __future__ import annotations

import errno
import fcntl
import os
import secrets
import stat
import subprocess
import sys
from collections.abc import Sequence

MAX_FAILURE_LINES = 1000
MAX_FAILURE_BYTES = 256 * 1024
MAX_EVIDENCE_BYTES = 16 * 1024


class StateError(RuntimeError):
    """Raised when watchdog state cannot be handled safely."""


def open_state_dir(path: str) -> int:
    absolute_path = os.path.abspath(path)
    components = [component for component in absolute_path.split(os.sep) if component]
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory_fd = os.open(os.sep, flags)

    try:
        for component in components:
            try:
                next_fd = os.open(component, flags, dir_fd=directory_fd)
            except FileNotFoundError:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=directory_fd)
                except FileExistsError:
                    pass
                next_fd = os.open(component, flags, dir_fd=directory_fd)
            except OSError as error:
                if error.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise StateError(
                        f"state directory path contains a symbolic link or non-directory: {path}"
                    ) from error
                raise
            os.close(directory_fd)
            directory_fd = next_fd

        state_stat = os.fstat(directory_fd)
        if state_stat.st_uid != os.geteuid():
            raise StateError(f"state directory is not owned by the current user: {path}")
        os.fchmod(directory_fd, 0o700)
        return directory_fd
    except Exception:
        os.close(directory_fd)
        raise


def open_private_file(directory_fd: int, name: str, flags: int) -> int:
    try:
        file_fd = os.open(
            name,
            flags | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
            mode=0o600,
            dir_fd=directory_fd,
        )
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise StateError(f"watchdog state file is a symbolic link: {name}") from error
        if error.errno == errno.ENXIO:
            raise StateError(
                f"watchdog state file is not a private owned file: {name}"
            ) from error
        raise

    try:
        file_stat = os.fstat(file_fd)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_uid != os.geteuid():
            raise StateError(f"watchdog state file is not a private owned file: {name}")
        os.fchmod(file_fd, 0o600)
        return file_fd
    except Exception:
        os.close(file_fd)
        raise


def replace_failure_log(directory_fd: int, content: bytes) -> None:
    temporary_name = f".failures.log.{secrets.token_hex(8)}"
    temporary_fd = open_private_file(
        directory_fd,
        temporary_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
    )
    try:
        with os.fdopen(temporary_fd, "wb", closefd=False) as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_fd)
        os.replace(
            temporary_name,
            "failures.log",
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        os.close(temporary_fd)
        try:
            os.unlink(temporary_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass


def append_failure(directory_fd: int, evidence: bytes) -> None:
    failure_fd = open_private_file(
        directory_fd,
        "failures.log",
        os.O_RDWR | os.O_APPEND | os.O_CREAT,
    )
    try:
        written = 0
        while written < len(evidence):
            written += os.write(failure_fd, evidence[written:])
        os.fsync(failure_fd)
        size = os.fstat(failure_fd).st_size
        start = max(0, size - MAX_FAILURE_BYTES)
        os.lseek(failure_fd, start, os.SEEK_SET)
        content = bytearray()
        while len(content) < MAX_FAILURE_BYTES:
            chunk = os.read(failure_fd, min(64 * 1024, MAX_FAILURE_BYTES - len(content)))
            if not chunk:
                break
            content.extend(chunk)
    finally:
        os.close(failure_fd)

    if start:
        newline = content.find(b"\n")
        content = content[newline + 1 :] if newline >= 0 else bytearray()
    lines = bytes(content).splitlines(keepends=True)
    if size > MAX_FAILURE_BYTES or len(lines) > MAX_FAILURE_LINES:
        replace_failure_log(directory_fd, b"".join(lines[-MAX_FAILURE_LINES:]))


def open_anonymous_evidence_file(directory_fd: int) -> int:
    name = f".evidence.{secrets.token_hex(8)}"
    evidence_fd = open_private_file(
        directory_fd,
        name,
        os.O_RDWR | os.O_CREAT | os.O_EXCL,
    )
    try:
        os.unlink(name, dir_fd=directory_fd)
    except Exception:
        os.close(evidence_fd)
        raise
    return evidence_fd


def read_evidence(evidence_fd: int) -> bytes:
    evidence = os.pread(evidence_fd, MAX_EVIDENCE_BYTES + 1, 0)
    if len(evidence) > MAX_EVIDENCE_BYTES:
        evidence = evidence[: MAX_EVIDENCE_BYTES - 1] + b"\n"
    return evidence


def run_watchdog(state_dir: str, command: Sequence[str]) -> int:
    state_fd = open_state_dir(state_dir)
    try:
        lock_fd = open_private_file(
            state_fd,
            "watchdog.lock",
            os.O_WRONLY | os.O_CREAT,
        )
        try:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return 0

            evidence_fd = open_anonymous_evidence_file(state_fd)
            environment = os.environ.copy()
            environment["DSA_WATCHDOG_MANAGED"] = "1"
            environment["DSA_WATCHDOG_EVIDENCE_PATH"] = (
                f"/proc/{os.getpid()}/fd/{evidence_fd}"
            )
            try:
                process = subprocess.Popen(
                    command,
                    env=environment,
                )
                return_code = process.wait()
                evidence = read_evidence(evidence_fd)
            finally:
                os.close(evidence_fd)

            if evidence:
                try:
                    append_failure(state_fd, evidence)
                except (OSError, StateError) as error:
                    print(
                        f"DSA watchdog failed: cannot persist failure evidence: {error}",
                        file=sys.stderr,
                    )
                    return return_code or 1
            return return_code
        finally:
            os.close(lock_fd)
    finally:
        os.close(state_fd)


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: watchdog_state.py STATE_DIR COMMAND [ARG ...]", file=sys.stderr)
        return 2

    try:
        return run_watchdog(sys.argv[1], sys.argv[2:])
    except (OSError, StateError) as error:
        print(f"DSA watchdog failed: cannot secure state directory: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

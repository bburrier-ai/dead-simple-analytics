import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("compose_name", ["docker-compose.yml", "docker-compose.test.yml"])
def test_postgres_healthcheck_targets_configured_database(compose_name: str) -> None:
    """The healthcheck must probe POSTGRES_DB, not the implicit user-named database."""
    lines = (REPO_ROOT / compose_name).read_text(encoding="utf-8").splitlines()
    database_line = next(line.strip() for line in lines if line.strip().startswith("POSTGRES_DB:"))
    healthcheck_line = next(line.strip() for line in lines if "pg_isready" in line)

    configured_database = database_line.split(":", 1)[1].strip()
    if ":-" in configured_database:
        configured_database = configured_database.rsplit(":-", 1)[1].rstrip("}")

    assert " -d " in healthcheck_line, (
        f"{compose_name} postgres healthcheck does not select POSTGRES_DB: {healthcheck_line}"
    )
    assert configured_database in healthcheck_line, (
        f"{compose_name} healthcheck does not target configured database "
        f"{configured_database!r}: {healthcheck_line}"
    )


def test_production_services_restart_unless_stopped() -> None:
    """Production services must recover after crashes and Docker daemon restarts."""
    lines = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8").splitlines()

    for service in ("postgres", "backend"):
        service_index = lines.index(f"  {service}:")
        service_lines = []
        for line in lines[service_index + 1 :]:
            if line.startswith("  ") and not line.startswith("    "):
                break
            service_lines.append(line.strip())

        assert "restart: unless-stopped" in service_lines, (
            f"{service} must use restart: unless-stopped in docker-compose.yml"
        )


def test_make_test_runs_use_isolated_compose_projects_and_cleanup(tmp_path: Path) -> None:
    """Concurrent local test runs must not share a Compose stack or database port."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    pytest_log = tmp_path / "pytest.log"

    docker = bin_dir / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        f'[ "$(pwd -P)" = {REPO_ROOT} ] || exit 41\n'
        f'printf \'portvar=%s %s\\n\' "$TEST_POSTGRES_PORT" "$*" >> {docker_log}\n'
        'if [ "$1" = compose ]; then\n'
        "  shift\n"
        '  while [ "$1" != -p ]; do shift; done\n'
        "  project=$2\n"
        '  case " $* " in\n'
        '    *" port postgres 5432 "*)\n'
        "      checksum=$(printf '%s' \"$project\" | cksum | cut -d' ' -f1)\n"
        "      printf '127.0.0.1:%s\\n' \"$((20000 + checksum % 20000))\"\n"
        "      ;;\n"
        "  esac\n"
        "fi\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)

    uv = bin_dir / "uv"
    uv.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$TEST_DATABASE_URL\" >> {pytest_log}\n"
        'exit "${UV_EXIT_CODE:-0}"\n',
        encoding="utf-8",
    )
    uv.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    for name in ("COMPOSE_TEST_PROJECT", "TEST_DATABASE_URL", "TEST_POSTGRES_PORT"):
        env.pop(name, None)

    def run_test(exit_code: int) -> subprocess.CompletedProcess[str]:
        run_env = env.copy()
        run_env["UV_EXIT_CODE"] = str(exit_code)
        return subprocess.run(
            ["make", "test"],
            cwd=REPO_ROOT,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run_test, (0, 23)))

    assert [result.returncode for result in results] == [0, 2], [
        result.stdout + result.stderr for result in results
    ]

    docker_calls = docker_log.read_text(encoding="utf-8").splitlines()
    projects = [
        call.split()[call.split().index("-p") + 1] for call in docker_calls if " up " in call
    ]
    cleanup_projects = {
        call.split()[call.split().index("-p") + 1] for call in docker_calls if " down " in call
    }
    database_urls = pytest_log.read_text(encoding="utf-8").splitlines()

    assert len(projects) == 2
    assert len(set(projects)) == 2
    assert all(call.startswith("portvar=0 ") for call in docker_calls if " up " in call)
    assert cleanup_projects == set(projects)
    assert len(database_urls) == 2
    assert len(set(database_urls)) == 2

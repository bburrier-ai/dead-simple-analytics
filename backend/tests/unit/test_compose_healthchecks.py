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

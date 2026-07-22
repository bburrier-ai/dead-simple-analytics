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

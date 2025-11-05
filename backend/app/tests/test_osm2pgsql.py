import pathlib

from app.utils.osm2pgsql import Osm2pgsqlOptions, build_osm2pgsql_command


def test_build_osm2pgsql_command(tmp_path: pathlib.Path) -> None:
    options = Osm2pgsqlOptions(
        database_name="osm_test",
        username="app_user",
        password=None,
        host="localhost",
        port=5432,
        mode="create",
        input_path=str(tmp_path / "small.pbf"),
    )
    (tmp_path / "small.pbf").write_text("stub")
    command = build_osm2pgsql_command(options, str(tmp_path / "small.pbf"))
    assert "--create" in command
    assert command[-1].endswith("small.pbf")

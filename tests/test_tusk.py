import tempfile
from tusk import __main__


def test_database_config_from_file():
    with tempfile.TemporaryDirectory() as dir:
        path = f"{dir}/.tusk.toml"
        with open(path, "w") as f:
            f.write(
                r"""
[database]
url = "dbname=postgres user=postgres"
"""
            )
        c = __main__.DatabaseConfig.from_file(path)
        assert c.url == "dbname=postgres user=postgres"

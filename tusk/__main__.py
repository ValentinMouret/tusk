from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from difflib import ndiff
from pathlib import Path
from typing import List

import psycopg2
import toml
from prettytable import PrettyTable

"""
TODO: Refactor.
TODO: Add a cleanup step.
TODO: Support standard Postgres variables. (:variable)
"""


@dataclass
class TuskConfig:
    action: str
    db_config: DatabaseConfig
    path: Path = Path("example")

    @staticmethod
    def from_args(args: argparse.Namespace) -> TuskConfig:
        return TuskConfig(
            action=args.action,
            db_config=DatabaseConfig.from_file(f"{args.path}/{args.config}"),
            path=args.path,
        )


@dataclass
class DatabaseConfig:
    # E.g. "dbname=postgres user=postgres"
    url: str

    @staticmethod
    def from_file(p: Path) -> DatabaseConfig:
        with open(p, "r") as f:
            c = toml.load(f)
        return DatabaseConfig(c["database"]["url"])


@dataclass
class Paths:
    root: Path

    seeds: Path = field(init=False)
    tests: Path = field(init=False)
    expected: Path = field(init=False)
    out: Path = field(init=False)

    def __post_init__(self):
        self.seeds = self.root / "seeds"
        self.tests = self.root / "tests"
        self.expected = self.root / "expected"
        self.out = self.root / "out"

        self.__check_setup()

    @property
    def test_files(self) -> List[Path]:
        return self.tests.glob("**/*.sql")

    @property
    def seed_files(self) -> List[Path]:
        if not self.seeds.exists():
            print("Please create a seeds folder")
            sys.exit(1)
        return self.seeds.glob("**/*.sql")

    def expected_path(self, p: Path) -> Path:
        return Path(
            p.__str__()
            .replace(self.tests.__str__(), self.expected.__str__())
            .replace(".sql", ".out")
        )

    def out_path(self, p: Path) -> Path:
        return Path(
            p.__str__()
            .replace(self.tests.__str__(), self.out.__str__())
            .replace(".sql", ".out")
        )

    def __check_setup(self):
        for folder in [self.tests, self.expected, self.out]:
            if not folder.exists():
                raise RuntimeError(f"Please create folder {folder}")


def get_columns(cursor) -> List[str]:
    """
    Returns the columns from a query.
    """
    return [c.name for c in cursor.description]


def __run_query(cursor, path: Path) -> str:
    query = path.read_text()
    cursor.execute("begin;")
    cursor.execute(query)
    result = to_pretty_table(cursor)
    cursor.execute("rollback;")

    return result


def seed(cursor, paths: Paths):
    """
    Seeds the database.
    """
    for file in paths.seed_files:
        print(f"Seeding {file.name}")
        cursor.execute(file.read_text())


def update(cursor, paths: Paths):
    """
    Runs the test files and assumes the outputs to be the right ones.
    They will overwrite the previously expected outputs.
    """
    for test_file in paths.test_files:
        result = __run_query(cursor, test_file)
        expected_file = paths.expected_path(test_file)

        expected_file.parent.mkdir(exist_ok=True, parents=True)

        with expected_file.open("w") as out:
            out.write(result)


def test(cursor, paths: Paths):
    """
    Runs the test files and compares the outputs with the expected ones.
    """
    n_errors = 0
    for i, test_file in enumerate(paths.test_files):
        result = __run_query(cursor, test_file)
        out_file = paths.out_path(test_file)

        out_file.parent.mkdir(exist_ok=True, parents=True)

        with out_file.open("w") as out:
            out.write(result)

        expected_file = paths.expected_path(test_file)

        if not expected_file.exists():
            print(
                f"not ok {i+1} - Could not find expected file {expected_file}. Please run tusk update"
            )
            sys.exit(1)

        diff = [
            line
            for line in ndiff(
                expected_file.read_text().splitlines(keepends=True),
                result.splitlines(keepends=True),
            )
            # Only keep lines that show a difference.
            if line.startswith(("+", "-"))
        ]
        if diff:
            ++n_errors
            header = result.splitlines()[0:3]
            print(
                f"""
# Query file: {test_file.name}
# Expected result file: {expected_file.name}
# Actual result file: {out_file.name}
# 
#   {header[0]}
#   {header[1]}
#   {header[2]}"""
            )
            print("".join([f"# {l}" for l in diff]))
            print(f"not ok {i+1} - {test_file}")
        else:
            print(f"ok {i+1} - {test_file}")

        if n_errors:
            print(f"You have {n_errors} tests that do not pass. Good luck!")
            sys.exit(13)


def to_pretty_table(cursor) -> str:
    table = PrettyTable(get_columns(cursor))
    for line in cursor.fetchall():
        table.add_row(line)
    return table.get_string()


action_handlers = {"seed": seed, "update": update, "test": test}


def main(conf: TuskConfig):
    paths = Paths(conf.path)
    handler = action_handlers[conf.action]
    with psycopg2.connect(conf.db_config.url) as conn:
        with conn.cursor() as cursor:
            handler(cursor, paths)


def build_parser() -> argparse.ArgumentParser:
    """
    Handles the parsing of arguments.

    action: either "seed", "update", or "test".
            Describes the main action to undertake.
    --path: (optional)
            Path to a directory containing "tests" and a config file (.tusk.toml by default).
            If no value is provided, the current directory is used.
    --config: (optional)
            Name of the configuration file to use. It is the relative path from `--config`.
            If no value is provided, `.tusk.toml` is used.
            It can be useful to have multiple configuration files if you multiple environments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["seed", "update", "test"], type=str)
    parser.add_argument("--path", default=".", type=Path, required=False)
    parser.add_argument("--config", default=".tusk.toml", type=Path, required=False)
    return parser


if __name__ == "__main__":
    ARGS = build_parser().parse_args(sys.argv[1:])
    CONF = TuskConfig.from_args(ARGS)
    main(CONF)

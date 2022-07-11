# Tusk

Tusk is a tool to run regression tests on a PostgreSQL database.
It is inspired by [regresql](https://github.com/dimitry/regresql) and Postgres’
[regress](https://github.com/postgres/postgres/tree/master/src/test/regress).

These tool felt hard to use, so I am giving a shot at making something simpler.

## Concept

The idea is simple. SQL files describe tests. For example:
```sql
select to_timestamp(1637532423) as timestamp;
```

These tests are run against the database and they return some output:
```text
+----------------------------------+
|   timestamp                      |
+----------------------------------+
| 2021-11-21 23:07:03+01           |
+----------------------------------+
```

It’s the **update** phase of testing. We know this behaviour to be the good one, so we record it
somewhere.

Now, we make changes to the database and we want to know if behaviour is the same on past tests.
For this, we run the same tests in a **test** phase and get some results:

```text
+----------------------------------+
|   timestamp                      |
+----------------------------------+
| 2021-11-21 23:06:03+00           |
+----------------------------------+
```

If we *diff* the two outputs, we can clearly see the output is different, so we broke our test. Did we
change something related to timezones?

## Getting started

Assuming you have a file tree like:
```text
example
├── .tusk.toml       # Some configuration to connect to the database.
├── expected         # The outputs of the «update» phase.
│   ├── orders.out
│   └── users.out
├── out              # The outputs of the «test» phase.
│   ├── orders.out
│   └── users.out
├── seeds
│   └── users.sql    # If you want to seed your database first, these can be helpful.
└── tests            # The tests to run. One file=one test.
    ├── orders.sql
    └── users.sql
```

Tests run in transactions, so they are independent of each other.

### Seed (optional)

This phase is optional, though it makes little sense to test an empty database. But maybe you are
handling your seeding differently. Anyway, if you want to seed the database, run:

```bash
tusk seed --path example/seeds
```

This run **any** SQL code that’s inside the seeds.
Feel free to put anything here that’s relevant.

### Update

This phase will run your tests and generate *expected* outputs that will be saved in an `expected`
folder.

```bash
tusk update --path example
```

### Test

This phase will run your tests, generate *actual* outputs that will be saved in an `out` folder.

It will also diff the outputs. If the diff is empty, tests pass and return `OK`.

If not, a useful diff is displayed and the test and test suite don’t pass.****
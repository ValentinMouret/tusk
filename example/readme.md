# Example

This shows an example setup that would work out of the box

A schema is provided.

You can start experimenting with it in the following way:

```shell
# Create a development database.
createdb tusk_dev

# Create the user table.
psql -d tusk_dev -f example/schema.sql

## Distribution is not sorted out, so this is verbose and not handy at the moment.

# Install dependencies
poetry install

# Seed the database.
poetry run python -m tusk seed --path=example

# Update the tests.
poetry run python -m tusk update --path=example

# Test the tests.
poetry run python -m tusk test --path=example
```

# Python UVX Example: CLI from GitHub

This repository provides a simple example of how to define and run a Python command-line interface (CLI) directly from a GitHub repository using `uvx`.

## What it does

The example CLI, `napy`, is a simple application built with Typer that greets a user. It demonstrates how `uvx` can execute Python scripts hosted on GitHub without needing to clone the repository locally first.

## Prerequisites

Before you can run this example, you need to have `uvx` installed on your system. If you haven't installed it yet, please follow the installation instructions for `uvx` [here](https://docs.astral.sh/uv/getting-started/installation/).

## Usage

You can run the CLI directly from GitHub using `uvx`.

**Basic command:**

The following command will download (if not already cached) and run the `napy` script:

```sh
uvx --from git+https://github.com/mortenoh/python-uvx-example napy
```

This will execute the default `hello` command, outputting:

```
👋 Hello, world!
```

**Providing arguments:**

The `hello` command accepts a `--name` argument. You can pass arguments to the script as follows:

```sh
uvx --from git+https://github.com/mortenoh/python-uvx-example napy --name "UVX User"
```

This will output:

```
👋 Hello, UVX User!
```

**Ensuring the latest version:**

To make sure `uvx` fetches the latest updates from the GitHub repository before running, use the `--refresh` flag:

```sh
uvx --refresh --from git+https://github.com/mortenoh/python-uvx-example napy --name "Fresh UVX"
```

## How it works

- **`pyproject.toml`**: This file defines the project metadata, dependencies (like `typer`), and the script entry point. `uvx` uses this file to understand how to build and run the Python application.
  ```toml
  [project.scripts]
  napy = "napy:main_entry_point"
  ```
- **`src/napy/__init__.py`**: This file contains the actual Python code for the CLI using the `typer` library.

  ```python
  import typer

  app = typer.Typer()

  @app.command()
  def hello(name: str = "world"):
      """Say hello to someone."""
      typer.echo(f"👋 Hello, {name}!")
  ```

- **`uvx`**: The `uvx` tool handles the fetching of the code from the specified Git repository (`git+https://github.com/mortenoh/python-uvx-example`), sets up a temporary virtual environment, installs dependencies defined in `pyproject.toml`, and then executes the specified script (`napy`).

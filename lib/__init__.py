from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

import tomlkit


def graphite_version() -> str:
    try:
        return version("graphiteos")
    except PackageNotFoundError:
        pyproject = Path(__file__).parent.parent / 'pyproject.toml'

        with open(pyproject, 'r') as f:
            toml = tomlkit.load(f)
            return str(toml['project']['version'])

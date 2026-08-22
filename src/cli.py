import sys

from .presentation.cli import parse_args, run

__all__ = ["parse_args", "run"]


if __name__ == "__main__":
    sys.exit(run())

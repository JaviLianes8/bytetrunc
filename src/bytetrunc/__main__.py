"""Allow ``python -m bytetrunc``."""

import sys

from ._cli import main

if __name__ == "__main__":
    sys.exit(main())

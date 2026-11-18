import sys
from .cli import main
try:
    main()
except (ValueError, FileNotFoundError, RuntimeError, PermissionError) as exc:
    print('ERROR:', exc, file=sys.stderr)
    raise SystemExit(2)

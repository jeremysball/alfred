import sys
import os

print(f"isatty(stdin): {sys.stdin.isatty()}")
print(f"isatty(stdout): {sys.stdout.isatty()}")
print(f"isatty(stderr): {sys.stderr.isatty()}")
print(f"TERM: {os.environ.get('TERM')}")

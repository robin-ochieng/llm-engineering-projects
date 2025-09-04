"""
This file was moved to: ../tender-intelligence-platform/app.py

To run the dashboard now use:
    python .\tender-intelligence-platform\app.py

Keeping this stub avoids confusion if you try to run the old path.
"""

from __future__ import annotations

from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent
    new_app = root / "tender-intelligence-platform" / "app.py"
    if new_app.exists():
        print("Note: The dashboard was moved to tender-intelligence-platform/app.py")
        print("Run it with:\n  python .\\tender-intelligence-platform\\app.py")
    else:
        print("Relocated app not found at tender-intelligence-platform/app.py")


if __name__ == "__main__":
    main()

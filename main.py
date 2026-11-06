"""Entry point: `python main.py` saves weekly charts into ./screenshots."""
import sys
from pathlib import Path

from chart_screenshots.cli import main

OUTPUT_DIR = Path(__file__).resolve().parent / "screenshots"

if __name__ == "__main__":
    sys.exit(main(OUTPUT_DIR))

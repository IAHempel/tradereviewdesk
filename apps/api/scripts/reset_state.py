from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import state_store


def main() -> None:
    parser = ArgumentParser(description="Manage TradeReviewDesk local API state.")
    parser.add_argument(
        "--show-paths",
        action="store_true",
        help="Print the seed and store paths without modifying state.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the current store file from the seed file.",
    )
    args = parser.parse_args()

    if args.show_paths or not args.reset:
        print(f"Seed: {state_store.get_seed_path()}")
        print(f"Store: {state_store.get_store_path()}")

    if args.reset:
        state_store.reset_state_from_seed()
        print("State reset from seed.")


if __name__ == "__main__":
    main()

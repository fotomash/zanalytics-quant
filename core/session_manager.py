from __future__ import annotations

from pathlib import Path


def read_intro() -> str:
    """Read and return the conversation starter text."""
    intro_path = Path(__file__).resolve().parent.parent / "conversation_starter.md"
    with intro_path.open("r", encoding="utf-8") as fh:
        return fh.read()


def main() -> None:
    """Print intro text and start a simple interactive session."""
    print(read_intro())
    while True:
        try:
            user_input = input("> ")
        except EOFError:
            break
        if user_input.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        print(f"You said: {user_input}")


if __name__ == "__main__":
    main()

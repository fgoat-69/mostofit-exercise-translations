from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_source(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {path}: "
            f"line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(data, list):
        raise ValueError(
            f"{path} must contain a JSON array of exercise objects."
        )

    return data


def validate_source_exercise(
    exercise: Any,
    index: int,
    source_path: Path,
) -> tuple[str, str, list[str]]:
    if not isinstance(exercise, dict):
        raise ValueError(
            f"{source_path}: item {index} must be a JSON object."
        )

    exercise_id = exercise.get("id")
    name = exercise.get("name")
    instructions = exercise.get("instructions")

    if not isinstance(exercise_id, str) or not exercise_id.strip():
        raise ValueError(
            f"{source_path}: item {index} has an invalid or missing id."
        )

    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            f"{source_path}: exercise {exercise_id!r} "
            "has an invalid or missing name."
        )

    if not isinstance(instructions, list):
        raise ValueError(
            f"{source_path}: exercise {exercise_id!r} "
            "instructions must be an array."
        )

    for instruction_index, instruction in enumerate(instructions):
        if not isinstance(instruction, str):
            raise ValueError(
                f"{source_path}: exercise {exercise_id!r}, "
                f"instruction {instruction_index} must be a string."
            )

    return exercise_id, name, instructions


def build_template(
    source_path: Path,
) -> dict[str, dict[str, Any]]:
    source = load_source(source_path)
    compact: dict[str, dict[str, Any]] = {}

    for index, exercise in enumerate(source):
        exercise_id, name, instructions = validate_source_exercise(
            exercise,
            index,
            source_path,
        )

        if exercise_id in compact:
            raise ValueError(
                f"Duplicate exercise ID {exercise_id!r} "
                f"found at source item {index}."
            )

        compact[exercise_id] = {
            "name": name,
            "instructions": instructions,
        }

    return compact


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a compact English translation template "
            "from the full exercise source JSON."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Full English exercise JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Generated compact English JSON file.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether the committed output is up to date.",
    )

    arguments = parser.parse_args()

    try:
        compact = build_template(arguments.input)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    generated_text = (
        json.dumps(compact, ensure_ascii=False, indent=2) + "\n"
    )

    if arguments.check:
        if not arguments.output.exists():
            print(
                f"Error: generated file does not exist: "
                f"{arguments.output}",
                file=sys.stderr,
            )
            return 1

        existing_text = arguments.output.read_text(encoding="utf-8")

        if existing_text != generated_text:
            print(
                f"Error: {arguments.output} is not up to date.",
                file=sys.stderr,
            )
            print(
                "Run the generator and commit the generated file.",
                file=sys.stderr,
            )
            return 1
    else:
        arguments.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        arguments.output.write_text(
            generated_text,
            encoding="utf-8",
        )

    print(
        f"Generated compact English template with "
        f"{len(compact)} unique exercises."
    )
    print(f"Output: {arguments.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

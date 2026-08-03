from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BATCH_FILENAME_PATTERN = re.compile(r"^[a-z]{2}_batch_(\d+)\.json$")


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {path}: "
            f"line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain one JSON object.")

    return data


def validate_exercise(
    exercise_id: str,
    exercise: Any,
    source_path: Path,
) -> None:
    if not isinstance(exercise, dict):
        raise ValueError(
            f"{source_path}: exercise {exercise_id!r} must be an object."
        )

    expected_fields = {"name", "instructions"}
    actual_fields = set(exercise)

    if actual_fields != expected_fields:
        raise ValueError(
            f"{source_path}: exercise {exercise_id!r} must contain exactly "
            f"{sorted(expected_fields)}; found {sorted(actual_fields)}."
        )

    name = exercise["name"]
    instructions = exercise["instructions"]

    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            f"{source_path}: exercise {exercise_id!r} has an invalid name."
        )

    if not isinstance(instructions, list):
        raise ValueError(
            f"{source_path}: exercise {exercise_id!r} instructions "
            "must be an array."
        )

    for index, instruction in enumerate(instructions):
        if not isinstance(instruction, str):
            raise ValueError(
                f"{source_path}: exercise {exercise_id!r}, instruction "
                f"{index} must be a string."
            )


def get_batch_number(path: Path) -> int:
    match = BATCH_FILENAME_PATTERN.fullmatch(path.name)

    if match is None:
        raise ValueError(
            f"Invalid batch filename: {path.name}. "
            "Expected a name such as de_batch_01.json."
        )

    return int(match.group(1))


def collect_batch_files(batch_directory: Path) -> list[Path]:
    batch_files = list(batch_directory.glob("*.json"))

    if not batch_files:
        raise ValueError(f"No JSON batch files found in {batch_directory}.")

    numbered_files = sorted(
        ((get_batch_number(path), path) for path in batch_files),
        key=lambda item: item[0],
    )

    batch_numbers = [number for number, _ in numbered_files]
    expected_numbers = list(
        range(batch_numbers[0], batch_numbers[-1] + 1)
    )

    if batch_numbers != expected_numbers:
        missing = sorted(set(expected_numbers) - set(batch_numbers))
        duplicates = sorted(
            number
            for number in set(batch_numbers)
            if batch_numbers.count(number) > 1
        )

        details: list[str] = []

        if missing:
            details.append(f"missing batches: {missing}")

        if duplicates:
            details.append(f"duplicate batch numbers: {duplicates}")

        raise ValueError("; ".join(details))

    return [path for _, path in numbered_files]


def build_translation(
    batch_directory: Path,
) -> tuple[dict[str, Any], int]:
    merged: dict[str, Any] = {}
    exercise_sources: dict[str, Path] = {}

    batch_files = collect_batch_files(batch_directory)

    for batch_path in batch_files:
        batch = load_json_object(batch_path)

        for exercise_id, exercise in batch.items():
            if not isinstance(exercise_id, str) or not exercise_id:
                raise ValueError(
                    f"{batch_path}: exercise IDs must be non-empty strings."
                )

            validate_exercise(exercise_id, exercise, batch_path)

            if exercise_id in merged:
                first_source = exercise_sources[exercise_id]
                raise ValueError(
                    f"Duplicate exercise ID {exercise_id!r} found in "
                    f"{first_source.name} and {batch_path.name}."
                )

            merged[exercise_id] = exercise
            exercise_sources[exercise_id] = batch_path

    return merged, len(batch_files)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge translation batch files into one JSON file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing the batch JSON files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Generated translation JSON file.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether the generated output is already up to date.",
    )

    arguments = parser.parse_args()

    try:
        merged, batch_count = build_translation(arguments.input)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    generated_text = (
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
    )

    if arguments.check:
        if not arguments.output.exists():
            print(
                f"Error: generated file does not exist: {arguments.output}",
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
                "Run the build script and commit the generated changes.",
                file=sys.stderr,
            )
            return 1
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(generated_text, encoding="utf-8")

    print(
        f"Validated {batch_count} batches and "
        f"{len(merged)} unique exercises."
    )
    print(f"Output: {arguments.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

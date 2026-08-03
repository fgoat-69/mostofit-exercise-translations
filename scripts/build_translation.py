from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BATCH_FILENAME_PATTERN = re.compile(
    r"^(?P<language>[a-z]{2})_batch_(?P<number>\d+)\.json$"
)


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
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


def parse_batch_filename(path: Path) -> tuple[str, int]:
    match = BATCH_FILENAME_PATTERN.fullmatch(path.name)

    if match is None:
        raise ValueError(
            f"Invalid batch filename: {path.name}. "
            "Expected a name such as de_batch_01.json, "
            "es_batch_01.json, or fr_batch_01.json."
        )

    return (
        match.group("language"),
        int(match.group("number")),
    )


def collect_batch_files(
    batch_directory: Path,
    expected_language: str | None,
    expected_batches: int | None,
) -> list[Path]:
    if not batch_directory.exists():
        raise ValueError(
            f"Batch directory does not exist: {batch_directory}"
        )

    if not batch_directory.is_dir():
        raise ValueError(
            f"Batch path is not a directory: {batch_directory}"
        )

    batch_files = list(batch_directory.glob("*.json"))

    if not batch_files:
        raise ValueError(
            f"No JSON batch files found in {batch_directory}."
        )

    parsed_files: list[tuple[int, Path]] = []
    detected_languages: set[str] = set()

    for path in batch_files:
        language, batch_number = parse_batch_filename(path)
        detected_languages.add(language)
        parsed_files.append((batch_number, path))

        if (
            expected_language is not None
            and language != expected_language
        ):
            raise ValueError(
                f"{path}: expected language prefix "
                f"{expected_language!r}, found {language!r}."
            )

    if len(detected_languages) != 1:
        raise ValueError(
            f"{batch_directory} contains multiple language prefixes: "
            f"{sorted(detected_languages)}."
        )

    numbered_files = sorted(
        parsed_files,
        key=lambda item: item[0],
    )

    batch_numbers = [number for number, _ in numbered_files]

    duplicates = sorted(
        number
        for number in set(batch_numbers)
        if batch_numbers.count(number) > 1
    )

    if duplicates:
        raise ValueError(
            f"Duplicate batch numbers found: {duplicates}."
        )

    if batch_numbers[0] != 1:
        raise ValueError(
            "Batch numbering must begin at 1. "
            f"First batch found: {batch_numbers[0]}."
        )

    expected_numbers = list(
        range(1, batch_numbers[-1] + 1)
    )

    if batch_numbers != expected_numbers:
        missing = sorted(
            set(expected_numbers) - set(batch_numbers)
        )

        raise ValueError(
            f"Missing batch numbers: {missing}."
        )

    if (
        expected_batches is not None
        and len(numbered_files) != expected_batches
    ):
        raise ValueError(
            f"Expected {expected_batches} batches in "
            f"{batch_directory}, but found {len(numbered_files)}."
        )

    return [path for _, path in numbered_files]


def build_translation(
    batch_directory: Path,
    expected_language: str | None,
    expected_batches: int | None,
) -> tuple[dict[str, Any], int]:
    merged: dict[str, Any] = {}
    exercise_sources: dict[str, Path] = {}

    batch_files = collect_batch_files(
        batch_directory=batch_directory,
        expected_language=expected_language,
        expected_batches=expected_batches,
    )

    for batch_path in batch_files:
        batch = load_json_object(batch_path)

        for exercise_id, exercise in batch.items():
            if not isinstance(exercise_id, str) or not exercise_id:
                raise ValueError(
                    f"{batch_path}: exercise IDs must be "
                    "non-empty strings."
                )

            validate_exercise(
                exercise_id=exercise_id,
                exercise=exercise,
                source_path=batch_path,
            )

            if exercise_id in merged:
                first_source = exercise_sources[exercise_id]

                raise ValueError(
                    f"Duplicate exercise ID {exercise_id!r} found in "
                    f"{first_source.name} and {batch_path.name}."
                )

            merged[exercise_id] = exercise
            exercise_sources[exercise_id] = batch_path

    return merged, len(batch_files)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Merge translation batch files into one JSON file."
        )
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
        "--language",
        choices=["de", "es", "fr", "nl"],
        help=(
            "Expected two-letter language prefix used by the "
            "batch filenames."
        ),
    )

    parser.add_argument(
        "--expected-batches",
        type=int,
        help="Expected number of batch files.",
    )

    parser.add_argument(
        "--expected-exercises",
        type=int,
        help="Expected number of unique exercises.",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Check whether the generated output is already "
            "up to date instead of writing it."
        ),
    )

    arguments = parser.parse_args()

    try:
        merged, batch_count = build_translation(
            batch_directory=arguments.input,
            expected_language=arguments.language,
            expected_batches=arguments.expected_batches,
        )

        if (
            arguments.expected_exercises is not None
            and len(merged) != arguments.expected_exercises
        ):
            raise ValueError(
                f"Expected {arguments.expected_exercises} unique "
                f"exercises, but found {len(merged)}."
            )

    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    generated_text = (
        json.dumps(
            merged,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    if arguments.check:
        if not arguments.output.exists():
            print(
                "Error: generated file does not exist: "
                f"{arguments.output}",
                file=sys.stderr,
            )
            return 1

        existing_text = arguments.output.read_text(
            encoding="utf-8-sig"
        )

        if existing_text != generated_text:
            print(
                f"Error: {arguments.output} is not up to date.",
                file=sys.stderr,
            )
            print(
                "Run the build workflow and commit the "
                "generated changes.",
                file=sys.stderr,
            )
            return 1

    else:
        arguments.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_output = arguments.output.with_suffix(
            arguments.output.suffix + ".tmp"
        )

        temporary_output.write_text(
            generated_text,
            encoding="utf-8",
            newline="\n",
        )

        temporary_output.replace(arguments.output)

    print(
        f"Validated {batch_count} batches and "
        f"{len(merged)} unique exercises."
    )
    print(f"Output: {arguments.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

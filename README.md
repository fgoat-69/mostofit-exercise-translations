
# MostoFit Exercise Translations

This repository contains translated exercise names and exercise instructions
used by the MostoFit Android application.

The original exercise data is based on:

- yuhonas/free-exercise-db

## Supported languages

- German (`de`)
- Spanish (`es`)
- French (`fr`)
- Dutch (`nl`)

## Structure

Translation files are stored in the `translations` directory:

- `translations/de.json`
- `translations/es.json`
- `translations/fr.json`
- `translations/nl.json`

Each translation is matched to the original exercise using its stable exercise ID.

Example structure:

```json
{
  "Exercise_ID": {
    "name": "Translated exercise name",
    "instructions": [
      "Translated instruction step one.",
      "Translated instruction step two."
    ]
  }
}

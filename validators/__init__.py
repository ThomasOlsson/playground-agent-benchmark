"""Validator registry: name -> module exposing validate(case, workdir)."""
from . import exact_text, json_file, keys_present, file_exists, allowed_paths_check

REGISTRY = {
    "exact_text": exact_text,
    "json_file": json_file,
    "keys_present": keys_present,
    "file_exists": file_exists,
}

ALWAYS_ON = allowed_paths_check  # runs for every case in addition to the declared validator

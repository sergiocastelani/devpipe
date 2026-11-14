import re

import pytest

from devpipe.models.feature_name import normalize_feature_name

CASES = [
    ("Nová Feature_X", "nova-feature-x"),
    ("!!!", ""),
    ("  a--b  ", "a-b"),
    ("New Feature", "new-feature"),
    ("", ""),
    ("already-a-slug", "already-a-slug"),
    ("ÀÉÎõü 123", "aeiou-123"),
    ("__x__", "x"),
    ("a.b/c", "a-b-c"),
    ("Straße", "strae"),
    ("日本", ""),
    ("a - b", "a-b"),
    ("x\ty\nz", "x-y-z"),
    ("C++ & Rust", "c-rust"),
]

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_normalize_feature_name(text, expected):
    assert normalize_feature_name(text) == expected


@pytest.mark.parametrize("text", [text for text, _ in CASES] + ["-", "a_-_b"])
def test_normalize_feature_name_gives_empty_or_valid_slug(text):
    result = normalize_feature_name(text)
    assert result == "" or SLUG.match(result)

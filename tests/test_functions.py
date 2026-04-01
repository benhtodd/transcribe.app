import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from types import SimpleNamespace
import pytest
from transcribe import find_keyword_hits, dedup_hits, fmt_ts_display, fmt_ts_file


def w(word, start, end=None):
    return SimpleNamespace(word=word, start=start, end=end or start + 0.3)


# --- fmt_ts_display ---

def test_fmt_ts_display_zero():
    assert fmt_ts_display(0) == "00:00:00"

def test_fmt_ts_display_minutes():
    assert fmt_ts_display(90) == "00:01:30"

def test_fmt_ts_display_hours():
    assert fmt_ts_display(3661) == "01:01:01"


# --- fmt_ts_file ---

def test_fmt_ts_file_uses_dashes():
    assert fmt_ts_file(90) == "00-01-30"


# --- dedup_hits ---

def test_dedup_hits_removes_close_same_keyword():
    hits = [(1.0, "unicorn"), (1.5, "unicorn"), (5.0, "unicorn")]
    assert dedup_hits(hits) == [(1.0, "unicorn"), (5.0, "unicorn")]

def test_dedup_hits_keeps_hits_beyond_gap():
    hits = [(1.0, "unicorn"), (4.0, "unicorn")]
    assert dedup_hits(hits, min_gap_seconds=2.0) == [(1.0, "unicorn"), (4.0, "unicorn")]

def test_dedup_hits_different_keywords_are_independent():
    hits = [(1.0, "unicorn"), (1.2, "rainbow"), (2.0, "unicorn")]
    result = dedup_hits(hits, min_gap_seconds=2.0)
    assert (1.0, "unicorn") in result
    assert (1.2, "rainbow") in result
    assert (2.0, "unicorn") not in result

def test_dedup_hits_empty():
    assert dedup_hits([]) == []

def test_dedup_hits_single_hit():
    assert dedup_hits([(3.0, "unicorn")]) == [(3.0, "unicorn")]


# --- find_keyword_hits ---

def test_find_keyword_hits_basic():
    words = [w("hello", 1.0), w("unicorn", 2.0), w("world", 3.0)]
    hits = find_keyword_hits(words, ["unicorn"])
    assert hits == [(2.0, "unicorn")]

def test_find_keyword_hits_case_insensitive():
    words = [w("Unicorn", 2.0)]
    assert find_keyword_hits(words, ["unicorn"]) == [(2.0, "unicorn")]

def test_find_keyword_hits_strips_punctuation():
    words = [w("unicorn.", 2.0)]
    assert find_keyword_hits(words, ["unicorn"]) == [(2.0, "unicorn")]

def test_find_keyword_hits_multi_word_phrase():
    words = [w("action", 1.0), w("item", 1.3), w("done", 2.0)]
    hits = find_keyword_hits(words, ["action item"])
    assert len(hits) == 1
    assert hits[0][0] == 1.0

def test_find_keyword_hits_multi_word_not_adjacent():
    words = [w("action", 1.0), w("other", 1.3), w("item", 2.0)]
    assert find_keyword_hits(words, ["action item"]) == []

def test_find_keyword_hits_no_match():
    words = [w("hello", 1.0), w("world", 2.0)]
    assert find_keyword_hits(words, ["unicorn"]) == []

def test_find_keyword_hits_multiple_keywords():
    words = [w("unicorn", 1.0), w("rainbow", 3.0)]
    hits = find_keyword_hits(words, ["unicorn", "rainbow"])
    assert (1.0, "unicorn") in hits
    assert (3.0, "rainbow") in hits

def test_find_keyword_hits_multiple_occurrences():
    words = [w("unicorn", 1.0), w("other", 2.0), w("unicorn", 5.0)]
    hits = find_keyword_hits(words, ["unicorn"])
    assert len(hits) == 2
    assert hits[0][0] == 1.0
    assert hits[1][0] == 5.0

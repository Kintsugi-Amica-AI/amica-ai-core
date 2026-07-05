from voice_sos.src.phrase_matcher import matches_secret_phrase


def test_matches_secret_phrase_inside_transcript() -> None:
    assert matches_secret_phrase("please send help now", "send help")


def test_empty_secret_phrase_does_not_match() -> None:
    assert not matches_secret_phrase("anything", "")

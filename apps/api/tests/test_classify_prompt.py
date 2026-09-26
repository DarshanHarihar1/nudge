from ai.classify import SYSTEM_PROMPT, build_system_prompt


def test_no_examples_is_base_prompt():
    assert build_system_prompt([]) == SYSTEM_PROMPT


def test_examples_are_listed_after_base_prompt():
    prompt = build_system_prompt([("zomato l", "Food"), ("ajaykuma", "Family")])
    assert prompt.startswith(SYSTEM_PROMPT)
    assert "- zomato l → Food" in prompt
    assert "- ajaykuma → Family" in prompt

import asyncio
import json

import pytest

import ai_service


def _patch_chat(monkeypatch, payload: dict):
    async def fake_chat(system_prompt, user_prompt):
        return json.dumps(payload)
    monkeypatch.setattr(ai_service, "_chat", fake_chat)


def test_generate_quiz_valid(monkeypatch):
    _patch_chat(monkeypatch, {
        "question": "2+2 nechiga teng?",
        "options": ["3", "4", "5", "6"],
        "correct_index": 1,
        "explanation": "2+2=4",
    })
    result = asyncio.run(ai_service.generate_quiz("matematika"))
    assert result["correct_index"] == 1
    assert len(result["options"]) == 4


def test_generate_quiz_bad_correct_index_raises(monkeypatch):
    _patch_chat(monkeypatch, {
        "question": "q?",
        "options": ["a", "b"],
        "correct_index": 5,
        "explanation": "",
    })
    with pytest.raises(ai_service.ContentValidationError):
        asyncio.run(ai_service.generate_quiz())


def test_generate_quiz_missing_options_raises(monkeypatch):
    _patch_chat(monkeypatch, {"question": "q?", "options": [], "correct_index": 0})
    with pytest.raises(ai_service.ContentValidationError):
        asyncio.run(ai_service.generate_quiz())


def test_generate_poll_valid(monkeypatch):
    _patch_chat(monkeypatch, {"question": "Qaysi tilni yaxshi ko'rasiz?", "options": ["Python", "Go"]})
    result = asyncio.run(ai_service.generate_poll())
    assert len(result["options"]) == 2


def test_generate_poll_too_many_options_raises(monkeypatch):
    _patch_chat(monkeypatch, {
        "question": "q?", "options": [f"opt{i}" for i in range(10)]
    })
    with pytest.raises(ai_service.ContentValidationError):
        asyncio.run(ai_service.generate_poll())


def test_generate_poll_too_few_options_raises(monkeypatch):
    _patch_chat(monkeypatch, {"question": "q?", "options": ["only-one"]})
    with pytest.raises(ai_service.ContentValidationError):
        asyncio.run(ai_service.generate_poll())


def test_generate_post_missing_fields_raises(monkeypatch):
    _patch_chat(monkeypatch, {"title": "", "text": "", "image_prompt": ""})
    with pytest.raises(ai_service.ContentValidationError):
        asyncio.run(ai_service.generate_post())


def test_options_truncated_to_90_chars(monkeypatch):
    long_opt = "x" * 200
    _patch_chat(monkeypatch, {
        "question": "q?",
        "options": [long_opt, "b", "c", "d"],
        "correct_index": 0,
        "explanation": "",
    })
    result = asyncio.run(ai_service.generate_quiz())
    assert len(result["options"][0]) == 90


def test_avoid_line_included_when_previous_text_given(monkeypatch):
    captured = {}

    async def fake_chat(system_prompt, user_prompt):
        captured["user_prompt"] = user_prompt
        return json.dumps({"title": "t", "text": "matn", "image_prompt": "p"})

    monkeypatch.setattr(ai_service, "_chat", fake_chat)
    asyncio.run(ai_service.generate_post("mavzu", previous_text="Avvalgi post matni"))
    assert "Avvalgi post matni" in captured["user_prompt"]


def test_brainstorm_step_asks_question_when_not_done(monkeypatch):
    _patch_chat(monkeypatch, {"done": False, "question": "Qaysi sinf uchun?"})
    result = asyncio.run(ai_service.brainstorm_step([{"role": "user", "content": "yangi kurs"}]))
    assert result == {"done": False, "question": "Qaysi sinf uchun?"}


def test_brainstorm_step_returns_brief_when_done(monkeypatch):
    _patch_chat(monkeypatch, {"done": True, "brief": "5-sinflar uchun matematika kursi, yangi guruh."})
    result = asyncio.run(ai_service.brainstorm_step([{"role": "user", "content": "matematika"}]))
    assert result["done"] is True
    assert "matematika" in result["brief"]


def test_brainstorm_step_empty_question_raises(monkeypatch):
    _patch_chat(monkeypatch, {"done": False, "question": ""})
    with pytest.raises(ai_service.ContentValidationError):
        asyncio.run(ai_service.brainstorm_step([{"role": "user", "content": "x"}]))


def test_brainstorm_step_force_finish_included_in_prompt(monkeypatch):
    captured = {}

    async def fake_chat(system_prompt, user_prompt):
        captured["system_prompt"] = system_prompt
        return json.dumps({"done": True, "brief": "yakuniy"})

    monkeypatch.setattr(ai_service, "_chat", fake_chat)
    asyncio.run(ai_service.brainstorm_step([{"role": "user", "content": "x"}], force_finish=True))
    assert "ENDI YANA SAVOL BERMA" in captured["system_prompt"]

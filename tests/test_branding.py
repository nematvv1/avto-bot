import os

import pytest
from PIL import Image

import config
from branding import add_branding


@pytest.fixture
def sample_image(tmp_path):
    path = tmp_path / "raw.png"
    img = Image.new("RGB", (400, 300), color=(20, 30, 90))
    img.save(path)
    return str(path)


def test_add_branding_produces_file(sample_image, monkeypatch, tmp_path):
    if not os.path.exists(config.LOGO_PATH):
        pytest.skip("assets/logo.png topilmadi — branding testi o'tkazib yuborildi.")

    out_dir = str(tmp_path / "generated_images")
    monkeypatch.setattr("branding.BRANDED_DIR", out_dir)

    result_path = add_branding(sample_image)
    assert os.path.exists(result_path)
    assert result_path.endswith("_branded.jpg")

    with Image.open(result_path) as img:
        assert img.size == (400, 300)


def test_add_branding_disabled_returns_original(sample_image, monkeypatch):
    monkeypatch.setattr("branding.ADD_BRANDING", False)
    result_path = add_branding(sample_image)
    assert result_path == sample_image

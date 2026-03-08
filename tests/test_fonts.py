from jpgcli.render import fonts


def test_resolve_font_stack_prefers_mac_cjk_fonts(monkeypatch) -> None:
    fonts.resolve_font_stack.cache_clear()
    monkeypatch.setattr(
        "jpgcli.render.fonts.font_manager.fontManager.ttflist",
        [
            type("FontEntry", (), {"name": "Arial Unicode MS"})(),
            type("FontEntry", (), {"name": "Hiragino Sans GB"})(),
            type("FontEntry", (), {"name": "DejaVu Sans"})(),
        ],
    )
    assert fonts.resolve_font_stack()[0] == "Hiragino Sans GB"
    fonts.resolve_font_stack.cache_clear()


def test_resolve_font_stack_falls_back_to_arial_unicode(monkeypatch) -> None:
    fonts.resolve_font_stack.cache_clear()
    monkeypatch.setattr(
        "jpgcli.render.fonts.font_manager.fontManager.ttflist",
        [
            type("FontEntry", (), {"name": "Arial Unicode MS"})(),
            type("FontEntry", (), {"name": "DejaVu Sans"})(),
        ],
    )
    assert fonts.resolve_font_stack()[0] == "Arial Unicode MS"
    fonts.resolve_font_stack.cache_clear()


def test_resolve_font_stack_uses_dejavu_as_last_resort(monkeypatch) -> None:
    fonts.resolve_font_stack.cache_clear()
    monkeypatch.setattr(
        "jpgcli.render.fonts.font_manager.fontManager.ttflist",
        [
            type("FontEntry", (), {"name": "DejaVu Sans"})(),
        ],
    )
    assert fonts.resolve_font_stack() == ["DejaVu Sans"]
    fonts.resolve_font_stack.cache_clear()

from app.services import visual


def test_generate_svg_is_valid():
    svg = visual.generate_svg("鸡蛋", 5.0)
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "🥚" in svg


def test_generate_svg_partial():
    # 1.2 个拳头：1 个完整图标 + 1 个淡化图标
    svg = visual.generate_svg("猪肉", 1.2)
    assert 'opacity="0.45"' in svg

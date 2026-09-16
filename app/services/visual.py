"""生成「斤两可视化」SVG 图片。

把「300 克猪肉 ≈ 1.2 个拳头」这种文字，
变成一张看得懂的图：画一行拳头/鸡蛋的图标，数量对应用量。
"""
import math

from .portion import FOODS

EMOJI_FONT = "Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif"
MAX_SHOWN = 10  # 最多画 10 个图标，再多就用 ×N 标注


def generate_svg(food: str, count: float) -> str:
    """根据「约等于多少个参照物」生成一张 SVG 图。"""
    info = FOODS[food]
    ref_emoji = info["ref_emoji"]
    food_emoji = info["food_emoji"]

    full = math.floor(count)
    frac = count - full

    shown = min(full, MAX_SHOWN)
    show_frac = 1 if (frac >= 0.05 and full < MAX_SHOWN) else 0
    if shown == 0 and show_frac == 0:
        show_frac = 1  # 极小的量，也显示一个淡化的图标

    size = 46
    gap = 8
    total = shown + show_frac
    row_width = total * (size + gap) - gap

    width = max(row_width + 20, 170)
    height = 128

    parts = [
        # 左上角：食材本身的小图标
        f'<text x="10" y="30" font-size="30" font-family="{EMOJI_FONT}">{food_emoji}</text>'
    ]

    # 一行参照物图标
    y = 106
    x = 10
    for _ in range(shown):
        parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-family="{EMOJI_FONT}">{ref_emoji}</text>'
        )
        x += size + gap
    if show_frac:
        parts.append(
            f'<text x="{x}" y="{y}" font-size="{int(size * 0.6)}" opacity="0.45" '
            f'font-family="{EMOJI_FONT}">{ref_emoji}</text>'
        )
    if full > MAX_SHOWN:
        parts.append(
            f'<text x="{x + size}" y="{y}" font-size="20" fill="#a8a29e" '
            f'font-family="sans-serif">×{full}</text>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" rx="16" fill="#fafafa"/>'
        + "".join(parts)
        + "</svg>"
    )
    return svg

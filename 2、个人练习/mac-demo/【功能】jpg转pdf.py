"""
图片转PDF工具
修改下方 IMAGE_FOLDER 和 OUTPUT_PDF 后直接运行即可
"""

# ─────────────────────────────────────────────
# 修改这里
IMAGE_FOLDER = r"C:\Users\MI\Downloads\金融智能文档写作平台"   # 图片所在文件夹
OUTPUT_PDF   = r"C:\Users\MI\Downloads\金融智能文档写作平台\output.pdf"  # 输出PDF路径
# ─────────────────────────────────────────────

import sys
import re
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("缺少依赖，请先安装：pip install Pillow")
    sys.exit(1)

try:
    import img2pdf
    USE_IMG2PDF = True
except ImportError:
    USE_IMG2PDF = False

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


def natural_sort_key(p: Path):
    """按文件名中的数字序号自然排序，如 1.jpg < 2.jpg < 10.jpg"""
    parts = re.split(r"(\d+)", p.stem)
    return [int(x) if x.isdigit() else x.lower() for x in parts]


def to_portrait(img: Image.Image) -> Image.Image:
    """横图自动旋转为竖屏"""
    if img.width > img.height:
        img = img.rotate(90, expand=True)
    return img


def normalize(img: Image.Image) -> tuple[Image.Image, bool]:
    """统一转为 RGB，透明通道白底处理，返回 (处理后图片, 是否被修改)"""
    original_mode = img.mode
    if img.mode in ("RGBA", "LA", "P"):
        if img.mode == "P":
            img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img, (img.mode != original_mode)


def convert(image_paths: list[Path], output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)

    if USE_IMG2PDF:
        _convert_img2pdf(image_paths, output)
    else:
        print("提示：pip install img2pdf 可获得真正无损转换")
        _convert_pillow(image_paths, output)


def _convert_img2pdf(image_paths: list[Path], output: Path):
    """img2pdf 无损转换，需要对不兼容格式写临时文件"""
    processed = []
    tmp_files = []

    for p in image_paths:
        img = Image.open(p)
        rotated = img.width > img.height
        img = to_portrait(img)
        img, mode_changed = normalize(img)

        if rotated or mode_changed:
            tmp = p.parent / f"__tmp_{p.stem}.jpg"
            img.save(tmp, "JPEG", quality=100, subsampling=0)
            processed.append(tmp)
            tmp_files.append(tmp)
        else:
            processed.append(p)

    try:
        data = img2pdf.convert([str(x) for x in processed])
        output.write_bytes(data)
        print(f"完成（无损）: {output}  共 {len(image_paths)} 页")
    finally:
        for tmp in tmp_files:
            tmp.unlink(missing_ok=True)


def _convert_pillow(image_paths: list[Path], output: Path):
    """Pillow 转换"""
    pages = []
    for p in image_paths:
        img = Image.open(p)
        img = to_portrait(img)
        img, _ = normalize(img)
        pages.append(img)

    pages[0].save(
        str(output),
        format="PDF",
        save_all=True,
        append_images=pages[1:],
    )
    print(f"完成（Pillow）: {output}  共 {len(pages)} 页")


def main():
    folder = Path(IMAGE_FOLDER)
    if not folder.is_dir():
        print(f"文件夹不存在: {folder}")
        sys.exit(1)

    images = sorted(
        (f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXT),
        key=natural_sort_key,
    )

    if not images:
        print(f"未找到图片（支持 {', '.join(SUPPORTED_EXT)}）")
        sys.exit(1)

    print(f"找到 {len(images)} 张图片，按以下顺序合并：")
    for i, p in enumerate(images, 1):
        print(f"  {i:>3}. {p.name}")

    convert(images, Path(OUTPUT_PDF))


if __name__ == "__main__":
    main()

"""Render final PDFs and contact sheets for human visual inspection.

Creates no QA-passed marker: an actual visual review is still required.
Run with the bundled Python, which provides pypdf and Pillow.
"""
from pathlib import Path
import subprocess
import json
from PIL import Image, ImageOps, ImageDraw
from pypdf import PdfReader

R = Path(__file__).resolve().parent
DEST = R / 'tmp/final_visual_review'
POPPLER = Path(r'C:\Users\asus\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe')


def contact(files, folder, prefix, width=820, height=1160):
    folder.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(files), 4):
        sheet = Image.new('RGB', (2 * width, 2 * (height + 30)), '#c6cbd0')
        draw = ImageDraw.Draw(sheet)
        for index, path in enumerate(files[start:start + 4]):
            with Image.open(path) as im:
                thumb = ImageOps.contain(im.convert('RGB'), (width - 12, height - 12))
            x = (index % 2) * width
            y = (index // 2) * (height + 30)
            draw.text((x + 8, y + 5), path.name, fill='black')
            sheet.paste(thumb, (x + (width - thumb.width) // 2, y + 30))
        sheet.save(folder / f'{prefix}_{start // 4 + 1:02}.png')


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    counts = {}
    for pdf in sorted((R / 'output/pdf').glob('*.pdf')):
        out = DEST / pdf.stem
        out.mkdir(exist_ok=True)
        subprocess.run([str(POPPLER), '-r', '100', '-png', str(pdf), str(out / 'page')], check=True)
        pages = sorted(out.glob('page-*.png'))
        count = len(PdfReader(pdf).pages)
        assert len(pages) == count
        contact(pages, out, 'contact')
        counts[pdf.name] = count
    for method in ['GDA', 'TA', 'ALNS', 'VND', 'SBRS', 'PRW']:
        contact(sorted((R / 'results/plots' / method).glob('*.png')), DEST / 'figures', method, 1000, 800)
    contact(sorted((R / 'results/plots').glob('*.png')), DEST / 'figures', 'comparison', 1000, 800)
    (DEST / 'pages.json').write_text(json.dumps(counts, indent=2), encoding='utf-8')
    print(json.dumps(counts, indent=2))


if __name__ == '__main__':
    main()

"""
Generate Arabic PDF user manual for THE QS HUB.
Uses fpdf2 with Unicode support + embedded Arabic-capable font.

Usage:
    py _generate_manual_pdf.py
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ── Arabic text handler (RTL reversal) ────────────────────────────────────────
def ar(text: str) -> str:
    """
    Very lightweight Arabic display shim.
    fpdf2 doesn't support full bidi — we handle RTL by reversing word order
    for lines that are primarily Arabic.  Latin strings are left as-is.
    """
    # If mostly ASCII (code/command blocks), leave alone
    arabic_chars = sum(1 for c in text if '؀' <= c <= 'ۿ')
    if arabic_chars < len(text) * 0.3:
        return text
    # Reverse word order for RTL display
    words = text.split()
    return ' '.join(reversed(words))


def strip_emoji(text: str) -> str:
    """Remove emoji and special Unicode symbols that Arial can't render."""
    # Map common emojis to text equivalents
    replacements = {
        '️': '[QTO]', '': '[QTO]',
        '': '[*]', '': '[*]', '': '[*]', '': '[*]',
        '': '[PDF]', '': '[DIR]', '': '[DIR]',
        '': '[DL]', '': '[UL]', '': '[SAVE]',
        '': '[AI]', '': '[OCR]', '': '[KEY]',
        '': '[OK]', '☑️': '[OK]', '☑': '[OK]',
        '❌': '[X]', '⬜': '[ ]', '': '[!]', '⚠': '[!]',
        '': '[TIP]', '⚡': '[!]', '': '[>>]',
        '️': '[PC]', '': '[PC]', '': '[PC]',
        '': '[FIX]', '': '[FIX]', '': '[SET]', '⚙': '[SET]',
        '': '[OK]', '': '[~]', '': '[!!]', '⚪': '[-]',
        '': '[NO]', '✏️': '[EDIT]', '✏': '[EDIT]',
        '️': '[GF]', '': '[GF]', '': '[BLDG]',
        '': '[FNSH]', '': '[DOOR]',
        '❓': '[?]', '': '[TEL]',
        '1️⃣': '1.', '2️⃣': '2.', '3️⃣': '3.', '4️⃣': '4.', '5️⃣': '5.',
        '━': '-',
        '️': '',   # variation selector
    }
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)
    # Remove any remaining emoji/symbols outside Latin + Arabic + common punctuation
    result = []
    for ch in text:
        cp = ord(ch)
        # Keep: Basic Latin, Latin Extended, Arabic, Arabic Presentation Forms,
        #       common symbols, RTL/LTR marks
        if (cp < 0x0600 or 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F
                or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF
                or cp in (0x200F, 0x200E, 0x0020, 0x000A, 0x000D)):
            result.append(ch)
        elif cp in (0x2713, 0x2714):   # check marks
            result.append('[OK]')
        elif cp in (0x2022, 0x2023, 0x25CF):  # bullets
            result.append('*')
        elif cp == 0x2192:             # →
            result.append('->')
        elif cp == 0x2190:             # ←
            result.append('<-')
        elif cp in (0x2014, 0x2013):   # em/en dash
            result.append('-')
        elif cp < 0x2000:
            result.append(ch)
        # else: drop
    return ''.join(result)


ROOT = os.path.dirname(os.path.abspath(__file__))
MD_PATH  = os.path.join(ROOT, 'دليل_المستخدم.md')
PDF_PATH = os.path.join(ROOT, 'دليل_المستخدم.pdf')

# ── Try to find a system font that supports Arabic ────────────────────────────
ARABIC_FONTS = [
    r'C:\Windows\Fonts\arial.ttf',
    r'C:\Windows\Fonts\calibri.ttf',
    r'C:\Windows\Fonts\times.ttf',
    r'C:\Windows\Fonts\segoeui.ttf',
    r'C:\Windows\Fonts\tahoma.ttf',
]
FONT_PATH = None
for fp in ARABIC_FONTS:
    if os.path.exists(fp):
        FONT_PATH = fp
        break

if not FONT_PATH:
    print("ERROR: No suitable font found. Trying to use DejaVu fallback...")
    FONT_PATH = None   # fpdf2 will use its built-in


class ManualPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font('main', 'B', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, 'THE QS HUB — دليل المستخدم الشامل',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font('main', 'I', 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f'صفحة {self.page_no()}', align='C')
        self.set_text_color(0, 0, 0)


def build_pdf():
    pdf = ManualPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Register font ─────────────────────────────────────────────────────────
    if FONT_PATH:
        font_name = 'main'
        pdf.add_font(font_name, '', FONT_PATH, uni=True)
        pdf.add_font(font_name, 'B', FONT_PATH, uni=True)
        pdf.add_font(font_name, 'I', FONT_PATH, uni=True)
    else:
        font_name = 'Helvetica'

    # ── Parse markdown file ───────────────────────────────────────────────────
    with open(MD_PATH, encoding='utf-8') as f:
        lines = f.readlines()

    # ── Cover page ────────────────────────────────────────────────────────────
    pdf.add_page()

    # Blue header bar
    pdf.set_fill_color(30, 80, 160)
    pdf.rect(0, 0, 210, 60, 'F')

    pdf.set_y(15)
    pdf.set_font(font_name, 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, 'THE QS HUB', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 10, 'دليل المستخدم الشامل', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # Sub-title band
    pdf.set_fill_color(240, 245, 255)
    pdf.rect(0, 60, 210, 25, 'F')
    pdf.set_y(65)
    pdf.set_font(font_name, '', 12)
    pdf.set_text_color(50, 80, 140)
    pdf.cell(0, 8, 'نظام حصر الكميات الاحترافي للفلل الإماراتية',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font(font_name, '', 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, 'من رفع ملف المشروع حتى تصدير Excel BOQ',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    pdf.set_y(100)
    pdf.set_text_color(0, 0, 0)

    # Info box
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(200, 210, 230)
    pdf.rect(30, 100, 150, 50, 'DF')
    pdf.set_font(font_name, '', 11)
    pdf.set_xy(30, 108)
    pdf.cell(150, 8, 'النسخة: 2.0', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(30)
    pdf.cell(150, 8, 'التاريخ: مايو 2026', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(30)
    pdf.cell(150, 8, 'يغطي: G — G+1 — G+2', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(30)
    pdf.cell(150, 8, 'المستخدم: المهندس / المحاسب الكمياتي', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Workflow diagram
    pdf.set_y(165)
    pdf.set_font(font_name, 'B', 11)
    pdf.set_text_color(30, 80, 160)
    pdf.cell(0, 8, 'سير العمل:', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    steps = [
        ('1.', 'رفع ملفات PDF'),
        ('2.', 'استخراج AI تلقائي'),
        ('3.', 'مراجعة وموافقة'),
        ('4.', 'حساب الكميات'),
        ('5.', 'تصدير Excel'),
    ]
    pdf.set_font(font_name, '', 10)
    pdf.set_text_color(50, 50, 50)
    y_pos = 180
    x_start = 20
    box_w = 32
    gap = 4
    for i, (icon, label) in enumerate(steps):
        x = x_start + i * (box_w + gap)
        # Arrow
        if i > 0:
            pdf.set_xy(x - gap, y_pos + 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(gap, 8, '→', align='C')
        # Box
        pdf.set_fill_color(235, 242, 255)
        pdf.set_draw_color(150, 180, 230)
        pdf.rect(x, y_pos, box_w, 20, 'DF')
        pdf.set_xy(x, y_pos + 2)
        pdf.set_text_color(30, 80, 160)
        pdf.cell(box_w, 7, icon, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(x)
        pdf.set_font(font_name, '', 7)
        pdf.set_text_color(40, 40, 80)
        pdf.cell(box_w, 6, label, align='C')

    # ── Content pages ─────────────────────────────────────────────────────────
    pdf.add_page()

    # Color palette
    BLUE     = (30, 80, 160)
    BLUE_BG  = (235, 242, 255)
    TEAL     = (0, 120, 110)
    TEAL_BG  = (230, 248, 245)
    GRAY     = (90, 90, 90)
    CODE_BG  = (40, 44, 52)
    CODE_FG  = (220, 220, 220)

    in_code = False
    code_lines = []

    def flush_code():
        nonlocal code_lines, in_code
        if not code_lines:
            return
        block = '\n'.join(code_lines)
        h = min(len(code_lines) * 5 + 6, 120)
        pdf.set_fill_color(*CODE_BG)
        pdf.set_draw_color(60, 60, 70)
        cur_y = pdf.get_y()
        if cur_y + h > 270:
            pdf.add_page()
        pdf.rect(pdf.get_x(), pdf.get_y(), 170, h, 'DF')
        pdf.set_font(font_name, '', 8)
        pdf.set_text_color(*CODE_FG)
        for cl in code_lines:
            pdf.set_x(22)
            if len(cl) > 95:
                cl = cl[:92] + '...'
            pdf.cell(166, 5, cl, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        code_lines = []
        in_code = False

    def write_paragraph(text: str, size=10, bold=False, color=(0,0,0), indent=0):
        if pdf.get_y() > 270:
            pdf.add_page()
        style = 'B' if bold else ''
        pdf.set_font(font_name, style, size)
        pdf.set_text_color(*color)
        pdf.set_x(20 + indent)
        # Wrap long lines
        lines_out = []
        words = text.split()
        cur = ''
        for w in words:
            test = (cur + ' ' + w).strip()
            # Rough char width estimate
            if len(test) > 90:
                lines_out.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines_out.append(cur)
        for ln in lines_out:
            if pdf.get_y() > 275:
                pdf.add_page()
            pdf.set_x(20 + indent)
            pdf.cell(170 - indent, 6, ln, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    skip_next_separator = False

    for raw_line in lines:
        line = strip_emoji(raw_line.rstrip('\n'))

        # Code block toggle
        if line.startswith('```'):
            if in_code:
                flush_code()
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        # Strip leading/trailing spaces
        stripped = line.strip()

        if not stripped:
            pdf.ln(2)
            continue

        # Horizontal rule
        if stripped.startswith('---'):
            if pdf.get_y() > 10:
                pdf.set_draw_color(180, 190, 210)
                pdf.set_line_width(0.4)
                pdf.line(20, pdf.get_y()+1, 190, pdf.get_y()+1)
                pdf.set_line_width(0.2)
                pdf.ln(4)
            continue

        # H1
        if stripped.startswith('# ') and not stripped.startswith('##'):
            flush_code()
            text = re.sub(r'^#+\s*', '', stripped)
            text = re.sub(r'[*_`]', '', text)
            if pdf.get_y() > 20:
                pdf.add_page()
            pdf.set_fill_color(*BLUE)
            pdf.rect(0, pdf.get_y(), 210, 14, 'F')
            pdf.set_font(font_name, 'B', 16)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 14, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            pdf.set_text_color(0, 0, 0)
            pdf.ln(4)
            continue

        # H2
        if stripped.startswith('## '):
            flush_code()
            text = re.sub(r'^#+\s*', '', stripped)
            text = re.sub(r'[*_`]', '', text)
            if pdf.get_y() > 260:
                pdf.add_page()
            pdf.set_fill_color(*BLUE_BG)
            pdf.set_draw_color(*BLUE)
            pdf.rect(20, pdf.get_y(), 170, 10, 'DF')
            pdf.set_font(font_name, 'B', 13)
            pdf.set_text_color(*BLUE)
            pdf.cell(0, 10, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
            continue

        # H3
        if stripped.startswith('### '):
            flush_code()
            text = re.sub(r'^#+\s*', '', stripped)
            text = re.sub(r'[*_`]', '', text)
            if pdf.get_y() > 265:
                pdf.add_page()
            pdf.set_fill_color(*TEAL_BG)
            pdf.rect(20, pdf.get_y(), 170, 8, 'F')
            pdf.set_font(font_name, 'B', 11)
            pdf.set_text_color(*TEAL)
            pdf.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
            continue

        # H4
        if stripped.startswith('#### '):
            flush_code()
            text = re.sub(r'^#+\s*', '', stripped)
            text = re.sub(r'[*_`]', '', text)
            pdf.set_font(font_name, 'B', 10)
            pdf.set_text_color(*GRAY)
            pdf.set_x(20)
            pdf.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
            continue

        # Blockquote (> text)
        if stripped.startswith('>'):
            text = stripped.lstrip('> ').strip()
            text = re.sub(r'[*_`]', '', text)
            if pdf.get_y() > 270:
                pdf.add_page()
            pdf.set_fill_color(255, 248, 220)
            pdf.set_draw_color(220, 180, 0)
            pdf.rect(22, pdf.get_y(), 166, 8, 'DF')
            pdf.set_font(font_name, 'I', 9)
            pdf.set_text_color(100, 80, 0)
            pdf.set_x(25)
            if len(text) > 90:
                text = text[:87] + '...'
            pdf.cell(163, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
            continue

        # Table rows (| ... |)
        if stripped.startswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            # Skip separator rows
            if all(set(c) <= set('-: ') for c in cells if c):
                continue
            # Clean markdown from cells
            cells = [re.sub(r'[*_`]', '', c) for c in cells]
            if pdf.get_y() > 270:
                pdf.add_page()
            n = len(cells)
            if n == 0:
                continue
            col_w = 170 / n
            # Detect header by checking if previous non-empty line started with |
            # Simple: make all table rows look like data rows, alternate fill
            row_fill = (248, 250, 252) if not hasattr(pdf, '_table_row') or pdf._table_row % 2 == 0 else (255, 255, 255)
            if not hasattr(pdf, '_table_row'):
                pdf._table_row = 0
            pdf._table_row += 1
            pdf.set_fill_color(*row_fill)
            pdf.set_draw_color(200, 210, 230)
            x_start = 20
            y_now = pdf.get_y()
            pdf.set_font(font_name, '', 8)
            pdf.set_text_color(30, 30, 30)
            for i, cell_text in enumerate(cells):
                x = x_start + i * col_w
                pdf.set_xy(x, y_now)
                if len(cell_text) > int(col_w / 2):
                    cell_text = cell_text[:int(col_w / 2)] + '..'
                pdf.cell(col_w, 6, cell_text, border=1, fill=True,
                         new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_y(y_now + 6)
            pdf.set_text_color(0, 0, 0)
            continue

        # List items (- or * or numbered)
        if stripped.startswith(('- ', '* ', '+ ')):
            text = stripped[2:]
            text = re.sub(r'[*_`]', '', text)
            if pdf.get_y() > 272:
                pdf.add_page()
            pdf.set_font(font_name, '', 10)
            pdf.set_text_color(40, 40, 40)
            pdf.set_x(25)
            pdf.cell(5, 6, '•', new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_x(30)
            if len(text) > 80:
                text = text[:77] + '...'
            pdf.cell(160, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            continue

        # Numbered list
        num_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if num_match:
            num, text = num_match.group(1), num_match.group(2)
            text = re.sub(r'[*_`]', '', text)
            if pdf.get_y() > 272:
                pdf.add_page()
            pdf.set_font(font_name, '', 10)
            pdf.set_text_color(40, 40, 40)
            pdf.set_x(24)
            pdf.cell(6, 6, f'{num}.', new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_x(30)
            if len(text) > 80:
                text = text[:77] + '...'
            pdf.cell(160, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            continue

        # Normal paragraph
        text = re.sub(r'[*_`]', '', stripped)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Remove markdown links
        if text.startswith('#'):
            continue   # leftover header marker
        write_paragraph(text)

    # Flush any remaining code block
    flush_code()

    # ── Save PDF ──────────────────────────────────────────────────────────────
    pdf.output(PDF_PATH)
    print(f'\n✓ PDF saved → {PDF_PATH}')
    print(f'  Pages: {pdf.page_no()}')
    print(f'  Font:  {FONT_PATH or "built-in"}')


if __name__ == '__main__':
    build_pdf()

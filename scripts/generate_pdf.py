from __future__ import annotations

from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "Anleitung.md"
OUTPUT = ROOT / "output" / "pdf" / "WhatsApp_Arbeitswecker_Anleitung.pdf"
DOC_COPY = ROOT / "docs" / "WhatsApp_Arbeitswecker_Anleitung.pdf"

NAVY = colors.HexColor("#14213D")
BLUE = colors.HexColor("#2563EB")
CYAN = colors.HexColor("#06B6D4")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#5C667A")
PALE = colors.HexColor("#EEF4FF")
LINE = colors.HexColor("#D7DFEA")
GREEN = colors.HexColor("#159A62")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("Noto", "/Library/Fonts/NotoSans_Regular.ttf"))
    pdfmetrics.registerFont(TTFont("Mono", "/Library/Fonts/Inconsolata_Regular.ttf"))
    pdfmetrics.registerFont(TTFont("MonoBold", "/Library/Fonts/Inconsolata_Bold.ttf"))


def add_links(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`]+)`", r'<font name="Mono">\1</font>', escaped)
    pattern = r"(https://[A-Za-z0-9./?&amp;_=%#:-]+)"
    return re.sub(pattern, r'<link href="\1" color="#2563EB">\1</link>', escaped)


def styles():
    sheet = getSampleStyleSheet()
    return {
        "body": ParagraphStyle("Body", parent=sheet["BodyText"], fontName="Noto", fontSize=9.2, leading=13.6, textColor=INK, spaceAfter=4.5 * mm),
        "h1": ParagraphStyle("H1", parent=sheet["Heading1"], fontName="Noto", fontSize=19, leading=23, textColor=NAVY, spaceBefore=7 * mm, spaceAfter=4 * mm, keepWithNext=True),
        "h2": ParagraphStyle("H2", parent=sheet["Heading2"], fontName="Noto", fontSize=13, leading=17, textColor=BLUE, spaceBefore=5 * mm, spaceAfter=2.5 * mm, keepWithNext=True),
        "lead": ParagraphStyle("Lead", parent=sheet["BodyText"], fontName="Noto", fontSize=12, leading=17, textColor=MUTED, alignment=TA_CENTER),
        "bullet": ParagraphStyle("Bullet", parent=sheet["BodyText"], fontName="Noto", fontSize=9.1, leading=13.2, leftIndent=5 * mm, firstLineIndent=-3 * mm, textColor=INK, spaceAfter=1.8 * mm),
        "quote": ParagraphStyle("Quote", parent=sheet["BodyText"], fontName="Noto", fontSize=9.2, leading=13.5, leftIndent=6 * mm, rightIndent=4 * mm, borderColor=CYAN, borderWidth=0, borderPadding=5 * mm, backColor=colors.HexColor("#E9F9FC"), textColor=INK, spaceAfter=5 * mm),
        "code": ParagraphStyle("Code", fontName="Mono", fontSize=7.6, leading=10.2, leftIndent=0, rightIndent=0, borderColor=LINE, borderWidth=0.5, borderPadding=3 * mm, backColor=colors.HexColor("#F7F9FC"), textColor=colors.HexColor("#273449"), spaceBefore=1 * mm, spaceAfter=4 * mm),
        "small": ParagraphStyle("Small", parent=sheet["BodyText"], fontName="Noto", fontSize=7.5, leading=10, textColor=MUTED),
    }


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
        canvas.setFont("Noto", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, height - 11.5 * mm, "WhatsApp-Arbeitswecker · Technische Anleitung")
        canvas.drawRightString(width - 18 * mm, 11 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def architecture_table(style_map):
    boxes = [
        ("1", "Günna", "WhatsApp-Nachricht"),
        ("2", "Meta", "Cloud API + Signatur"),
        ("3", "Bridge", "prüfen · parsen · speichern"),
        ("4", "Home Assistant", "Sensor + Alarm"),
    ]
    cells = []
    for number, title, subtitle in boxes:
        cells.append(Paragraph(f'<font color="#2563EB"><b>{number}</b></font><br/><b>{title}</b><br/><font size="7" color="#5C667A">{subtitle}</font>', style_map["body"]))
    table = Table([cells], colWidths=[39 * mm] * 4, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
    ]))
    return table


def markdown_story(style_map):
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story = []
    paragraph: list[str] = []
    code: list[str] = []
    in_code = False
    skipped_title = 0

    def flush_paragraph():
        if paragraph:
            story.append(Paragraph(add_links(" ".join(paragraph)), style_map["body"]))
            paragraph.clear()

    for line in lines:
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(Preformatted("\n".join(code), style_map["code"], maxLineLength=95))
                code.clear()
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        if line.startswith("# ") and skipped_title < 1:
            skipped_title += 1
            continue
        if line.startswith("## Technische Anleitung"):
            continue
        if line.startswith("## "):
            flush_paragraph()
            title = line[3:].strip()
            story.append(Paragraph(add_links(title), style_map["h1"]))
            if title.startswith("2. Architektur"):
                story.append(architecture_table(style_map))
                story.append(Spacer(1, 3 * mm))
            continue
        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(add_links(line[4:].strip()), style_map["h2"]))
            continue
        if line.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(add_links(line[2:].strip()), style_map["quote"]))
            continue
        if line.startswith("- [ ] "):
            flush_paragraph()
            story.append(Paragraph("□ " + add_links(line[6:].strip()), style_map["bullet"]))
            continue
        if re.match(r"^[-*] ", line):
            flush_paragraph()
            story.append(Paragraph("• " + add_links(line[2:].strip()), style_map["bullet"]))
            continue
        if re.match(r"^\d+\. ", line):
            flush_paragraph()
            number, item = line.split(". ", 1)
            story.append(Paragraph(f"{number}. " + add_links(item), style_map["bullet"]))
            continue
        if not line.strip():
            flush_paragraph()
        else:
            paragraph.append(line.strip().replace("  ", " "))
    flush_paragraph()
    return story


def build() -> None:
    register_fonts()
    style_map = styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=21 * mm, bottomMargin=17 * mm,
        title="WhatsApp-Arbeitswecker – Technische Anleitung",
        author="OrbitNestLab",
        subject="Sichere WhatsApp-Cloud-API-Anbindung an Home Assistant",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=header_footer))

    story = [Spacer(1, 25 * mm)]
    story.append(Paragraph("WHATSAPP · HOME ASSISTANT", ParagraphStyle("Kicker", fontName="Noto", fontSize=9, leading=12, textColor=CYAN, alignment=TA_CENTER, spaceAfter=7 * mm)))
    story.append(Paragraph("WhatsApp-<br/>Arbeitswecker", ParagraphStyle("Cover", fontName="Noto", fontSize=33, leading=38, textColor=NAVY, alignment=TA_CENTER, spaceAfter=9 * mm)))
    story.append(Paragraph("Technische Anleitung zur sicheren, fehlertoleranten Übernahme von Arbeitszeiten in Home Assistant", style_map["lead"]))
    story.append(Spacer(1, 15 * mm))
    story.append(architecture_table(style_map))
    story.append(Spacer(1, 18 * mm))
    info = Table([
        ["Version", "1.0"], ["Stand", "27. Oktober 2026"], ["Projekt", "OrbitNestLab/whatsapp-arbeitswecker"], ["Schutzprinzip", "Signatur · Whitelist · Deduplizierung · Secrets"],
    ], colWidths=[38 * mm, 112 * mm])
    info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Noto"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED), ("TEXTCOLOR", (1, 0), (1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE), ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story.append(info)
    story.append(PageBreak())
    story.extend(markdown_story(style_map))
    doc.build(story)
    DOC_COPY.write_bytes(OUTPUT.read_bytes())
    print(OUTPUT)


if __name__ == "__main__":
    build()

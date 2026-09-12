"""Build a visually verifiable PDF from the authoritative research Markdown."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "PROJECT_RESEARCH_AND_EVIDENCE.md"
OUTPUT = ROOT / "docs" / "PROJECT_RESEARCH_AND_EVIDENCE.pdf"
NAVY = colors.HexColor("#1F4E79")
MUTED = colors.HexColor("#5A626C")


def inline(text: str) -> str:
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"<link href='\2' color='#1F4E79'>\1</link>", text)
    text = text.replace("**", "<b>", 1).replace("**", "</b>", 1) if text.count("**") == 2 else text.replace("**", "")
    return text.replace("`", "").replace("&", "&amp;").replace("->", "-&gt;")


def footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(inch, 0.48 * inch, "Chennai compound-disruption routing | evidence manuscript")
    canvas.drawRightString(7.5 * inch, 0.48 * inch, f"Page {document.page}")
    canvas.restoreState()


def build():
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "AcademicBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5,
        leading=12.3, spaceAfter=6, alignment=TA_JUSTIFY,
    )
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=NAVY, spaceBefore=14, spaceAfter=7, keepWithNext=True)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=NAVY, spaceBefore=10, spaceAfter=5, keepWithNext=True)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.HexColor("#294E6B"), spaceBefore=7, spaceAfter=4, keepWithNext=True)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=20, firstLineIndent=-10, bulletIndent=8, spaceAfter=3)
    quote = ParagraphStyle("Quote", parent=body, leftIndent=24, rightIndent=18, textColor=colors.HexColor("#374655"), fontName="Helvetica-Oblique", spaceBefore=4, spaceAfter=8)
    code = ParagraphStyle("Code", parent=body, fontName="Courier", fontSize=7.4, leading=9.2, leftIndent=12, rightIndent=6, backColor=colors.HexColor("#F4F6F9"), borderPadding=6, spaceAfter=8)
    title = ParagraphStyle("CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=31, textColor=colors.HexColor("#1A3752"), alignment=TA_CENTER, spaceAfter=16)
    subtitle = ParagraphStyle("CoverSubtitle", parent=body, fontName="Helvetica-Oblique", fontSize=13, leading=17, textColor=MUTED, alignment=TA_CENTER)
    story = [Spacer(1, 1.55 * inch)]
    story.append(Paragraph("REPRODUCIBLE SYSTEMS AND EVALUATION REPORT", ParagraphStyle("Kicker", parent=body, fontName="Helvetica-Bold", fontSize=9, textColor=NAVY, alignment=TA_CENTER, spaceAfter=18)))
    story.append(Paragraph("Certificate-Gated Dynamic Routing<br/>under Compound Urban Disruptions", title))
    story.append(Paragraph("A Chennai-oriented integration and evidence package", subtitle))
    story.append(Spacer(1, 0.65 * inch))
    story.append(Paragraph("Execution status: Stage 10 partial, with explicit experiment gaps", ParagraphStyle("Status", parent=body, fontName="Helvetica-Bold", fontSize=10, textColor=NAVY, alignment=TA_CENTER)))
    story.append(Paragraph("Evidence regenerated September 2026", ParagraphStyle("Date", parent=body, fontSize=9, textColor=MUTED, alignment=TA_CENTER)))
    story.append(PageBreak())

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    index = 1
    in_code = False
    code_lines: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line.strip() == "\\[":
            equation: list[str] = []
            index += 1
            while index < len(lines) and lines[index].strip() != "\\]":
                equation.append(lines[index].strip())
                index += 1
            wrapped = "\n".join(textwrap.wrap(" ".join(equation), width=92))
            story.append(
                XPreformatted(
                    wrapped,
                    ParagraphStyle(
                        "Equation", parent=code, alignment=TA_CENTER,
                        backColor=None, fontSize=8.2,
                    ),
                )
            )
            index += 1
            continue
        if line.startswith("```"):
            if in_code:
                wrapped = "\n".join(
                    part
                    for source_line in code_lines
                    for part in (textwrap.wrap(source_line, width=95, subsequent_indent="  ") or [""])
                )
                story.append(XPreformatted(wrapped, code))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if line.startswith("|") and index + 1 < len(lines) and re.match(r"^\|[ :\-|]+\|$", lines[index + 1]):
            rows = [[Paragraph(inline(cell.strip()), ParagraphStyle("Cell", parent=body, fontSize=7.2, leading=8.6, spaceAfter=0)) for cell in line.strip("|").split("|")]]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([Paragraph(inline(cell.strip()), ParagraphStyle("Cell", parent=body, fontSize=7.2, leading=8.6, spaceAfter=0)) for cell in lines[index].strip("|").split("|")])
                index += 1
            table = Table(rows, colWidths=[6.5 * inch / len(rows[0])] * len(rows[0]), repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1A3752")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB5C0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.extend([table, Spacer(1, 7)])
            continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            text = inline(heading.group(2))
            story.append(Paragraph(text, {2: h1, 3: h2, 4: h3}[level]))
            if heading.group(2).startswith("Stage 1 "):
                image = ROOT / "outputs" / "maps" / "stage1_publication_before_after.png"
                if image.is_file():
                    story.append(KeepTogether([Image(str(image), width=4.8 * inch, height=3.43 * inch), Paragraph("Figure 1. Dated Stage 3 route before and after the historical-hotspot scenario blockage.", ParagraphStyle("Caption", parent=body, fontSize=8, textColor=MUTED, alignment=TA_CENTER))]))
            if heading.group(2).startswith("6.3 OpenStreetMap"):
                image = ROOT / "docs" / "evidence" / "STAGE3_GRAPH_QA_MAP.png"
                if image.is_file():
                    story.append(KeepTogether([Image(str(image), width=6.15 * inch, height=4.1 * inch), Paragraph("Figure 2. Stage 3 Chennai road-graph quality-assurance map.", ParagraphStyle("Caption2", parent=body, fontSize=8, textColor=MUTED, alignment=TA_CENTER))]))
        elif re.match(r"^\d+\.\s+", line):
            number, text = line.split(". ", 1)
            story.append(Paragraph(inline(text), bullet, bulletText=number + "."))
        elif line.startswith("- "):
            story.append(Paragraph(inline(line[2:]), bullet, bulletText="-"))
        elif line.startswith("> "):
            story.append(Paragraph(inline(line[2:]), quote))
        elif line.strip():
            story.append(Paragraph(inline(line), body))
        index += 1
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, leftMargin=inch, rightMargin=inch,
        topMargin=0.78 * inch, bottomMargin=0.72 * inch,
        title="Certificate-Gated Dynamic Routing under Compound Urban Disruptions",
        author="Research project team",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build()

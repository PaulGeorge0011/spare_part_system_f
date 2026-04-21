# -*- coding: utf-8 -*-
"""
将 项目说明书.md 转为 Word (.docx)。
仅使用 Python 标准库（zipfile + xml），无需 pip 安装。
"""
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


def escape_xml(s):
    return escape(s or "").replace("\n", "</w:t><w:br/><w:t>")


def para_text(text, bold=False):
    if bold:
        return f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>'
    return f'<w:r><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>'


def paragraph(content, heading_level=0):
    if heading_level == 1:
        return f'<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:jc w:val="center"/></w:pPr>{content}</w:p>'
    if heading_level == 2:
        return f'<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr>{content}</w:p>'
    return f"<w:p>{content}</w:p>"


def table_rows(rows, header_shade=True):
    tc = []
    for ri, row in enumerate(rows):
        tr = []
        for cell in row:
            cell_text = escape_xml(cell.replace("**", "").strip())
            shade = ""
            if header_shade and ri == 0:
                shade = '<w:shd w:val="clear" w:fill="E0E0E0"/>'
            tr.append(
                f'<w:tc><w:tcPr><w:tcW w:w="2000" w:type="dxa"/>{shade}</w:tcPr>'
                f'<w:p><w:r><w:t xml:space="preserve">{cell_text}</w:t></w:r></w:p></w:tc>'
            )
        tc.append(f"<w:tr>{''.join(tr)}</w:tr>")
    return f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders><w:top w:val="single"/><w:left w:val="single"/><w:bottom w:val="single"/><w:right w:val="single"/></w:tblBorders></w:tblPr>{"".join(tc)}</w:tbl>'


def parse_md_to_docx(md_path: Path, docx_path: Path):
    content = md_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    body_parts = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 一级标题
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = stripped[2:].strip()
            body_parts.append(paragraph(para_text(text, bold=True), heading_level=1))
            i += 1
            continue

        # 二级标题
        if re.match(r"^##\s+", stripped):
            text = re.sub(r"^##\s+", "", stripped).strip()
            body_parts.append(paragraph(para_text(text, bold=True), heading_level=2))
            i += 1
            continue

        # 三级标题
        if re.match(r"^###\s+", stripped):
            text = re.sub(r"^###\s+", "", stripped).strip()
            body_parts.append(
                f'<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr>{para_text(text, bold=True)}</w:p>'
            )
            i += 1
            continue

        # 分隔线
        if stripped == "---":
            body_parts.append('<w:p><w:r><w:t xml:space="preserve">_________________________________________________</w:t></w:r></w:p>')
            i += 1
            continue

        # 表格
        if stripped.startswith("|") and "|" in stripped[1:]:
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_str = lines[i].strip()
                cells = [c.strip() for c in row_str.split("|")[1:-1]]
                if cells and all(re.match(r"^[\s\-:]*$", c) for c in cells):
                    i += 1
                    continue
                rows.append(cells)
                i += 1
            if rows:
                body_parts.append(table_rows(rows))
                body_parts.append("<w:p/>")
            continue

        # 无序列表
        if stripped.startswith("- "):
            items = []
            while i < len(lines) and (
                lines[i].strip().startswith("- ")
                or (
                    lines[i].strip() == ""
                    and i + 1 < len(lines)
                    and lines[i + 1].strip().startswith("- ")
                )
            ):
                if lines[i].strip():
                    items.append(lines[i].strip()[2:].strip())
                i += 1
            for item in items:
                item_clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", item)
                body_parts.append(
                    f'<w:p><w:pPr><w:ind w:left="720"/></w:pPr>{para_text("• " + item_clean)}</w:p>'
                )
            continue

        # 普通段落（含 **粗体**）
        if stripped:
            parts = re.split(r"(\*\*[^*]+\*\*)", stripped)
            runs = []
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    runs.append(para_text(part[2:-2], bold=True))
                elif part:
                    runs.append(para_text(part.replace("**", "")))
            body_parts.append(paragraph("".join(runs)))
            i += 1
            continue

        if not stripped and i < len(lines) and i > 0 and lines[i - 1].strip():
            body_parts.append("<w:p/>")
        i += 1

    body = "".join(body_parts)
    body += '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'

    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
  </w:body>
</w:document>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>'''

    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

    styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="宋体" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:styleId="Heading1" w:default="0"><w:name w:val="Heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:sz w:val="28"/><w:szCs w:val="28"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2" w:default="0"><w:name w:val="Heading 2"/><w:basedOn w:val="Normal"/><w:pPr/><w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading3" w:default="0"><w:name w:val="Heading 3"/><w:basedOn w:val="Normal"/><w:pPr/><w:rPr><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Normal" w:default="1"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="宋体"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
</w:styles>'''

    core_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">备件管理系统项目说明书</dc:title></cp:coreProperties>'''

    app_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Python</Application></Properties>'''

    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", doc_rels)
        zf.writestr("word/styles.xml", styles_xml.encode("utf-8"))
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("docProps/app.xml", app_xml)

    print(f"已生成 Word 文档: {docx_path}")


def main():
    root = Path(__file__).resolve().parent.parent
    md_path = root / "项目说明书.md"
    docx_path = root / "项目说明书.docx"
    if not md_path.exists():
        print(f"未找到: {md_path}")
        sys.exit(1)
    parse_md_to_docx(md_path, docx_path)


if __name__ == "__main__":
    main()

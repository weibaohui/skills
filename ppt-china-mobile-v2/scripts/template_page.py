#!/usr/bin/env python3
"""Create one editable page seed from the China Mobile internal-report template.

Only ZIP/XML from the standard library is used. This does not author body content,
resize text, render a slide, or replace visual QA after Artifact Tool editing.
The retained masters, layouts, relationships, and media are copied byte-for-byte.

Usage (the installed default source is ../assets/internal-report-template.pptx):
  python3 template_page.py --type body --fields body-fields.json --output page.pptx
  python3 template_page.py --type cover --fields cover-fields.json --output cover.pptx

Fields, with unknown keys rejected:
  cover:   title (required), organization and date (optional; default blank)
  contents: items (exactly four nonempty, single-line strings)
  chapter: items as above, activeIndex (required integer, zero-based 0..3)
  body:    title (required; no body content is generated)
  closing: text (required; one or two lines)

Contents preserves the source's first-item highlight. Chapter is a derived page:
its current item is blue and all other item labels are gray; source boldness,
groups and numbers remain unchanged. Different item counts need structural adaptation;
this helper deliberately refuses them. Output must not already exist. Successful
stdout is JSON with output, pageType, sourcePage, slideCount, and validation counts.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import io
import json
from pathlib import Path
import posixpath
import sys
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
}
for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)

PAGE_NUMBERS = {"cover": 1, "contents": 2, "chapter": 2, "body": 3, "closing": 4}
ITEM_IDS = ("50", "51", "52", "58")
PRESENTATION = "ppt/presentation.xml"
PRESENTATION_RELS = "ppt/_rels/presentation.xml.rels"
BLUE = "0070C0"
GREY = "A6A6A6"


def q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def xml_bytes(root: ET.Element) -> bytes:
    # OPC package readers require unprefixed Types/Relationships roots.
    if root.tag in (q("ct", "Types"), q("rel", "Relationships"), q("ep", "Properties")):
        ET.register_namespace("", root.tag[1:].split("}", 1)[0])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_xml(data: bytes) -> ET.Element:
    # Preserve familiar extension prefixes when the selected slide is serialized.
    for _, (prefix, uri) in ET.iterparse(io.BytesIO(data), events=("start-ns",)):
        if prefix and not (prefix.startswith("ns") and prefix[2:].isdigit()):
            ET.register_namespace(prefix, uri)
    return ET.fromstring(data)


def text_value(value: object, name: str, *, blank: bool = False,
               multiline: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if not blank and not value.strip():
        raise ValueError(f"{name} must not be blank")
    if any(not (c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF
                    or 0xE000 <= ord(c) <= 0xFFFD
                    or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
        raise ValueError(f"{name} contains a character not allowed in XML 1.0")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if not multiline and "\n" in value:
        raise ValueError(f"{name} must be a single line")
    return value


def validate_fields(page_type: str, fields: object) -> dict:
    if not isinstance(fields, dict):
        raise ValueError("--fields must be a JSON object")
    allowed = {
        "cover": {"title", "organization", "date"},
        "contents": {"items"}, "chapter": {"items", "activeIndex"},
        "body": {"title"}, "closing": {"text"},
    }[page_type]
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
    result = dict(fields)
    if page_type in ("cover", "body"):
        result["title"] = text_value(fields.get("title"), "title")
    if page_type == "cover":
        for key in ("organization", "date"):
            result[key] = text_value(fields.get(key, ""), key, blank=True, multiline=False)
    elif page_type in ("contents", "chapter"):
        items = fields.get("items")
        if not isinstance(items, list) or len(items) != 4:
            raise ValueError("items must contain exactly four strings; other counts require structural adaptation")
        result["items"] = [text_value(item, f"items[{i}]", multiline=False)
                           for i, item in enumerate(items)]
        if page_type == "chapter":
            index = fields.get("activeIndex")
            if type(index) is not int or not 0 <= index < 4:
                raise ValueError("activeIndex must be a zero-based integer from 0 to 3")
    elif page_type == "closing":
        result["text"] = text_value(fields.get("text"), "text")
        if len(result["text"].split("\n")) > 2:
            raise ValueError("closing text supports at most two lines in the fixed frame")
    return result


def shape_by_id(root: ET.Element, shape_id: str) -> ET.Element:
    matches = []
    for shape in root.findall(".//p:sp", NS):
        props = shape.find("p:nvSpPr/p:cNvPr", NS)
        if props is not None and props.get("id") == shape_id:
            matches.append(shape)
    if len(matches) != 1:
        raise ValueError(f"source template must contain exactly one text shape with id {shape_id}")
    return matches[0]


def paragraph_with_text(original: ET.Element, text: str) -> ET.Element:
    """Keep the paragraph and its first run's styling, removing old prompt runs."""
    paragraph = deepcopy(original)
    original_run_props = original.find("a:r/a:rPr", NS)
    if original_run_props is None:
        original_run_props = original.find("a:endParaRPr", NS)
    for child in list(paragraph):
        if child.tag not in (q("a", "pPr"), q("a", "endParaRPr")):
            paragraph.remove(child)
    run = ET.Element(q("a", "r"))
    if original_run_props is not None:
        props = deepcopy(original_run_props)
        props.tag = q("a", "rPr")
        run.append(props)
    text_node = ET.SubElement(run, q("a", "t"))
    text_node.text = text
    end = paragraph.find("a:endParaRPr", NS)
    paragraph.insert(list(paragraph).index(end) if end is not None else len(paragraph), run)
    return paragraph


def replace_text(shape: ET.Element, text: str) -> None:
    body = shape.find("p:txBody", NS)
    if body is None:
        raise ValueError("source text shape has no text body")
    originals = body.findall("a:p", NS)
    if not originals:
        raise ValueError("source text shape has no paragraph")
    for paragraph in originals:
        body.remove(paragraph)
    for i, line in enumerate(text.split("\n")):
        body.append(paragraph_with_text(originals[min(i, len(originals) - 1)], line))


def replace_metadata(shape: ET.Element, organization: str, date: str) -> None:
    body = shape.find("p:txBody", NS)
    paragraphs = [] if body is None else body.findall("a:p", NS)
    if len(paragraphs) != 2:
        raise ValueError("cover metadata shape must contain organization and date in two paragraphs")
    for original, text in zip(paragraphs, (organization, date)):
        index = list(body).index(original)
        body.remove(original)
        body.insert(index, paragraph_with_text(original, text))


def set_text_color(shape: ET.Element, color: str, *, bold: bool | None = None) -> None:
    for paragraph in shape.findall("p:txBody/a:p", NS):
        properties = paragraph.findall("a:r/a:rPr", NS)
        properties += paragraph.findall("a:endParaRPr", NS)
        for props in properties:
            if bold is not None:
                props.set("b", "1" if bold else "0")
            for child in list(props):
                if child.tag in {q("a", name) for name in
                                 ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")}:
                    props.remove(child)
            fill = ET.Element(q("a", "solidFill"))
            ET.SubElement(fill, q("a", "srgbClr"), {"val": color})
            # DrawingML order: optional line, fill, effects, and font properties.
            props.insert(1 if len(props) and props[0].tag == q("a", "ln") else 0, fill)


def rels_part(part: str) -> str:
    if not part:
        return "_rels/.rels"
    return posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")


def relationship_target(owner: str, target: str) -> str:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        raise ValueError(f"internal relationship uses a URL: {target}")
    path = unquote(parsed.path)
    normalized = posixpath.normpath(path.lstrip("/") if path.startswith("/")
                                    else posixpath.join(posixpath.dirname(owner), path))
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"relationship escapes the package: {target}")
    return normalized


def reachable_parts(parts: dict[str, bytes]) -> set[str]:
    seen: set[str] = set()
    pending = [""]
    while pending:
        owner = pending.pop()
        if owner:
            if owner in seen:
                continue
            if owner not in parts:
                raise ValueError(f"missing relationship target: {owner}")
            seen.add(owner)
        relationship_part = rels_part(owner)
        if relationship_part not in parts:
            continue
        seen.add(relationship_part)
        for relationship in ET.fromstring(parts[relationship_part]):
            if relationship.get("TargetMode") == "External":
                continue
            pending.append(relationship_target(owner, relationship.attrib["Target"]))
    return seen


def update_app_properties(data: bytes) -> bytes:
    root = parse_xml(data)
    for name, value in (("Slides", "1"), ("Notes", "0"), ("HiddenSlides", "0")):
        node = root.find(f"ep:{name}", NS)
        if node is not None:
            node.text = value
    # Remove stale counts/title lists describing the original four-page deck.
    for name in ("Words", "Paragraphs", "HeadingPairs", "TitlesOfParts"):
        node = root.find(f"ep:{name}", NS)
        if node is not None:
            root.remove(node)
    return xml_bytes(root)


def validate_package(parts: dict[str, bytes], original: dict[str, bytes],
                     selected_part: str) -> dict:
    presentation = ET.fromstring(parts[PRESENTATION])
    slide_ids = presentation.findall("p:sldIdLst/p:sldId", NS)
    if len(slide_ids) != 1:
        raise ValueError("output presentation does not contain exactly one slide")
    slide_parts = [name for name in parts if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
    if slide_parts != [selected_part]:
        raise ValueError(f"unexpected output slide parts: {slide_parts}")
    relationship_count = 0
    for name, data in parts.items():
        if not name.endswith(".rels"):
            continue
        owner = "" if name == "_rels/.rels" else posixpath.join(
            posixpath.dirname(posixpath.dirname(name)), posixpath.basename(name)[:-5])
        for relationship in ET.fromstring(data):
            if relationship.get("TargetMode") == "External":
                continue
            target = relationship_target(owner, relationship.attrib["Target"])
            if target not in parts:
                raise ValueError(f"broken relationship in {name}: {target}")
            relationship_count += 1
    preserved = [name for name in original if name.startswith(
        ("ppt/slideMasters/", "ppt/slideLayouts/", "ppt/media/", "ppt/theme/"))]
    for name in preserved:
        if parts.get(name) != original[name]:
            raise ValueError(f"original template asset was removed or changed: {name}")
    for name, data in parts.items():
        if name.endswith((".xml", ".rels")):
            ET.fromstring(data)
    return {"internalRelationships": relationship_count,
            "unchangedTemplateParts": len(preserved),
            "unchangedMediaParts": sum(name.startswith("ppt/media/") for name in preserved),
            "nativeTextShapes": len(ET.fromstring(parts[selected_part]).findall(".//p:sp[p:txBody]", NS))}


def create_seed(source: Path, output: Path, page_type: str, fields: dict) -> dict:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"output directory does not exist: {output.parent}")
    with ZipFile(source) as archive:
        infos = {info.filename: info for info in archive.infolist() if not info.is_dir()}
        original = {name: archive.read(name) for name in infos}
    parts = dict(original)
    page_number = PAGE_NUMBERS[page_type]
    selected_part = f"ppt/slides/slide{page_number}.xml"
    slide = parse_xml(parts[selected_part])
    if page_type == "cover":
        replace_text(shape_by_id(slide, "2"), fields["title"])
        replace_metadata(shape_by_id(slide, "5"), fields["organization"], fields["date"])
    elif page_type in ("contents", "chapter"):
        for shape_id, item in zip(ITEM_IDS, fields["items"]):
            replace_text(shape_by_id(slide, shape_id), item)
        if page_type == "chapter":
            for index, shape_id in enumerate(ITEM_IDS):
                set_text_color(shape_by_id(slide, shape_id),
                               BLUE if index == fields["activeIndex"] else GREY)
    elif page_type == "body":
        layout = ET.fromstring(parts["ppt/slideLayouts/slideLayout4.xml"])
        title = deepcopy(shape_by_id(layout, "10"))
        if any(name.startswith("{" + NS["r"] + "}") for element in title.iter() for name in element.attrib):
            raise ValueError("layout title unexpectedly contains relationships; adapt the copy logic")
        replace_text(title, fields["title"])
        placeholder = title.find("p:nvSpPr/p:nvPr/p:ph", NS)
        if placeholder is not None:
            placeholder.attrib.pop("hasCustomPrompt", None)
        tree = slide.find("p:cSld/p:spTree", NS)
        if tree is None or tree.findall("p:sp", NS):
            raise ValueError("source body slide must have an empty shape tree")
        tree.append(title)
    else:
        closing = shape_by_id(slide, "439")
        replace_text(closing, fields["text"])
        if "\n" in fields["text"]:
            # Two lines are a derived text fit inside the original fixed frame.
            for paragraph in closing.findall("p:txBody/a:p", NS):
                props = paragraph.find("a:pPr", NS)
                for tag, value in (("lnSpc", "100000"), ("spcBef", "0"), ("spcAft", "0")):
                    spacing = props.find("a:" + tag, NS)
                    if spacing is None:
                        spacing = ET.SubElement(props, q("a", tag))
                    spacing.clear()
                    ET.SubElement(spacing, q("a", "spcPct"), {"val": value})
    parts[selected_part] = xml_bytes(slide)

    presentation = parse_xml(parts[PRESENTATION])
    presentation_rels = parse_xml(parts[PRESENTATION_RELS])
    selected_rid = None
    for relationship in list(presentation_rels):
        if relationship.get("Type", "").endswith("/slide"):
            if relationship_target(PRESENTATION, relationship.attrib["Target"]) == selected_part:
                selected_rid = relationship.attrib["Id"]
            else:
                presentation_rels.remove(relationship)
    if selected_rid is None:
        raise ValueError("selected slide has no presentation relationship")
    id_list = presentation.find("p:sldIdLst", NS)
    if id_list is None:
        raise ValueError("template has no slide ID list")
    for slide_id in list(id_list):
        if slide_id.get(q("r", "id")) != selected_rid:
            id_list.remove(slide_id)
    if presentation.find("p:custShowLst", NS) is not None:
        raise ValueError("template custom shows require adaptation")
    parts[PRESENTATION] = xml_bytes(presentation)
    parts[PRESENTATION_RELS] = xml_bytes(presentation_rels)

    # A stale thumbnail would show the unfilled source cover, so omit its link.
    root_rels = parse_xml(parts["_rels/.rels"])
    for relationship in list(root_rels):
        if relationship.get("Type", "").endswith("/thumbnail"):
            root_rels.remove(relationship)
    parts["_rels/.rels"] = xml_bytes(root_rels)
    if "docProps/app.xml" in parts:
        parts["docProps/app.xml"] = update_app_properties(parts["docProps/app.xml"])
    keep = reachable_parts(parts)
    content_types = parse_xml(parts["[Content_Types].xml"])
    for override in list(content_types):
        if override.tag == q("ct", "Override") and unquote(override.attrib["PartName"].lstrip("/")) not in keep:
            content_types.remove(override)
    parts["[Content_Types].xml"] = xml_bytes(content_types)
    keep.add("[Content_Types].xml")
    parts = {name: data for name, data in parts.items() if name in keep}
    checks = validate_package(parts, original, selected_part)
    created = False
    try:
        with output.open("xb") as target:
            created = True
            with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
                for name, data in parts.items():
                    archive.writestr(infos[name], data)
        with ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError("written ZIP failed CRC verification")
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {"output": str(output), "pageType": page_type, "sourcePage": page_number,
            "slideCount": 1, "derivedPage": page_type == "chapter", "validation": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent / "../assets/internal-report-template.pptx")
    parser.add_argument("--type", required=True, choices=PAGE_NUMBERS, dest="page_type")
    parser.add_argument("--fields", type=Path, required=True, help="path to a UTF-8 JSON object file")
    parser.add_argument("--output", type=Path, required=True, help="new single-slide PPTX; must not exist")
    args = parser.parse_args()
    try:
        raw_fields = args.fields.expanduser().read_text(encoding="utf-8")
        fields = validate_fields(args.page_type, json.loads(raw_fields))
        result = create_seed(args.source.expanduser().resolve(), args.output.expanduser().resolve(), args.page_type, fields)
    except (ValueError, KeyError, OSError, ET.ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

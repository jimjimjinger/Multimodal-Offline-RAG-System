from __future__ import annotations

import html
import math
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

import fitz


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "SCIE용" / "산출물" / "도식"

CANVAS_WIDTH = 2400
CANVAS_HEIGHT = 1300
PRINT_WIDTH_IN = 7.16
PNG_WIDTH = 4300

NAVY = "#173B63"
BLUE = "#4779A7"
BLUE_FILL = "#EEF4FA"
GREEN = "#477F63"
GREEN_FILL = "#EEF7F1"
AMBER = "#A96D00"
AMBER_FILL = "#FFF6E2"
NEUTRAL = "#59636E"
NEUTRAL_FILL = "#F7F9FB"
WHITE = "#FFFFFF"
GROUP_FILL = "#F5F8FB"
LIGHT_LINE = "#AEB9C5"


@dataclass(frozen=True)
class Node:
    key: str
    x: int
    y: int
    width: int
    height: int
    title: tuple[str, ...]
    detail: tuple[str, ...] = ()
    fill: str = NEUTRAL_FILL
    stroke: str = BLUE
    title_size: int = 42
    detail_size: int = 34
    radius: int = 14

    @property
    def left(self) -> tuple[int, int]:
        return self.x, self.y + self.height // 2

    @property
    def right(self) -> tuple[int, int]:
        return self.x + self.width, self.y + self.height // 2

    @property
    def top(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y

    @property
    def bottom(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height


@dataclass(frozen=True)
class Edge:
    points: tuple[tuple[int, int], ...]
    color: str = NEUTRAL
    dashed: bool = False
    label: str = ""
    label_x: int = 0
    label_y: int = 0
    label_color: str | None = None


@dataclass
class Diagram:
    name: str
    title: str
    nodes: list[Node]
    edges: list[Edge]
    badges: list[tuple[str, str, int, int]] = field(default_factory=list)
    group_boxes: list[tuple[int, int, int, int, str, str]] = field(default_factory=list)
    divider_y: int | None = None
    diamonds: list[tuple[str, tuple[tuple[int, int], ...], tuple[str, ...]]] = field(default_factory=list)
    notes: list[tuple[int, int, int, int, str, str]] = field(default_factory=list)
    boxed_badges: bool = False


def svg_text_lines(
    lines: tuple[str, ...],
    x: float,
    y: float,
    size: int,
    color: str,
    *,
    bold: bool = False,
    line_gap: float = 1.12,
) -> str:
    weight = "700" if bold else "400"
    spans = []
    start_y = y - ((len(lines) - 1) * size * line_gap) / 2
    for index, line in enumerate(lines):
        line_y = start_y + index * size * line_gap
        spans.append(
            f'<text x="{x}" y="{line_y:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" dy="0.32em" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(line)}</text>'
        )
    return "\n".join(spans)


def svg_node(node: Node) -> str:
    title_line_gap = 1.00
    detail_line_gap = 1.08
    title_height = node.title_size + (len(node.title) - 1) * node.title_size * title_line_gap
    detail_height = 0.0
    content_gap = 0.0
    if node.detail:
        detail_height = node.detail_size + (len(node.detail) - 1) * node.detail_size * detail_line_gap
        content_gap = max(11.0, node.detail_size * 0.42)
    total_height = title_height + content_gap + detail_height
    content_top = node.y + (node.height - total_height) / 2
    title_center = content_top + title_height / 2
    detail_center = content_top + title_height + content_gap + detail_height / 2
    parts = [
        f'<rect x="{node.x}" y="{node.y}" width="{node.width}" height="{node.height}" '
        f'rx="{node.radius}" fill="{node.fill}" stroke="{node.stroke}" stroke-width="3"/>'
    ]
    parts.append(
        svg_text_lines(
            node.title,
            node.x + node.width / 2,
            title_center,
            node.title_size,
            NAVY,
            bold=True,
            line_gap=title_line_gap,
        )
    )
    if node.detail:
        parts.append(
            svg_text_lines(
                node.detail,
                node.x + node.width / 2,
                detail_center,
                node.detail_size,
                NEUTRAL,
                line_gap=detail_line_gap,
            )
        )
    return "\n".join(parts)


def svg_edge(edge: Edge) -> str:
    if edge.dashed and edge.color == LIGHT_LINE:
        segments: list[str] = []
        dash_length = 30.0
        gap_length = 22.0
        for (x1, y1), (x2, y2) in zip(edge.points, edge.points[1:]):
            dx = x2 - x1
            dy = y2 - y1
            length = math.hypot(dx, dy)
            if length == 0:
                continue
            ux = dx / length
            uy = dy / length
            position = 0.0
            while position < length:
                dash_end = min(position + dash_length, length)
                start_x = x1 + ux * position
                start_y = y1 + uy * position
                end_x = x1 + ux * dash_end
                end_y = y1 + uy * dash_end
                segments.append(
                    f'<line x1="{start_x:.1f}" y1="{start_y:.1f}" x2="{end_x:.1f}" y2="{end_y:.1f}" '
                    f'stroke="{edge.color}" stroke-width="6" stroke-linecap="butt"/>'
                )
                position += dash_length + gap_length

        return "\n".join(segments)

    points = " ".join(f"{x},{y}" for x, y in edge.points)
    dash = (
        ' stroke-dasharray="30 22"'
        if edge.dashed and edge.color == LIGHT_LINE
        else ' stroke-dasharray="13 11"'
        if edge.dashed
        else ""
    )
    return (
        f'<polyline points="{points}" fill="none" stroke="{edge.color}" stroke-width="6" '
        f'stroke-linejoin="round" stroke-linecap="round"{dash}/>'
    )


def svg_arrowhead(edge: Edge) -> str:
    previous = edge.points[-2]
    endpoint = edge.points[-1]
    dx = endpoint[0] - previous[0]
    dy = endpoint[1] - previous[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return ""
    ux = dx / length
    uy = dy / length
    px = -uy
    py = ux
    base_x = endpoint[0] - ux * 20
    base_y = endpoint[1] - uy * 20
    arrow_points = (
        endpoint,
        (base_x + px * 10, base_y + py * 10),
        (base_x - px * 10, base_y - py * 10),
    )
    point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in arrow_points)
    return f'<polygon points="{point_text}" fill="{edge.color}"/>'


def svg_edge_label(edge: Edge) -> str:
    if not edge.label:
        return ""
    label_width = max(180, len(edge.label) * 18)
    return "\n".join(
        (
            f'<rect x="{edge.label_x - label_width / 2:.1f}" y="{edge.label_y - 26}" '
            f'width="{label_width}" height="50" rx="5" fill="{WHITE}"/>',
            svg_text_lines(
                (edge.label,),
                edge.label_x,
                edge.label_y,
                28,
                edge.label_color or edge.color,
                bold=True,
            ),
        )
    )


def make_svg(diagram: Diagram) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PRINT_WIDTH_IN}in" '
        f'height="{PRINT_WIDTH_IN * CANVAS_HEIGHT / CANVAS_WIDTH:.4f}in" '
        f'viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}">',
        "<defs>",
        f'<marker id="arrow" markerWidth="14" markerHeight="14" refX="11" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 12 5 L 0 10 z" fill="{NEUTRAL}"/></marker>',
        f'<marker id="arrow-green" markerWidth="14" markerHeight="14" refX="11" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 12 5 L 0 10 z" fill="{GREEN}"/></marker>',
        f'<marker id="arrow-amber" markerWidth="14" markerHeight="14" refX="11" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 12 5 L 0 10 z" fill="{AMBER}"/></marker>',
        f'<marker id="arrow-light" markerWidth="14" markerHeight="14" refX="11" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 12 5 L 0 10 z" fill="{LIGHT_LINE}"/></marker>',
        "</defs>",
        f'<rect width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" fill="{WHITE}"/>',
    ]

    for x, y, width, height, label, color in diagram.group_boxes:
        parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" '
            f'fill="{GROUP_FILL}" stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="70" rx="18" fill="{color}"/>'
        )
        parts.append(f'<rect x="{x}" y="{y + 52}" width="{width}" height="18" fill="{color}"/>')
        parts.append(svg_text_lines((label,), x + width / 2, y + 37, 40, WHITE, bold=True))

    if diagram.divider_y is not None:
        y = diagram.divider_y
        parts.append(f'<line x1="50" y1="{y}" x2="2350" y2="{y}" stroke="{LIGHT_LINE}" stroke-width="3"/>')
        parts.append(f'<rect x="750" y="{y - 28}" width="900" height="56" fill="{WHITE}"/>')
        parts.append(svg_text_lines(("PRECOMPUTED ONCE - LOADED LOCALLY AT RUNTIME",), 1200, y, 34, NAVY, bold=True))

    # All connectors are emitted first so boxes and labels remain above them.
    for edge in diagram.edges:
        parts.append(svg_edge(edge))

    for key, points, lines in diagram.diamonds:
        color = AMBER if key == "decision" else BLUE
        fill = AMBER_FILL if key == "decision" else BLUE_FILL
        point_text = " ".join(f"{x},{y}" for x, y in points)
        parts.append(f'<polygon points="{point_text}" fill="{fill}" stroke="none"/>')
        for start, end in zip(points, points[1:] + points[:1]):
            parts.append(
                f'<line x1="{start[0]}" y1="{start[1]}" x2="{end[0]}" y2="{end[1]}" '
                f'stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
            )
        cx = sum(x for x, _ in points) / len(points)
        cy = sum(y for _, y in points) / len(points)
        parts.append(svg_text_lines(lines, cx, cy, 25, NAVY, bold=True, line_gap=0.96))

    for node in diagram.nodes:
        parts.append(svg_node(node))

    # Explicit arrowheads are emitted after nodes so they remain visible after
    # SVG/PDF conversion while ending at, rather than inside, each target box.
    for edge in diagram.edges:
        parts.append(svg_arrowhead(edge))

    # Connector labels and section headings are always above lines and boxes.
    for edge in diagram.edges:
        parts.append(svg_edge_label(edge))

    for letter, label, x, y in diagram.badges:
        color = GREEN if letter == "B" else NAVY
        badge_width = 54 if diagram.boxed_badges else 64
        badge_height = 50 if diagram.boxed_badges else 58
        title_height = 54 if diagram.boxed_badges else 62
        title_offset = 66 if diagram.boxed_badges else 76
        label_width = min(
            CANVAS_WIDTH - x - title_offset - 40,
            max(590, len(label) * (19 if diagram.boxed_badges else 22) + 54),
        )
        if diagram.boxed_badges:
            parts.append(
                f'<rect x="{x + title_offset}" y="{y - 2}" width="{label_width}" height="{title_height}" rx="9" '
                f'fill="{WHITE}" stroke="{color}" stroke-width="3"/>'
            )
        else:
            parts.append(f'<rect x="{x + 76}" y="{y - 2}" width="{label_width}" height="62" fill="{WHITE}"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="{badge_width}" height="{badge_height}" rx="10" fill="{color}"/>')
        parts.append(svg_text_lines((letter,), x + badge_width / 2, y + badge_height / 2, 29 if diagram.boxed_badges else 34, WHITE, bold=True))
        parts.append(
            f'<text x="{x + title_offset + 10}" y="{y + title_height / 2 - 1}" text-anchor="start" dominant-baseline="middle" '
            f'font-family="Arial, Helvetica, sans-serif" font-size="{31 if diagram.boxed_badges else 42}" font-weight="700" '
            f'fill="{color}">{html.escape(label)}</text>'
        )

    for x, y, width, height, text, color in diagram.notes:
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" fill="{WHITE}"/>')
        parts.append(svg_text_lines((text,), x + width / 2, y + height / 2, 29, color, bold=True))

    parts.append("</svg>")
    return "\n".join(parts)


def figure1() -> Diagram:
    nodes = [
        Node("manual", 50, 300, 230, 120, ("Robot Training", "Manual PDF"), title_size=31),
        Node("text_extract", 350, 145, 300, 100, ("Text Extraction",), fill=BLUE_FILL, title_size=35),
        Node("bge", 740, 135, 280, 120, ("BGE-M3", "Encoding"), fill=BLUE_FILL, title_size=36),
        Node("text_index", 1380, 145, 600, 100, ("Text Vector Index",), title_size=38),
        Node("image_extract", 350, 305, 300, 120, ("Image Extraction",), fill=BLUE_FILL, title_size=34),
        Node("bbox", 740, 305, 280, 120, ("BBox Candidate", "Filter"), fill=BLUE_FILL, title_size=34),
        Node("siglip", 1120, 305, 300, 120, ("SigLIP Semantic", "Ranking"), fill=BLUE_FILL, title_size=34),
        Node("image_index", 1510, 315, 650, 100, ("Image Index and Mapping",), title_size=36),
        Node("manual_context", 350, 475, 300, 120, ("Manual Context", "Definition"), fill=GREEN_FILL, stroke=GREEN, title_size=34),
        Node("stage_profiles", 740, 475, 280, 120, ("Stage Profile", "Construction"), fill=GREEN_FILL, stroke=GREEN, title_size=33),
        Node("context_map", 1380, 485, 600, 100, ("Stage Context Map",), fill=GREEN_FILL, stroke=GREEN, title_size=37),
        Node("query", 50, 895, 240, 110, ("User Query",), title_size=34),
        Node("g3", 360, 885, 300, 130, ("G3 Multimodal", "Retrieval"), fill=BLUE_FILL, title_size=34),
        Node("stage", 500, 1085, 300, 120, ("Stage Context", "Estimation"), fill=GREEN_FILL, stroke=GREEN, title_size=33),
        Node("g4", 830, 885, 340, 130, ("G4 Context-Aware", "Re-ranking"), fill=GREEN_FILL, stroke=GREEN, title_size=32),
        Node("topk", 1270, 885, 300, 130, ("Top-k Text and", "Image Evidence"), title_size=31),
        Node("llm", 1650, 895, 260, 110, ("4-bit Local LLM",), fill=BLUE_FILL, title_size=31),
        Node("guidance", 2020, 895, 300, 110, ("Training Guidance",), title_size=30),
    ]
    edges = [
        Edge(((280, 330), (315, 330), (315, 195), (350, 195))),
        Edge(((280, 360), (330, 360), (330, 365), (350, 365))),
        Edge(((280, 390), (315, 390), (315, 535), (350, 535)), GREEN),
        Edge(((650, 195), (740, 195))),
        Edge(((1020, 195), (1380, 195))),
        Edge(((650, 365), (740, 365))),
        Edge(((1020, 365), (1120, 365))),
        Edge(((1420, 365), (1510, 365))),
        Edge(((650, 535), (740, 535)), GREEN),
        Edge(((1020, 535), (1380, 535)), GREEN),
        Edge(((290, 950), (360, 950))),
        Edge(((290, 980), (325, 980), (325, 1145), (500, 1145)), GREEN),
        Edge(((660, 950), (830, 950))),
        Edge(((800, 1145), (1000, 1145), (1000, 1015)), GREEN),
        Edge(((1170, 950), (1270, 950)), GREEN),
        Edge(((1570, 950), (1650, 950))),
        Edge(((1910, 950), (2020, 950))),
        Edge(((1790, 585), (1790, 770), (1085, 770), (1085, 885)), LIGHT_LINE, True),
    ]
    return Diagram(
        name="figure1_overall_architecture",
        title="Overall architecture",
        nodes=nodes,
        edges=edges,
        badges=[
            ("A", "OFFLINE KNOWLEDGE CONSTRUCTION", 45, 35),
            ("B", "LOCAL RETRIEVAL AND RESPONSE", 45, 755),
        ],
        divider_y=670,
    )


def figure2() -> Diagram:
    nodes = [
        Node("query", 50, 175, 220, 110, ("User Query",), title_size=33),
        Node("g3", 370, 170, 320, 120, ("G3 Candidate", "Retrieval"), fill=BLUE_FILL, title_size=34),
        Node("baseline", 820, 170, 350, 120, ("Baseline Candidate", "Ranking"), title_size=34),
        Node("stage", 310, 610, 340, 120, ("Stage Context", "Estimation"), fill=GREEN_FILL, stroke=GREEN, title_size=34),
        Node("map", 310, 850, 340, 120, ("Manual-Derived", "Context Map"), fill=GREEN_FILL, stroke=GREEN, title_size=33),
        Node("g4", 1080, 610, 340, 120, ("G4 Context-Aware", "Re-ranking"), fill=GREEN_FILL, stroke=GREEN, title_size=32),
        Node("fusion", 1530, 610, 340, 120, ("Text and Image", "Score Fusion"), fill=BLUE_FILL, title_size=33),
        Node("final", 1980, 610, 300, 120, ("Final Top-k", "Evidence"), title_size=34),
        Node("fallback", 1080, 870, 340, 120, ("Low-Confidence", "G3 Fallback"), fill=AMBER_FILL, stroke=AMBER, title_size=32),
    ]
    diamond = ((730, 670), (880, 530), (1030, 670), (880, 810))
    edges = [
        Edge(((270, 230), (370, 230))),
        Edge(((690, 230), (820, 230))),
        Edge(((995, 290), (995, 520), (1250, 520), (1250, 610)), BLUE),
        Edge(((270, 255), (285, 255), (285, 670), (310, 670)), GREEN),
        Edge(((480, 850), (480, 730)), GREEN),
        Edge(((650, 670), (730, 670)), GREEN),
        Edge(((1030, 670), (1080, 670)), GREEN),
        Edge(((1420, 670), (1530, 670)), GREEN),
        Edge(((1870, 670), (1980, 670)), BLUE),
        Edge(((880, 810), (880, 930), (1080, 930)), AMBER),
        Edge(((1420, 930), (2130, 930), (2130, 730)), AMBER),
    ]
    return Diagram(
        name="figure2_g4_reranking",
        title="G4 context-aware re-ranking",
        nodes=nodes,
        edges=edges,
        badges=[
            ("A", "G3 MULTIMODAL CANDIDATE RETRIEVAL", 55, 35),
            ("B", "AUTOMATIC STAGE CONTEXT INFERENCE", 55, 400),
            ("C", "G4 SCORE FUSION AND RE-RANKING", 1080, 400),
        ],
        diamonds=[("decision", diamond, ("Stage confidence", ">= 0.45", "margin >= 0.03"))],
        boxed_badges=True,
    )


def write_drawio(diagram: Diagram, path: Path) -> None:
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net"})
    page = ET.SubElement(mxfile, "diagram", {"name": diagram.title, "id": diagram.name})
    graph = ET.SubElement(
        page,
        "mxGraphModel",
        {
            "dx": "1200",
            "dy": "650",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": str(CANVAS_WIDTH),
            "pageHeight": str(CANVAS_HEIGHT),
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    for index, (x, y, width, height, label, color) in enumerate(diagram.group_boxes, start=1):
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": f"group-{index}",
                "parent": "1",
                "vertex": "1",
                "value": label,
                "style": (
                    f"rounded=1;whiteSpace=wrap;html=1;fillColor={GROUP_FILL};strokeColor={color};"
                    "strokeWidth=3;fontFamily=Arial;fontSize=30;fontStyle=1;verticalAlign=top;spacingTop=16;"
                ),
            },
        )
        ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(width), "height": str(height), "as": "geometry"})

    for index, edge in enumerate(diagram.edges, start=1):
        style = f"endArrow=block;html=1;rounded=0;strokeColor={edge.color};strokeWidth=4;"
        if edge.dashed:
            style += "dashed=1;dashPattern=16 10;" if edge.color == LIGHT_LINE else "dashed=1;dashPattern=8 6;"
        cell = ET.SubElement(root, "mxCell", {"id": f"edge-{index}", "parent": "1", "edge": "1", "style": style, "value": edge.label})
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        array = ET.SubElement(geometry, "Array", {"as": "points"})
        for x, y in edge.points[1:-1]:
            ET.SubElement(array, "mxPoint", {"x": str(x), "y": str(y)})
        ET.SubElement(geometry, "mxPoint", {"x": str(edge.points[0][0]), "y": str(edge.points[0][1]), "as": "sourcePoint"})
        ET.SubElement(geometry, "mxPoint", {"x": str(edge.points[-1][0]), "y": str(edge.points[-1][1]), "as": "targetPoint"})

    for node in diagram.nodes:
        value = "<b>" + "<br>".join(html.escape(line) for line in node.title) + "</b>"
        if node.detail:
            value += "<br><font color='#59636E'>" + "<br>".join(html.escape(line) for line in node.detail) + "</font>"
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": node.key,
                "parent": "1",
                "vertex": "1",
                "value": value,
                "style": (
                    f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={node.fill};strokeColor={node.stroke};"
                    f"strokeWidth=3;fontFamily=Arial;fontSize={node.detail_size};fontColor={NAVY};align=center;verticalAlign=middle;"
                ),
            },
        )
        ET.SubElement(cell, "mxGeometry", {"x": str(node.x), "y": str(node.y), "width": str(node.width), "height": str(node.height), "as": "geometry"})

    for index, (key, points, lines) in enumerate(diagram.diamonds, start=1):
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": f"diamond-{index}",
                "parent": "1",
                "vertex": "1",
                "value": "<b>" + "<br>".join(lines) + "</b>",
                "style": f"rhombus;whiteSpace=wrap;html=1;fillColor={AMBER_FILL};strokeColor={AMBER};strokeWidth=3;fontFamily=Arial;fontSize=28;fontColor={NAVY};",
            },
        )
        ET.SubElement(cell, "mxGeometry", {"x": str(min(xs)), "y": str(min(ys)), "width": str(max(xs) - min(xs)), "height": str(max(ys) - min(ys)), "as": "geometry"})

    for index, (letter, label, x, y) in enumerate(diagram.badges, start=1):
        color = GREEN if letter == "B" else NAVY
        badge = ET.SubElement(root, "mxCell", {"id": f"badge-{index}", "parent": "1", "vertex": "1", "value": letter, "style": f"rounded=1;arcSize=20;whiteSpace=wrap;html=1;fillColor={color};strokeColor={color};fontFamily=Arial;fontSize={24 if diagram.boxed_badges else 28};fontStyle=1;fontColor={WHITE};"})
        ET.SubElement(badge, "mxGeometry", {"x": str(x), "y": str(y), "width": "54" if diagram.boxed_badges else "64", "height": "50" if diagram.boxed_badges else "58", "as": "geometry"})
        title_offset = 66 if diagram.boxed_badges else 76
        label_width = min(
            CANVAS_WIDTH - x - title_offset - 40,
            max(590, len(label) * (19 if diagram.boxed_badges else 22) + 54),
        )
        title_style = (
            f"rounded=1;arcSize=10;html=1;strokeColor={color};strokeWidth=3;fillColor={WHITE};"
            f"align=left;spacingLeft=8;verticalAlign=middle;fontFamily=Arial;fontSize=27;fontStyle=1;fontColor={color};"
            if diagram.boxed_badges
            else f"text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontFamily=Arial;fontSize=34;fontStyle=1;fontColor={color};"
        )
        title = ET.SubElement(root, "mxCell", {"id": f"title-{index}", "parent": "1", "vertex": "1", "value": label, "style": title_style})
        ET.SubElement(title, "mxGeometry", {"x": str(x + title_offset), "y": str(y - 2), "width": str(label_width), "height": "54" if diagram.boxed_badges else "62", "as": "geometry"})

    ET.indent(mxfile, space="  ")
    path.write_text(ET.tostring(mxfile, encoding="unicode"), encoding="utf-8")


def export_svg(svg: str, svg_path: Path, pdf_path: Path, png_path: Path) -> None:
    svg_path.write_text(svg, encoding="utf-8")
    source = fitz.open(stream=svg.encode("utf-8"), filetype="svg")
    pdf_path.write_bytes(source.convert_to_pdf())
    pdf = fitz.open(pdf_path)
    scale = PNG_WIDTH / pdf[0].rect.width
    pixmap = pdf[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    pixmap.set_dpi(600, 600)
    pixmap.save(png_path)


def build() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for diagram in (figure1(), figure2()):
        base = OUTPUT_DIR / diagram.name
        svg_path = base.with_suffix(".svg")
        pdf_path = base.with_suffix(".pdf")
        png_path = base.with_suffix(".png")
        drawio_path = base.with_suffix(".drawio")
        export_svg(make_svg(diagram), svg_path, pdf_path, png_path)
        write_drawio(diagram, drawio_path)
        generated.extend((drawio_path, svg_path, pdf_path, png_path))
    return generated


if __name__ == "__main__":
    for generated_path in build():
        print(generated_path)

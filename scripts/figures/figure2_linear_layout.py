import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 2400
HEIGHT = 1450

NAVY = (27, 59, 99)
BODY = (88, 97, 108)
BLUE = (77, 120, 157)
GREEN = (72, 126, 98)
AMBER = (170, 108, 0)
WHITE = (255, 255, 255)
BLUE_FILL = (238, 244, 250)
GREEN_FILL = (239, 248, 242)
NEUTRAL_FILL = (248, 250, 252)
AMBER_FILL = (255, 248, 230)


def font(size, *, bold=False, language="en"):
    if language == "ko":
        path = Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf")
    else:
        path = Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf")
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def centered_lines(draw, box, lines, text_font, fill, spacing=7):
    x1, y1, x2, y2 = box
    bounds = [draw.textbbox((0, 0), line, font=text_font) for line in lines]
    heights = [bound[3] - bound[1] for bound in bounds]
    total = sum(heights) + spacing * max(0, len(lines) - 1)
    y = y1 + ((y2 - y1) - total) / 2
    for line, bound, height in zip(lines, bounds, heights):
        width = bound[2] - bound[0]
        draw.text((x1 + ((x2 - x1) - width) / 2, y), line, font=text_font, fill=fill)
        y += height + spacing


def badge(draw, letter, box, *, color, language):
    draw.rounded_rectangle(box, radius=12, fill=color)
    centered_lines(draw, box, [letter], font(31, bold=True, language=language), WHITE, spacing=0)


def draw_node(
    draw,
    box,
    title_lines,
    detail_lines=(),
    *,
    fill=NEUTRAL_FILL,
    outline=BLUE,
    title_size=31,
    detail_size=20,
    title_ratio=0.48,
    language="en",
):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=16, fill=fill, outline=outline, width=3)
    split = y1 + int((y2 - y1) * title_ratio)
    centered_lines(
        draw,
        (x1 + 14, y1 + 14, x2 - 14, split),
        title_lines,
        font(title_size, bold=True, language=language),
        NAVY,
        spacing=1,
    )
    if detail_lines:
        centered_lines(
            draw,
            (x1 + 14, split, x2 - 14, y2 - 14),
            detail_lines,
            font(detail_size, language=language),
            BODY,
            spacing=5,
        )


def draw_path_arrow(draw, points, color, width=6, head=15):
    draw.line(points, fill=color, width=width, joint="curve")
    start, end = points[-2], points[-1]
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    left = (
        end[0] - head * math.cos(angle - math.pi / 6),
        end[1] - head * math.sin(angle - math.pi / 6),
    )
    right = (
        end[0] - head * math.cos(angle + math.pi / 6),
        end[1] - head * math.sin(angle + math.pi / 6),
    )
    draw.polygon((end, left, right), fill=color)


def labels(language):
    if language == "ko":
        return {
            "a_title": "G3 멀티모달 후보 검색",
            "b_title": "실습 단계 문맥 자동 추정",
            "c_title": "G4 점수 결합 및 재순위화",
            "query_title": ["사용자 질문"],
            "g3_title": ["G3 후보 검색"],
            "g3_detail": ["텍스트 + 이미지 검색", "페이지 근접도", "BBox 필터 기반 사전 계산", "SigLIP 매핑"],
            "base_title": ["G3 기본 후보"],
            "base_detail": ["텍스트·이미지·기본 점수"],
            "stage_title": ["실습 단계 추정"],
            "stage_detail": ["BGE-M3 프로파일 유사도", "1위 점수 + 1위/2위 점수 차이"],
            "map_title": ["매뉴얼 기반 문맥 맵"],
            "map_detail": ["페이지·제목·핵심어", "평가 정답 미포함"],
            "decision": ["신뢰 가능?", "점수 ≥ 0.45", "점수 차이 ≥", "0.03"],
            "accepted": "적용",
            "low": "낮은 신뢰도",
            "g4_title": ["G4 상황 인지형", "재순위화"],
            "g4_detail": ["1. 단계-페이지 후보 추가", "2. 페이지·핵심어·절 점수 계산", "3. G3 후보 순위 보정"],
            "fusion_title": ["분리 점수", "결합"],
            "fusion_detail": ["텍스트 = 기본 + 0.28 × 단계", "이미지 = 기본 + 0.50 × 단계 × 순위", "+ 0.25 × 단계-페이지"],
            "final_title": ["최종 상위 k개", "근거"],
            "final_detail": ["텍스트 근거", "+ 이미지 근거"],
            "fallback_title": ["저신뢰도", "대체 경로"],
            "fallback_detail": ["기존 G3 순위 유지"],
        }
    return {
        "a_title": "G3 MULTIMODAL CANDIDATE RETRIEVAL",
        "b_title": "AUTOMATIC STAGE CONTEXT INFERENCE",
        "c_title": "G4 SCORE FUSION AND RE-RANKING",
        "query_title": ["User", "Query"],
        "g3_title": ["G3 Candidate", "Retrieval"],
        "g3_detail": ["text + image retrieval", "page proximity", "precomputed BBox-filtered", "SigLIP mapping"],
        "base_title": ["Baseline", "Candidates"],
        "base_detail": ["text, images, base scores"],
        "stage_title": ["Stage Estimation"],
        "stage_detail": ["BGE-M3 profile similarity", "top-1 score + top-1/top-2 margin"],
        "map_title": ["Manual-Derived Map"],
        "map_detail": ["pages, headings, keywords", "no evaluation labels"],
        "decision": ["Confident?", "score >= 0.45", "margin >= 0.03"],
        "accepted": "accepted",
        "low": "low confidence",
        "g4_title": ["G4 Context-Aware", "Re-ranking"],
        "g4_detail": ["1. Add stage-page candidates", "2. Score page, keyword, section", "3. Adjust the G3 candidate ranks"],
        "fusion_title": ["Separate Score", "Fusion"],
        "fusion_detail": ["Text = base + 0.28 x stage", "Image = base + 0.50 x stage x rank", "+ 0.25 x stage-page"],
        "final_title": ["Final Top-k", "Evidence"],
        "final_detail": ["text evidence", "+ image evidence"],
        "fallback_title": ["Low-Confidence", "Fallback"],
        "fallback_detail": ["keep the original G3 ranking"],
    }


def create_figure(output_path, language="en"):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = labels(language)
    image = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)

    badge(draw, "A", (50, 40, 112, 98), color=NAVY, language=language)
    draw.text((132, 47), text["a_title"], font=font(39, bold=True, language=language), fill=NAVY)
    badge(draw, "B", (50, 690, 112, 748), color=GREEN, language=language)
    draw.text((132, 697), text["b_title"], font=font(37, bold=True, language=language), fill=GREEN)
    badge(draw, "C", (1260, 500, 1325, 558), color=NAVY, language=language)
    draw.text((1340, 508), text["c_title"], font=font(29 if language == "en" else 31, bold=True, language=language), fill=NAVY)

    query_box = (55, 470, 300, 650)
    g3_box = (430, 200, 825, 455)
    base_box = (955, 235, 1310, 420)
    stage_box = (430, 830, 825, 1055)
    map_box = (430, 1125, 825, 1355)
    diamond = [(1068, 818), (1202, 945), (1068, 1072), (938, 945)]
    g4_box = (1225, 650, 1580, 970)
    fusion_box = (1640, 650, 1995, 970)
    final_box = (2055, 650, 2370, 970)
    fallback_box = (1240, 1080, 1600, 1300)

    draw_node(draw, query_box, text["query_title"], title_size=36, title_ratio=1.0, language=language)
    draw_node(draw, g3_box, text["g3_title"], text["g3_detail"], fill=BLUE_FILL, title_size=32, detail_size=21, title_ratio=0.43, language=language)
    draw_node(draw, base_box, text["base_title"], text["base_detail"], title_size=35, detail_size=24, title_ratio=0.58, language=language)
    draw_node(draw, stage_box, text["stage_title"], text["stage_detail"], fill=GREEN_FILL, outline=GREEN, title_size=34, detail_size=23, title_ratio=0.50, language=language)
    draw_node(draw, map_box, text["map_title"], text["map_detail"], outline=GREEN, title_size=31, detail_size=24, title_ratio=0.52, language=language)

    draw.polygon(diamond, fill=AMBER_FILL)
    draw.line(diamond + [diamond[0]], fill=AMBER, width=3, joint="curve")
    centered_lines(draw, (970, 850, 1168, 1038), text["decision"], font(27, bold=True, language=language), NAVY, spacing=4)

    draw_node(draw, g4_box, text["g4_title"], text["g4_detail"], fill=GREEN_FILL, outline=GREEN, title_size=31, detail_size=20, title_ratio=0.45, language=language)
    draw_node(draw, fusion_box, text["fusion_title"], text["fusion_detail"], fill=BLUE_FILL, title_size=31, detail_size=18, title_ratio=0.48, language=language)
    draw_node(draw, final_box, text["final_title"], text["final_detail"], title_size=31, detail_size=22, title_ratio=0.55, language=language)
    draw_node(draw, fallback_box, text["fallback_title"], text["fallback_detail"], fill=AMBER_FILL, outline=AMBER, title_size=31, detail_size=22, title_ratio=0.58, language=language)

    # A creates the G3 candidates and routes them into the C-stage re-ranker.
    draw_path_arrow(draw, [(300, 560), (365, 560), (365, 328), (430, 328)], BODY)
    draw_path_arrow(draw, [(825, 328), (955, 328)], BODY)
    draw_path_arrow(draw, [(1132, 420), (1132, 590), (1402, 590), (1402, 650)], BLUE)

    # B independently estimates stage context from the same user query.
    draw_path_arrow(draw, [(300, 600), (350, 600), (350, 945), (430, 945)], GREEN)
    draw_path_arrow(draw, [(625, 1125), (625, 1055)], GREEN)
    draw_path_arrow(draw, [(825, 945), (938, 945)], GREEN)
    draw_path_arrow(draw, [(1202, 945), (1225, 825)], GREEN)
    draw.rectangle((1130, 835, 1220, 885), fill=WHITE)
    centered_lines(draw, (1135, 838, 1215, 882), [text["accepted"]], font(22, bold=True, language=language), GREEN, spacing=0)

    # C is linear; only the low-confidence fallback uses a bypass route.
    draw_path_arrow(draw, [(1580, 810), (1640, 810)], GREEN)
    draw_path_arrow(draw, [(1995, 810), (2055, 810)], BLUE)
    draw_path_arrow(draw, [(1068, 1072), (1068, 1190), (1240, 1190)], AMBER)
    draw.rectangle((920, 1125, 1125, 1175), fill=WHITE)
    centered_lines(draw, (925, 1128, 1120, 1172), [text["low"]], font(22, bold=True, language=language), AMBER, spacing=0)
    draw_path_arrow(draw, [(1600, 1190), (2212, 1190), (2212, 970)], AMBER)

    image.save(output_path)
    return output_path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    print(create_figure(project_root / "SCIE용" / "산출물" / "도식" / "figure2_g4_reranking.png", "en"))

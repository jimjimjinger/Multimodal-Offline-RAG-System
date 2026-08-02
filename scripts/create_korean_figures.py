import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from figure2_linear_layout import create_figure as create_linear_figure_2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = PROJECT_ROOT / "SCIE용" / "산출물" / "도식"
DESKTOP_DIR = PROJECT_ROOT.parent

FIGURE_1_SOURCE = FIGURE_DIR / "figure1_overall_architecture.png"
FIGURE_2_SOURCE = FIGURE_DIR / "figure2_g4_reranking.png"
FIGURE_1_OUTPUT = DESKTOP_DIR / "Figure_1_Revised_Overall_Architecture_Korean.png"
FIGURE_2_OUTPUT = DESKTOP_DIR / "Figure_2_Revised_G4_Process_Korean.png"

NAVY = (27, 59, 99)
BLUE = (77, 120, 157)
GREEN = (72, 126, 98)
AMBER = (170, 108, 0)
BODY = (88, 97, 108)
WHITE = (255, 255, 255)
BLUE_FILL = (238, 244, 250)
GREEN_FILL = (239, 248, 242)
NEUTRAL_FILL = (248, 250, 252)
AMBER_FILL = (255, 248, 230)


def font(size, bold=False):
    path = Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf")
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def clear_inside(draw, box, fill, inset=6):
    x1, y1, x2, y2 = box
    draw.rectangle((x1 + inset, y1 + inset, x2 - inset, y2 - inset), fill=fill)


def centered_lines(draw, box, lines, text_font, fill, spacing=7):
    x1, y1, x2, y2 = box
    measured = [draw.textbbox((0, 0), line, font=text_font) for line in lines]
    heights = [bbox[3] - bbox[1] for bbox in measured]
    total_height = sum(heights) + spacing * max(0, len(lines) - 1)
    y = y1 + ((y2 - y1) - total_height) / 2
    for line, bbox, height in zip(lines, measured, heights):
        width = bbox[2] - bbox[0]
        draw.text((x1 + ((x2 - x1) - width) / 2, y), line, font=text_font, fill=fill)
        y += height + spacing


def draw_arrow(draw, start, end, color, width=6, head=15):
    draw.line((start, end), fill=color, width=width)
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


def box_text(
    draw,
    box,
    title_lines,
    detail_lines=(),
    *,
    fill=NEUTRAL_FILL,
    title_size=32,
    detail_size=23,
    title_ratio=0.56,
):
    clear_inside(draw, box, fill)
    x1, y1, x2, y2 = box
    split = y1 + int((y2 - y1) * title_ratio)
    centered_lines(
        draw,
        (x1 + 15, y1 + 12, x2 - 15, split),
        list(title_lines),
        font(title_size, bold=True),
        NAVY,
        spacing=1,
    )
    if detail_lines:
        centered_lines(
            draw,
            (x1 + 15, split - 2, x2 - 15, y2 - 12),
            list(detail_lines),
            font(detail_size),
            BODY,
            spacing=4,
        )


def create_figure_1():
    image = Image.open(FIGURE_1_SOURCE).convert("RGB")
    draw = ImageDraw.Draw(image)

    draw.rectangle((130, 35, 1130, 105), fill=WHITE)
    draw.text((140, 48), "오프라인 지식 구축", font=font(42, bold=True), fill=NAVY)

    box_text(
        draw,
        (55, 280, 305, 500),
        ["협동 로봇", "실습 매뉴얼"],
        ["PDF"],
        fill=NEUTRAL_FILL,
        title_size=34,
        detail_size=31,
        title_ratio=0.70,
    )
    box_text(draw, (400, 100, 730, 270), ["텍스트 추출"], ["청킹"], fill=BLUE_FILL, title_size=34, detail_size=29)
    box_text(draw, (400, 300, 730, 500), ["이미지 추출"], ["정제"], fill=BLUE_FILL, title_size=34, detail_size=29)
    box_text(
        draw,
        (400, 500, 730, 665),
        ["매뉴얼 문맥"],
        ["페이지·제목·핵심어"],
        fill=GREEN_FILL,
        title_size=32,
        detail_size=25,
    )
    box_text(draw, (820, 100, 1110, 270), ["BGE-M3"], ["텍스트 임베딩"], fill=NEUTRAL_FILL, title_size=34, detail_size=26)
    box_text(
        draw,
        (820, 300, 1110, 470),
        ["텍스트-이미지", "연결"],
        ["BBox 후보 필터링", "SigLIP 의미 순위화"],
        fill=BLUE_FILL,
        title_size=31,
        detail_size=20,
        title_ratio=0.54,
    )
    box_text(
        draw,
        (820, 500, 1110, 665),
        ["실습 단계 문맥"],
        ["매뉴얼 기반 프로파일"],
        fill=GREEN_FILL,
        title_size=30,
        detail_size=23,
    )

    draw.rectangle((1215, 85, 2330, 165), fill=NAVY)
    centered_lines(
        draw,
        (1230, 90, 2315, 160),
        ["로컬 멀티모달 지식베이스"],
        font(38, bold=True),
        WHITE,
    )
    box_text(
        draw,
        (1280, 205, 2260, 325),
        ["텍스트 벡터 인덱스"],
        ["청크 + 페이지/절 메타데이터"],
        fill=WHITE,
        title_size=33,
        detail_size=25,
        title_ratio=0.55,
    )
    box_text(
        draw,
        (1280, 375, 2260, 495),
        ["이미지 인덱스 및 매핑 메타데이터"],
        ["이미지 전용 검색 + 텍스트-이미지 연결"],
        fill=WHITE,
        title_size=31,
        detail_size=24,
        title_ratio=0.55,
    )
    box_text(
        draw,
        (1280, 545, 2260, 645),
        ["실습 단계 프로파일 및 문맥 맵"],
        ["페이지 범위 + 제목 + 핵심어"],
        fill=WHITE,
        title_size=29,
        detail_size=23,
        title_ratio=0.56,
    )

    draw.rectangle((720, 708, 1680, 764), fill=WHITE)
    centered_lines(
        draw,
        (725, 712, 1675, 758),
        ["한 번 사전 계산 · 실행 시 로컬에서 불러옴"],
        font(29, bold=True),
        NAVY,
    )

    draw.rectangle((130, 785, 1060, 850), fill=WHITE)
    draw.text((140, 795), "로컬 검색 및 응답 생성", font=font(42, bold=True), fill=NAVY)

    draw.rectangle((815, 855, 1380, 910), fill=WHITE)
    centered_lines(draw, (820, 858, 1375, 906), ["로컬 인덱스 및 메타데이터"], font(25, bold=True), BLUE)
    draw.rectangle((1375, 892, 1920, 947), fill=WHITE)
    centered_lines(draw, (1380, 895, 1915, 943), ["단계 프로파일 및 문맥"], font(25, bold=True), GREEN)

    box_text(draw, (55, 1030, 280, 1200), ["사용자 질문"], fill=NEUTRAL_FILL, title_size=35, title_ratio=1.0)
    box_text(
        draw,
        (370, 970, 740, 1260),
        ["로컬 검색", "제어기"],
        ["G3 후보", "실습 단계 자동 추정"],
        fill=BLUE_FILL,
        title_size=34,
        detail_size=27,
        title_ratio=0.54,
    )
    box_text(
        draw,
        (835, 990, 1230, 1240),
        ["G4 상황 인지형", "검색"],
        ["후보 확장 및 재순위화"],
        fill=GREEN_FILL,
        title_size=33,
        detail_size=25,
        title_ratio=0.62,
    )
    box_text(draw, (1320, 1030, 1595, 1200), ["상위 k개 근거"], ["텍스트 + 이미지"], fill=NEUTRAL_FILL, title_size=31, detail_size=25)
    box_text(draw, (1685, 1030, 1970, 1200), ["4비트 로컬", "LLM"], ["오프라인 생성"], fill=BLUE_FILL, title_size=31, detail_size=23, title_ratio=0.67)
    box_text(draw, (2065, 1030, 2350, 1200), ["실습 안내", "응답"], ["텍스트 + 도식"], fill=NEUTRAL_FILL, title_size=31, detail_size=23, title_ratio=0.67)

    image.save(FIGURE_1_OUTPUT)


def create_figure_2():
    create_linear_figure_2(FIGURE_2_OUTPUT, "ko")
    return

    image = Image.open(FIGURE_2_SOURCE).convert("RGB")
    draw = ImageDraw.Draw(image)

    draw.rectangle((130, 35, 1250, 108), fill=WHITE)
    draw.text((140, 50), "G3 멀티모달 후보 검색", font=font(42, bold=True), fill=NAVY)

    box_text(draw, (55, 470, 300, 650), ["사용자 질문"], fill=NEUTRAL_FILL, title_size=36, title_ratio=1.0)
    box_text(
        draw,
        (430, 200, 825, 455),
        ["G3 후보 검색"],
        ["텍스트 + 이미지 검색", "페이지 근접도 +", "BBox 필터 기반 사전 계산", "SigLIP 매핑"],
        fill=BLUE_FILL,
        title_size=32,
        detail_size=21,
        title_ratio=0.43,
    )
    box_text(
        draw,
        (955, 235, 1310, 420),
        ["기본 후보"],
        ["텍스트·이미지·기본 점수"],
        fill=NEUTRAL_FILL,
        title_size=36,
        detail_size=25,
    )

    draw.rectangle((130, 690, 1280, 760), fill=WHITE)
    draw.text((140, 702), "실습 단계 문맥 자동 추정", font=font(39, bold=True), fill=GREEN)

    draw.rectangle((1210, 480, 2399, 580), fill=WHITE)
    draw.rounded_rectangle((1260, 500, 1325, 558), radius=12, fill=NAVY)
    centered_lines(draw, (1260, 500, 1325, 558), ["C"], font(31, bold=True), WHITE, spacing=0)
    draw.text((1340, 508), "G4 점수 결합 및 재순위화", font=font(31, bold=True), fill=NAVY)

    box_text(
        draw,
        (430, 830, 825, 1055),
        ["실습 단계 추정"],
        ["BGE-M3 프로파일 유사도", "1위 점수 + 1위/2위 점수 차이"],
        fill=GREEN_FILL,
        title_size=34,
        detail_size=23,
        title_ratio=0.50,
    )
    box_text(
        draw,
        (430, 1125, 825, 1355),
        ["매뉴얼 기반 문맥 맵"],
        ["페이지·제목·핵심어", "평가 정답 미포함"],
        fill=NEUTRAL_FILL,
        title_size=31,
        detail_size=24,
        title_ratio=0.52,
    )

    # Clear the original English decision label and redraw its local connections.
    draw.rectangle((915, 790, 1215, 1085), fill=WHITE)
    draw_arrow(draw, (825, 945), (940, 945), BODY)
    draw_arrow(draw, (1198, 945), (1225, 825), GREEN)
    draw.line(((1068, 1068), (1068, 1190)), fill=AMBER, width=6)

    diamond = [(1068, 818), (1202, 945), (1068, 1072), (938, 945)]
    draw.polygon(diamond, fill=AMBER_FILL)
    draw.line(diamond + [diamond[0]], fill=AMBER, width=3, joint="curve")
    centered_lines(
        draw,
        (970, 850, 1168, 1038),
        ["신뢰 가능?", "점수 ≥ 0.45", "점수 차이 ≥", "0.03"],
        font(27, bold=True),
        NAVY,
        spacing=4,
    )

    box_text(
        draw,
        (1225, 650, 1580, 970),
        ["G4 상황 인지형", "재순위화"],
        ["1. 단계-페이지 후보 추가", "2. 페이지·핵심어·절 점수 계산", "3. G3 후보 순위 보정"],
        fill=GREEN_FILL,
        title_size=31,
        detail_size=20,
        title_ratio=0.45,
    )
    box_text(
        draw,
        (1640, 650, 1995, 970),
        ["분리 점수", "결합"],
        ["텍스트 = 기본 + 0.28 × 단계", "이미지 = 기본 + 0.50 × 단계 × 순위", "+ 0.25 × 단계-페이지"],
        fill=BLUE_FILL,
        title_size=31,
        detail_size=18,
        title_ratio=0.48,
    )
    box_text(
        draw,
        (1240, 1080, 1600, 1300),
        ["저신뢰도", "대체 경로"],
        ["기존 G3 순위 유지"],
        fill=AMBER_FILL,
        title_size=31,
        detail_size=22,
        title_ratio=0.58,
    )
    box_text(
        draw,
        (2055, 650, 2370, 970),
        ["최종 상위 k개", "근거"],
        ["텍스트 근거", "+ 이미지 근거"],
        fill=NEUTRAL_FILL,
        title_size=31,
        detail_size=22,
        title_ratio=0.55,
    )

    draw.rectangle((1130, 835, 1220, 885), fill=WHITE)
    centered_lines(draw, (1135, 838, 1215, 882), ["적용"], font(22, bold=True), GREEN)
    draw.rectangle((920, 1125, 1125, 1175), fill=WHITE)
    centered_lines(draw, (925, 1128, 1120, 1172), ["낮은 신뢰도"], font(22, bold=True), AMBER)

    image.save(FIGURE_2_OUTPUT)


if __name__ == "__main__":
    create_figure_1()
    create_figure_2()
    print(FIGURE_1_OUTPUT)
    print(FIGURE_2_OUTPUT)

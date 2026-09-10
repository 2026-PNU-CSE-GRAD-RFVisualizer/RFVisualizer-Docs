from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


W, H = 4200, 1900
BG = "#FFFFFF"
INK = "#172033"
MUTED = "#56647A"
LINE = "#44546A"
BLUE = "#E7F0FF"
BLUE_STROKE = "#4F7DC9"
GREEN = "#E8F5E6"
GREEN_STROKE = "#5D9B59"
PURPLE = "#F1E8F7"
PURPLE_STROKE = "#8A63A6"
ORANGE = "#FFF0D8"
ORANGE_STROKE = "#D8922E"
RED = "#FDE7E5"
RED_STROKE = "#C85D55"
GRAY = "#F2F4F7"
GRAY_STROKE = "#7B8798"
CYAN = "#E5F6F7"
CYAN_STROKE = "#3D929A"

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "archive" / "paper" / "figures"
PNG_PATH = OUT_DIR / "fig1_rfvisualizer_pipeline.png"
SVG_PATH = OUT_DIR / "fig1_rfvisualizer_pipeline.svg"


def pick_font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


FONT_STAGE = pick_font(41, True)
FONT_TITLE = pick_font(40, True)
FONT_BODY = pick_font(29, False)
FONT_BODY_BOLD = pick_font(29, True)
FONT_SMALL = pick_font(25, False)
FONT_TINY = pick_font(22, False)
FONT_TAG = pick_font(25, True)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
    '<rect width="100%" height="100%" fill="#FFFFFF"/>',
    '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L12,6 L0,12 z" fill="#44546A"/></marker></defs>',
]


def sx(text):
    return escape(str(text))


def rounded_box(x1, y1, x2, y2, fill, stroke, title, lines=(), radius=28, title_size="normal"):
    d.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=fill, outline=stroke, width=4)
    svg.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="4"/>')
    title_font = FONT_TITLE if title_size == "normal" else FONT_BODY_BOLD
    line_gap = 8
    blocks = [(title, title_font, INK)] + [(line, FONT_BODY, MUTED) for line in lines]
    heights = []
    for text, font, _ in blocks:
        box = d.textbbox((0, 0), text, font=font)
        heights.append(box[3] - box[1])
    total = sum(heights) + line_gap * (len(blocks) - 1)
    cy = y1 + (y2 - y1 - total) / 2
    for (text, font, color), th in zip(blocks, heights):
        box = d.textbbox((0, 0), text, font=font)
        tw = box[2] - box[0]
        tx = x1 + (x2 - x1 - tw) / 2
        d.text((tx, cy), text, font=font, fill=color)
        weight = 700 if font in (FONT_TITLE, FONT_BODY_BOLD) else 400
        size = 40 if font == FONT_TITLE else 29
        svg.append(f'<text x="{(x1+x2)/2}" y="{cy+th}" text-anchor="middle" font-family="Malgun Gothic, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{sx(text)}</text>')
        cy += th + line_gap


def stage_header(x1, x2, num, label, fill, stroke):
    d.rounded_rectangle((x1, 65, x2, 155), radius=24, fill=fill, outline=stroke, width=3)
    text = f"{num}  {label}"
    box = d.textbbox((0, 0), text, font=FONT_STAGE)
    d.text(((x1+x2-box[2])/2, 88), text, font=FONT_STAGE, fill=INK)
    svg.append(f'<rect x="{x1}" y="65" width="{x2-x1}" height="90" rx="24" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
    svg.append(f'<text x="{(x1+x2)/2}" y="123" text-anchor="middle" font-family="Malgun Gothic, Arial, sans-serif" font-size="41" font-weight="700" fill="{INK}">{sx(text)}</text>')


def arrow(points, label=None, label_xy=None, dashed=False, width=5, color=LINE):
    d.line(points, fill=color, width=width, joint="curve")
    if len(points) >= 2:
        x0, y0 = points[-2]
        x1, y1 = points[-1]
        import math
        ang = math.atan2(y1-y0, x1-x0)
        length, wing = 24, 12
        p1 = (x1 - length*math.cos(ang) + wing*math.sin(ang), y1 - length*math.sin(ang) - wing*math.cos(ang))
        p2 = (x1 - length*math.cos(ang) - wing*math.sin(ang), y1 - length*math.sin(ang) + wing*math.cos(ang))
        d.polygon([(x1, y1), p1, p2], fill=color)
    path = "M " + " L ".join(f"{x},{y}" for x, y in points)
    dash = ' stroke-dasharray="14 10"' if dashed else ""
    svg.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arrow)"{dash}/>')
    if label and label_xy:
        lx, ly = label_xy
        box = d.textbbox((0, 0), label, font=FONT_TINY)
        d.rounded_rectangle((lx-12, ly-5, lx+box[2]+12, ly+box[3]+7), radius=8, fill=BG)
        d.text((lx, ly), label, font=FONT_TINY, fill=MUTED)
        svg.append(f'<rect x="{lx-12}" y="{ly-5}" width="{box[2]+24}" height="{box[3]+12}" rx="8" fill="#FFFFFF"/>')
        svg.append(f'<text x="{lx}" y="{ly+23}" font-family="Malgun Gothic, Arial, sans-serif" font-size="22" fill="{MUTED}">{sx(label)}</text>')


def lane_label(x, y, text, fill, stroke):
    box = d.textbbox((0, 0), text, font=FONT_TAG)
    w = box[2] + 42
    d.rounded_rectangle((x, y, x+w, y+52), radius=18, fill=fill, outline=stroke, width=3)
    d.text((x+20, y+10), text, font=FONT_TAG, fill=INK)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="52" rx="18" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')
    svg.append(f'<text x="{x+20}" y="{y+37}" font-family="Malgun Gothic, Arial, sans-serif" font-size="25" font-weight="700" fill="{INK}">{sx(text)}</text>')


# Six canonical stages. Their colors are reused by the corresponding boxes below.
stage_header(70, 690, "1", "장면 구축", BLUE, BLUE_STROKE)
stage_header(720, 1340, "2", "계측", GREEN, GREEN_STROKE)
stage_header(1370, 2030, "3", "전파 계산", PURPLE, PURPLE_STROKE)
stage_header(2060, 2720, "4", "측정 보정", ORANGE, ORANGE_STROKE)
stage_header(2750, 3410, "5", "비교 평가", CYAN, CYAN_STROKE)
stage_header(3440, 4130, "6", "3D 시각화", RED, RED_STROKE)

# Upper lane: scene reconstruction and simulation
lane_label(85, 205, "시각·기하 경로", BLUE, BLUE_STROKE)
rounded_box(80, 315, 390, 515, GRAY, GRAY_STROKE, "실내 다중시점 사진", ("링 복도 촬영",), title_size="small")
rounded_box(470, 315, 760, 515, BLUE, BLUE_STROKE, "COLMAP", ("카메라 자세", "희소 점군"))
rounded_box(840, 315, 1130, 515, BLUE, BLUE_STROKE, "PGSR 학습", ("Gaussian + 표면",))
arrow([(390, 415), (470, 415)])
arrow([(760, 415), (840, 415)])

rounded_box(1240, 240, 1580, 430, BLUE, BLUE_STROKE, "Gaussian Scene", ("실시간 시각 표현",))
rounded_box(1240, 505, 1580, 695, BLUE, BLUE_STROKE, "PGSR Surface Mesh", ("표면·평면 후보",), title_size="small")
arrow([(1130, 390), (1180, 390), (1180, 335), (1240, 335)])
arrow([(1130, 440), (1180, 440), (1180, 600), (1240, 600)])

rounded_box(1670, 425, 2075, 690, BLUE, BLUE_STROKE, "미터 좌표 정합", ("Scale · 축 · 원점", "닫힌 Proxy Scene", "재질 · TX/RX 배치"))
arrow([(1580, 600), (1670, 600)])
arrow([(1580, 335), (1620, 335), (1620, 500), (1670, 500)], label="동일 좌표계", label_xy=(1580, 445))

rounded_box(2190, 340, 2600, 615, PURPLE, PURPLE_STROKE, "Sionna RT", ("2.437 GHz (Ch. 6)", "LoS · 반사 · 회절 · 산란", "max_depth = 12"))
arrow([(2075, 555), (2130, 555), (2130, 478), (2190, 478)])

rounded_box(2700, 250, 3070, 445, PURPLE, PURPLE_STROKE, "지점 예측", ("R̂S(x)", "Calibration / Test"))
rounded_box(2700, 520, 3070, 715, PURPLE, PURPLE_STROKE, "격자 예측", ("6개 높이 Radio Map",))
arrow([(2600, 445), (2650, 445), (2650, 347), (2700, 347)])
arrow([(2600, 510), (2650, 510), (2650, 617), (2700, 617)])

# Middle/lower lane: measurement
lane_label(85, 820, "계측·데이터 경로", GREEN, GREEN_STROKE)
rounded_box(80, 930, 420, 1175, GREEN, GREEN_STROKE, "ESP32 RSSI × 5", ("원격 노드 1–4", "Gateway 로컬 노드 5", "200 ms · 이동평균 5"))
rounded_box(500, 930, 820, 1175, GREEN, GREEN_STROKE, "ESP-NOW Gateway", ("CRC · Sequence", "누락 · 중복 집계"), title_size="small")
rounded_box(900, 930, 1215, 1175, GREEN, GREEN_STROKE, "STM32F107", ("UART 115200 bps", "Checksum · Timeout"))
rounded_box(1295, 930, 1655, 1175, GREEN, GREEN_STROKE, "Serial–MQTT", ("JSON 정규화", "QoS 1 Publish"))
rounded_box(1735, 900, 2120, 1205, GREEN, GREEN_STROKE, "Backend 저장·QC", ("JSONL 원본 보존", "SQLite 정규화", "채널·범위·오류 검사", "동일 시간창 정합"))
arrow([(420, 1052), (500, 1052)], label="ESP-NOW", label_xy=(418, 1005))
arrow([(820, 1052), (900, 1052)], label="UART", label_xy=(820, 1005))
arrow([(1215, 1052), (1295, 1052)], label="Serial", label_xy=(1215, 1005))
arrow([(1655, 1052), (1735, 1052)], label="MQTT", label_xy=(1655, 1005))

rounded_box(2190, 860, 2600, 1045, ORANGE, ORANGE_STROKE, "장치 편차 보정", ("공통 위치 중앙값", "corrected_rssi"))
rounded_box(2190, 1100, 2600, 1285, ORANGE, ORANGE_STROKE, "데이터 분리", ("Calibration C1–C4", "Test T1–T10"))
arrow([(2120, 990), (2160, 990), (2160, 952), (2190, 952)])
arrow([(2395, 1045), (2395, 1100)])

# Fusion
rounded_box(3150, 790, 3560, 1025, ORANGE, ORANGE_STROKE, "보정 지점 잔차", ("e(x_i) = R(x_i) - R_S(x_i)", "Residual IDW 보간"))
arrow([(2600, 1175), (2870, 1175), (2870, 950), (3150, 950)], label="Calibration만 사용", label_xy=(2660, 1125))
arrow([(3070, 347), (3120, 347), (3120, 875), (3150, 875)], label="지점 예측", label_xy=(3070, 745))

rounded_box(3640, 805, 4100, 1015, ORANGE, ORANGE_STROKE, "보정 RF 신호장", ("R_C(x) = R_S(x) + b(x)", "공간 구조 + 실측 잔차"))
arrow([(3560, 907), (3640, 907)])

# Evaluation
rounded_box(2700, 1370, 3160, 1745, CYAN, CYAN_STROKE, "4가지 방법 비교", ("Raw Sionna RT", "Plain IDW", "Residual IDW", "Global-bias 보정", "MAE · RMSE · Bias · P95"))
arrow([(2600, 1195), (2660, 1195), (2660, 1557), (2700, 1557)], label="Test는 평가에만 사용", label_xy=(2545, 1310))
arrow([(3410, 1025), (3410, 1295), (3090, 1295), (3090, 1370)], label="보정 결과", label_xy=(3170, 1242))

# Visualization chain
rounded_box(3280, 1350, 3620, 1570, RED, RED_STROKE, "3D RF Volume", ("6개 높이", "Viewer Bundle"))
rounded_box(3710, 1260, 4110, 1510, RED, RED_STROKE, "SIBR Viewer", ("Gaussian + RF 합성", "Mesh-depth 가림", "800×480 렌더링"))
# Route the grid branch below the prediction box and around the residual box.
# This keeps the long visualization edge from crossing the residual-fusion node.
arrow([(2885, 715), (2885, 1325), (3240, 1325), (3240, 1460), (3280, 1460)], label="격자 예측", label_xy=(2910, 760))
arrow([(3640, 907), (3600, 907), (3600, 1325), (3450, 1325), (3450, 1350)], label="잔차 보정", label_xy=(3475, 1120))
arrow([(3620, 1460), (3710, 1460)])

# Notes and legend
d.text((82, 1810), "실선: 데이터/처리 흐름    모든 장면·지점·RF 격자는 동일한 미터 좌표계 사용", font=FONT_SMALL, fill=MUTED)
svg.append(f'<text x="82" y="1840" font-family="Malgun Gothic, Arial, sans-serif" font-size="25" fill="{MUTED}">실선: 데이터/처리 흐름    모든 장면·지점·RF 격자는 동일한 미터 좌표계 사용</text>')

OUT_DIR.mkdir(parents=True, exist_ok=True)
img.save(PNG_PATH, dpi=(600, 600), optimize=True)
svg.append("</svg>")
SVG_PATH.write_text("\n".join(svg), encoding="utf-8")
print(PNG_PATH)
print(SVG_PATH)

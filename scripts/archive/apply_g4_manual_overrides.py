import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from create_scie_stage_label_workbook import write_workbook  # noqa: E402
from paths import SCIE_DATA_DIR, SCIE_DIR, SCIE_EXCEL_DIR, STAGE_CONTEXT_MAP_MANUAL_PATH  # noqa: E402


CSV_PATH = STAGE_CONTEXT_MAP_MANUAL_PATH
XLSX_PATH = SCIE_EXCEL_DIR / "11_stage_context_map_manual.xlsx"
MD_PATH = SCIE_DIR / "11_stage_context_map_manual.md"


def override(text_pages, image_pages, section, content, action, evidence):
    return {
        "텍스트 페이지 범위": text_pages,
        "이미지 페이지 범위": image_pages,
        "섹션 키워드": section,
        "본문 키워드": content,
        "동작/질문 키워드": action,
        "근거": evidence,
    }


MANUAL_OVERRIDES = {
    "DART-Platform/Robot Settings": override(
        "187-201",
        "186-203",
        "Robot Settings, User Coordinates, Mount, Home Position, Cockpit",
        "DART-Platform, Robot Settings, User Coordinates, Mount, Home Position, Cockpit, Default Position, Custom Position, Apply",
        "Robot Settings, file, save, import, export, mount, coordinate, cockpit",
        "매뉴얼 6.7.1 Robot Settings section 기준",
    ),
    "TCP/툴 좌표 설정": override(
        "201-209",
        "200-210",
        "Tool Settings, Tool Center Point, TCP, Tool Coordinate",
        "Tool Settings, TCP, Tool Center Point, Tool Coordinate, offset, X, Y, Z, flange, tool frame, simulation",
        "TCP, tool coordinate, offset, X, Y, Z",
        "매뉴얼 6.7.2 Tool Settings의 TCP/Tool Center Point 설명 기준",
    ),
    "UI/시스템 정보 확인": override(
        "164-170; 349-350",
        "163-171; 348-351",
        "Program screen, Header, System Information",
        "Header, current time, menu button, System Information, Platform Version, DART-Platform",
        "time, header, system information, platform version",
        "DART-Platform 화면 구성 및 System Information section 기준",
    ),
    "네트워크/포트 연결": override(
        "148-153; 354-357",
        "147-154; 353-358",
        "Network Connection, External Device Connection, Network Settings",
        "WAN, LAN, TCP/IP, Modbus, Ethernet/IP, PROFINET, network, port, controller, external device",
        "WAN, LAN, network, port, TCP/IP, Modbus",
        "인터페이스 Network Connection 및 System Settings Network section 기준",
    ),
    "비상/Backdrive": override(
        "169-170; 178-181",
        "168-181",
        "Backdrive, menu button, brake release",
        "Backdrive, brake, servo off, joint, release, hold, emergency, recovery, manual mode",
        "Backdrive, brake release, joint, emergency",
        "DART-Platform Backdrive module section 기준",
    ),
    "사용자 관리/권한": override(
        "342-354",
        "341-355",
        "Store, Account, Supervisor Password, Safety Password",
        "user, account, supervisor, password, admin, safety password, lock, setting",
        "account, supervisor, password, admin",
        "Store account 및 Settings password section 기준",
    ),
    "상태 확인/I/O Overview": override(
        "331-338",
        "330-339",
        "Status, I/O Overview",
        "Status, I/O Overview, digital input, digital output, analog input, high, low, icon, controller, flange",
        "status, I/O Overview, digital input, high, low",
        "Status module의 I/O Overview section 기준",
    ),
    "설치/기구 고정": override(
        "84-86; 115-118",
        "83-87; 114-119",
        "Robot base fixing, hardware installation",
        "robot base, M8, bolt, torque, 20Nm, washer, positioning pin, fixed position, installation",
        "base, bolt, torque, fixing, installation",
        "빠른 설치 및 설치 매뉴얼의 로봇 베이스 고정 section 기준",
    ),
    "설치/로봇 운반": override(
        "97-98; 160-162",
        "96-99; 159-163",
        "Lifting point, robot transport, packaging box",
        "transport, lifting point, carry, shaded area, packaging, box, robot posture",
        "transport, carry, lifting point",
        "설치 매뉴얼 이동 및 설치를 위한 인양 지점 section 기준",
    ),
    "설치/마운팅 설정": override(
        "187-201",
        "186-203",
        "Robot Settings, Mount",
        "Mount, installation angle, ceiling, wall, floor, Y rotation, Z rotation, Robot Settings",
        "mount, ceiling, angle, Y, Z",
        "DART-Platform Robot Settings의 Mount 설정 section 기준",
    ),
    "설치/매니퓰레이터 연결": override(
        "119-122",
        "118-123",
        "System connection, manipulator connection",
        "manipulator cable, controller, fixing hook, system connection, cable lock, power connector",
        "manipulator cable, controller, fixing hook",
        "설치 매뉴얼 System connection section 기준",
    ),
    "설치/제품 개봉": override(
        "83; 98-104",
        "82-84; 97-105",
        "Unpacking, components, system configuration",
        "unpacking, package, box, robot, controller, components, teach pendant, cable",
        "unpack, package, box, components",
        "로봇 시작하기 패킹 뜯기 및 설치 매뉴얼 구성품 section 기준",
    ),
    "설치/컨트롤러 배치": override(
        "87-89",
        "86-90",
        "Controller placement",
        "controller, placement, ventilation, clearance, 50 mm, cable bending radius, floor",
        "controller, ventilation, clearance, 50 mm",
        "컨트롤러 배치하기 section 기준",
    ),
    "설치/케이블 노이즈 대책": override(
        "116-118",
        "115-119",
        "Robot installation preparation, cable noise prevention",
        "cable, electromagnetic noise, ferrite core, shield, malfunction, manipulator cable",
        "cable, noise, ferrite core",
        "로봇 설치 준비의 케이블 배치 및 노이즈 주의 section 기준",
    ),
    "설치/케이블 방수": override(
        "405-406",
        "404-406",
        "Installation guide, Cube module, Grommet",
        "cube module, cable, grommet, waterproof, frame cover, installation guide",
        "grommet, waterproof, cable, cube module",
        "부록 설치 가이드의 그로밋 결합 절차 기준",
    ),
    "설치/케이블 배선": override(
        "116-118",
        "115-119",
        "Cable routing, minimum bend radius",
        "cable, routing, minimum bending radius, teach pendant cable, manipulator cable, installation preparation",
        "cable routing, bending radius",
        "로봇 설치 준비의 케이블 최소 곡률반경 section 기준",
    ),
    "설치/케이블 연결": override(
        "83-84; 119-122",
        "82-85; 118-123",
        "Controller cable connection, system connection",
        "teach pendant cable, robot cable, manipulator cable, controller, click, fixing hook, system connection",
        "connect cable, teach pendant, manipulator, controller",
        "빠른 설치 및 System connection의 케이블 연결 section 기준",
    ),
    "수동 조작/Jog": override(
        "373-381",
        "372-382",
        "Jog, manual operation, task motion",
        "Jog, manual, task motion, joint motion, linear, end-effector, target position",
        "Jog, task motion, linear movement",
        "DART-Platform Jog module 화면 section 기준",
    ),
    "시스템 관리/공장 초기화": override(
        "366-371",
        "365-372",
        "Data management, Factory Reset",
        "Factory Reset, database, log file, workcell item, task file, reset, data management",
        "factory reset, reset, delete data",
        "Settings Data management의 Factory Reset section 기준",
    ),
    "시스템 관리/로그": override(
        "339-342",
        "338-342",
        "Logs, log management",
        "Logs, log, date filter, category, level, warning, information, comment, error log",
        "log, error log, export, filter",
        "DART-Platform Logs module section 기준",
    ),
    "시스템 관리/소프트웨어 업데이트": override(
        "166-167; 360-366",
        "165-168; 359-367",
        "Module install, Robot Update",
        "module install, package file, .dm, Robot Update, update file, upload, version",
        "software update, module install, .dm, package",
        "Footer module install 및 Robot Update section 기준",
    ),
    "안전 I/O/보호정지 배선": override(
        "144-147",
        "143-148",
        "Safety I/O, protective stop, TBSFT",
        "Safety I/O, TBSFT, PR, protective stop, safety input, terminal block, light curtain, fence",
        "protective stop, PR, TBSFT, safety input",
        "컨트롤러 Safety I/O 구성하기 section 기준",
    ),
    "안전 I/O/비상정지 배선": override(
        "144-147",
        "143-148",
        "Safety I/O, emergency stop, TBSFT",
        "Safety I/O, TBSFT, EM, emergency stop, safety input, terminal block, external switch",
        "emergency stop, EM, TBSFT, safety input",
        "컨트롤러 Safety I/O 구성하기 section 기준",
    ),
    "안전 I/O/테스트 펄스": override(
        "145-147",
        "144-148",
        "Safety I/O, test pulse",
        "test pulse, safety controller, SI1, SI2, SI3, SI4, safety signal, safety input",
        "test pulse, SI1, SI2, SI3, SI4",
        "Safety Controller 전용 안전 입력 단자 설명 기준",
    ),
    "안전 복구/Recovery": override(
        "181-184",
        "180-185",
        "Recovery, software recovery mode",
        "Recovery, safety violation, robot position, angle, joint, task, software recovery, emergency",
        "Recovery, safety violation, robot position",
        "Recovery module 및 software recovery mode section 기준",
    ),
    "안전 복구/패키징": override(
        "90-91; 184-186",
        "89-92; 183-187",
        "Packaging pose, Pack, Unpack",
        "packaging pose, Pack, Unpack, Recovery, default home position, packaging mode, joint limit",
        "packaging, Pack, Unpack, Recovery",
        "패키징 자세 해제 및 Recovery Pack/Unpack section 기준",
    ),
    "안전 설정/Safety Review": override(
        "246-249",
        "245-250",
        "Safety Setting Review",
        "Safety Setting Review, Robot Parameter, safety settings, review, save, changed value",
        "Safety Review, changed value, save",
        "6.7.4 Safety Setting Review section 기준",
    ),
    "안전 설정/Zone 형상": override(
        "226-246",
        "225-247",
        "Safety Settings, Zone, shape",
        "Zone, sphere, cylinder, cuboid, tilted cuboid, polyhedron, shape, safety settings",
        "zone, shape, sphere, cylinder, cuboid",
        "6.7.3 Safety Settings의 Zone 형상 설정 section 기준",
    ),
    "안전 설정/공간 제한 구역": override(
        "226-238",
        "225-239",
        "Safety Settings, Space Limit, point",
        "Space Limit, zone, point 1, point 2, 3 point, height, x axis, xy plane, safety zone",
        "space limit, point, height, x axis, xy plane",
        "6.7.3 Safety Settings의 Space Limit section 기준",
    ),
    "안전 설정/구역 설정": override(
        "224-230",
        "223-231",
        "Safety Settings, zone setting, center position",
        "Zone, center position, X, Y, Z, sphere, radius, safety area, robot parameter",
        "zone, center position, X, Y, Z",
        "6.7.3 Safety Settings의 Zone 위치 입력 section 기준",
    ),
    "안전 설정/충돌 민감도 감소 구역": override(
        "240-246",
        "239-247",
        "Safety Settings, collision sensitivity reduction zone",
        "collision sensitivity, reduction zone, material, surface, sensitivity, safety zone, robot parameter",
        "collision sensitivity, reduction zone",
        "6.7.3 Safety Settings의 충돌 민감도 감소 구역 section 기준",
    ),
    "안전 설정/협착 방지 구역": override(
        "239-243",
        "238-244",
        "Safety Settings, Crushing Prevention Zone",
        "Crushing Prevention Zone, finger, hand, safety zone, restricted space, worker, prevention",
        "crushing prevention, safety zone, finger",
        "6.7.3 Safety Settings의 Crushing Prevention Zone section 기준",
    ),
    "안전/전원/극성": override(
        "397-404",
        "396-404",
        "CS-12P, power input, polarity",
        "power input, polarity, reverse polarity, controller failure, DC controller, voltage, ground, circuit breaker",
        "power, polarity, reverse, controller",
        "부록 CS-12P 전원 입력 주의 section 기준",
    ),
    "안전/전원/접지": override(
        "86-87; 120-122; 397-404",
        "85-88; 119-123; 396-404",
        "Power connection, grounding, CS-12P",
        "ground, earth, circuit breaker, power cable, controller, IEC plug, power supply, safety",
        "grounding, circuit breaker, power connection",
        "컨트롤러 전원 연결 및 CS-12P 전원 공급 조건 section 기준",
    ),
    "안전/전원/케이블": override(
        "397-404",
        "396-404",
        "CS-12P, power cable, controller warning",
        "cable, extension, modification, fire, controller failure, power supply, DC controller, safety warning",
        "cable, modification, fire, controller failure",
        "부록 CS-12P 케이블/전원 안전 주의 section 기준",
    ),
    "안전/특이점/동작 제한": override(
        "173-175",
        "172-176",
        "Singularity, motion limitation",
        "Singularity, wrist, shoulder, elbow, joint speed, angle limit, stop, position error",
        "singularity, joint speed, angle limit",
        "DART-Platform Singularity 설명 section 기준",
    ),
    "원격 제어/필수 설정": override(
        "249-257",
        "248-258",
        "Remote Control, required settings",
        "Remote Control, module, task, safety input signal, servo on, run, dashboard, input signal",
        "remote control, module, task, safety input",
        "Remote Control 설정 항목 및 실행 절차 section 기준",
    ),
    "전원/컨트롤러 조작": override(
        "88-89; 125-126",
        "87-90; 124-126",
        "Controller power switch",
        "controller power switch, power on, power off, controller bottom, teach pendant, system power",
        "power switch, controller, power on",
        "컨트롤러 전원 켜기 및 설치 매뉴얼 전원 section 기준",
    ),
    "제어기 I/O 배선": override(
        "133-145",
        "132-146",
        "Controller I/O, configurable digital I/O",
        "controller I/O, configurable digital I/O, NPN, PNP, VCC, VIO, GND, GIO, TBPWR, TBCO, TBCI",
        "controller I/O, NPN, TBPWR, VCC, GND",
        "컨트롤러 I/O 구성하기 section 기준",
    ),
    "제어기 I/O/Sink 배선": override(
        "141-143",
        "140-144",
        "Controller I/O, Sink type",
        "Sink type, Negative common, Oxx, GIO, TBCO, input device, digital output wiring",
        "Sink type, Oxx, GIO, Negative common",
        "디지털 I/O Sink type 배선 section 기준",
    ),
    "제어기 I/O/디지털 입출력": override(
        "139-144",
        "138-145",
        "Configurable digital I/O",
        "digital input, digital output, configurable I/O, 16 input, 16 output, controller, terminal block",
        "digital input, digital output, 16",
        "Configurable digital I/O 구성 section 기준",
    ),
    "제어기 I/O/디지털 출력 배선": override(
        "141-142",
        "140-143",
        "Digital output wiring, simple load",
        "TBCO, Oxx, GIO, simple load, digital output, load, output channel",
        "TBCO, Oxx, GIO, load",
        "TBCO 단자블록 단순부하 배선 section 기준",
    ),
    "제어기 I/O/엔코더 입력": override(
        "137-138",
        "136-139",
        "External encoder input, TBEN",
        "TBEN, encoder, A phase, B phase, Z phase, S phase, conveyor, input voltage",
        "TBEN, encoder, A phase, B phase, Z phase",
        "외부 엔코더 입력 TBEN section 기준",
    ),
    "제어기 I/O/외부 장치 연결": override(
        "133-134",
        "132-135",
        "External device connection",
        "external device, emergency stop switch, light curtain, safety mat, solenoid valve, relay, controller I/O",
        "external device, safety device, controller I/O",
        "컨트롤러 I/O 외부 장치 연결 section 기준",
    ),
    "좌표계/오른손 법칙": override(
        "175-177",
        "174-178",
        "Coordinate system, right-hand rule",
        "coordinate, right-hand rule, X axis, Y axis, Z axis, thumb, index finger, middle finger",
        "right-hand rule, X, Y, Z",
        "DART-Platform 좌표계/축 방향 설명 section 기준",
    ),
    "직접교시/Cockpit": override(
        "194-196",
        "193-197",
        "Cockpit, direct teaching",
        "Cockpit, direct teaching, freedrive, constrained motion, tool flange, button, hand guiding",
        "Cockpit, direct teaching, button",
        "Robot Settings의 Cockpit 직접 교시 설명 section 기준",
    ),
    "직접교시/Cockpit 설정": override(
        "196-200",
        "195-201",
        "Cockpit settings",
        "Cockpit, button 1, button 2, 1+2, guide image, setting, reset, function",
        "Cockpit, button setting, function",
        "Robot Settings의 Cockpit 설정 화면 section 기준",
    ),
    "통신/PROFINET": override(
        "153-158",
        "152-159",
        "PROFINET, extended protocol",
        "PROFINET, Slot, Robot State, Slot#1, Ethernet/IP, adapter, transaction, GPR",
        "PROFINET, Slot#1, Robot State",
        "인터페이스 확장 프로토콜 PROFINET section 기준",
    ),
    "툴 설정/Tool Shape": override(
        "207-210",
        "206-211",
        "Tool Settings, Tool Shape",
        "Tool Shape, name, tool item, simulation, robot end, protection, shape",
        "Tool Shape, name, add tool shape",
        "Tool Settings의 Tool Shape section 기준",
    ),
    "툴 설정/Tool Weight": override(
        "203-207",
        "202-208",
        "Tool Settings, Tool Weight",
        "Tool Weight, weight, center of gravity, tool settings, robot parameters, payload",
        "Tool Weight, weight, center of gravity",
        "Tool Settings의 Tool Weight section 기준",
    ),
    "툴 장착/플랜지 고정": override(
        "93-94; 123-125",
        "92-95; 122-126",
        "Tool installation, tool flange",
        "tool flange, M6, bolt, 9 Nm, bracket, tool, fixed position, installation",
        "tool flange, M6, bolt, 9 Nm",
        "툴 설치하기 및 로봇과 툴 연결하기 section 기준",
    ),
    "툴 플랜지/I/O 배선": override(
        "127-130",
        "126-131",
        "Flange I/O, Schematic Diagram, X1 connector",
        "flange I/O, X1, 8 pin, pin map, Power, GND, digital input, RS-485, connector",
        "flange I/O, X1, pin, Power, GND",
        "플랜지 I/O Schematic Diagram section 기준",
    ),
    "툴 플랜지/디지털 출력": override(
        "130-131",
        "129-132",
        "Flange digital output",
        "flange digital output, PNP, Photo coupler, output channel, +24V, open, active, inactive",
        "digital output, +24V, open",
        "플랜지 디지털 출력 사양 section 기준",
    ),
    "툴 플랜지/아날로그 입력": override(
        "132-133",
        "131-134",
        "Flange analog input",
        "flange analog input, voltage mode, current mode, 0-10V, 4-20mA, external device",
        "analog input, voltage, current, 0-10V, 4-20mA",
        "플랜지 아날로그 입력 사양 section 기준",
    ),
    "툴 플랜지/통신 배선": override(
        "127-130",
        "126-131",
        "Flange I/O, RS-485, X1 connector",
        "RS-485, X1, pin 4, pin 6, RS-485+, RS-485-, flange connector, communication",
        "RS-485, X1, pin 4, pin 6",
        "플랜지 I/O X1 커넥터 pin map section 기준",
    ),
    "티치 펜던트/USB 데이터 관리": override(
        "102-103",
        "101-104",
        "Teach pendant, USB",
        "teach pendant, USB, log backup, task export, task import, storage, connector",
        "USB, log backup, task export, task import",
        "설치 매뉴얼 티치펜던트 각부 명칭 section 기준",
    ),
    "티치 펜던트/비상정지": override(
        "89-90; 102-103",
        "88-91; 101-104",
        "Teach pendant, emergency stop button",
        "teach pendant, emergency stop, top right, release, clockwise, warning popup, button",
        "emergency stop, teach pendant, release, clockwise",
        "비상 정지 버튼 해제 및 티치펜던트 각부 명칭 section 기준",
    ),
    "티치 펜던트/상태 확인": override(
        "331-338",
        "330-339",
        "Status, I/O Overview",
        "Status, I/O Overview, joint angle, robot current position, controller input, output, monitoring",
        "Status, I/O Overview, joint angle",
        "Status module 및 I/O Overview section 기준",
    ),
    "티치 펜던트/전원 조작": override(
        "94-95; 102-103",
        "93-96; 101-104",
        "Teach pendant, power button",
        "teach pendant, power button, long press, 4 seconds, forced shutdown, system power",
        "power button, long press, shutdown",
        "티치펜던트 각부 명칭 및 시스템 전원 끄기 section 기준",
    ),
    "티치 펜던트/전원 종료": override(
        "94-95",
        "93-96",
        "System power off, shutdown popup",
        "system power off, shutdown popup, confirm, teach pendant, power off, exit button",
        "power off, shutdown popup, confirm",
        "시스템 전원 끄기 section 기준",
    ),
    "프로그래밍/Task Editor": override(
        "262-267",
        "261-268",
        "Task Editor, command editor",
        "Task Editor, command, task list, property, command list, programming, copy, paste, delete",
        "Task Editor, command, program",
        "DART-Platform Task Editor module section 기준",
    ),
    "프로그래밍/모션 명령": override(
        "267-276",
        "266-277",
        "Robot motion property, MoveJ, MoveL",
        "MoveJ, MoveL, motion, linear, joint, TCP, target pose, coordinate, motion command, radius",
        "MoveJ, MoveL, linear, joint",
        "로봇 모션 속성 및 기본 개념 section 기준",
    ),
    "프로그램 실행/Home Position": override(
        "187-200",
        "186-201",
        "Robot Settings, Home Position",
        "Home Position, Default Position, Custom Position, program start, robot settings, apply",
        "Home Position, Default Position, Custom Position",
        "Robot Settings의 Home Position section 기준",
    ),
    "힘 제어/Custom Code": override(
        "299-311",
        "298-312",
        "Force Control, Custom Code, command example",
        "force control, external force, set_external_force_reset, Custom Code, compliance, force reset, DRL",
        "set_external_force_reset, external force, Custom Code",
        "힘 제어 명령어 예제 및 Custom Code section 기준",
    ),
}


def read_rows():
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(rows):
    fields = list(rows[0].keys())
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(rows):
    fields = list(rows[0].keys())
    table = [fields] + [[row.get(field, "") for field in fields] for row in rows]
    write_workbook(table, XLSX_PATH, "G4 수동 확정 매핑표")


def write_markdown(rows):
    lines = [
        "# G4 매뉴얼 기준 단계 문맥 매핑표",
        "",
        "## 목적",
        "",
        "이 문서는 논문 실험에서 사용할 수 있도록 매뉴얼 섹션 기준으로 수동 검토한 G4 단계 문맥 매핑표이다.",
        "질문별 정답 이미지 파일명은 매핑표에 사용하지 않고, 실습 단계와 매뉴얼 section/page/keyword만 사용하였다.",
        "",
        "## 검토 방식",
        "",
        "- 1차 자동 매핑표에서 넓은 키워드 때문에 잘못 잡힌 page 범위를 수정하였다.",
        "- `설치`, `설정`, `안전`, `좌표`처럼 넓은 단어보다 실제 매뉴얼 section heading을 우선하였다.",
        "- 각 단계별 텍스트 page 범위와 이미지 page 범위를 지나치게 넓지 않게 고정하였다.",
        "",
        "## 매핑표 요약",
        "",
        "| 단계 ID | 실습 단계 | 텍스트 페이지 범위 | 이미지 페이지 범위 | 대표 키워드 | 근거 |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        keywords = row["본문 키워드"].split(", ")[:5]
        lines.append(
            f"| {row['stage_id']} | {row['실습 단계']} | {row['텍스트 페이지 범위']} | "
            f"{row['이미지 페이지 범위']} | {', '.join(keywords)} | {row['근거']} |"
        )
    lines.extend(
        [
            "",
            "## 산출 파일",
            "",
            "- `SCIE용/data/11_stage_context_map_manual.csv`",
            "- `SCIE용/excel/11_stage_context_map_manual.xlsx`",
        ]
    )
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    rows = read_rows()
    missing = sorted(set(MANUAL_OVERRIDES) - {row["실습 단계"] for row in rows})
    if missing:
        raise RuntimeError(f"unknown stage names: {missing}")

    for row in rows:
        stage = row["실습 단계"]
        if stage in MANUAL_OVERRIDES:
            row.update(MANUAL_OVERRIDES[stage])
            row["근거 질문"] = "평가 정답 미사용"

    write_csv(rows)
    write_xlsx(rows)
    write_markdown(rows)
    print(f"updated: {CSV_PATH}")
    print(f"updated: {XLSX_PATH}")
    print(f"updated: {MD_PATH}")
    print(f"overrides: {len(MANUAL_OVERRIDES)}")


if __name__ == "__main__":
    main()

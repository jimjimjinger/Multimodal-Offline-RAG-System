# G4 매뉴얼 기준 단계 문맥 매핑표

## 목적

이 문서는 논문 실험에서 사용할 수 있도록 매뉴얼 섹션 기준으로 수동 검토한 G4 단계 문맥 매핑표이다.
질문별 정답 이미지 파일명은 매핑표에 사용하지 않고, 실습 단계와 매뉴얼 section/page/keyword만 사용하였다.

## 검토 방식

- 1차 자동 매핑표에서 넓은 키워드 때문에 잘못 잡힌 page 범위를 수정하였다.
- `설치`, `설정`, `안전`, `좌표`처럼 넓은 단어보다 실제 매뉴얼 section heading을 우선하였다.
- 각 단계별 텍스트 page 범위와 이미지 page 범위를 지나치게 넓지 않게 고정하였다.

## 매핑표 요약

| 단계 ID | 실습 단계 | 텍스트 페이지 범위 | 이미지 페이지 범위 | 대표 키워드 | 근거 |
|---|---|---|---|---|---|
| M001 | DART-Platform/Robot Settings | 187-201 | 186-203 | DART-Platform, Robot Settings, User Coordinates, Mount, Home Position | 매뉴얼 6.7.1 Robot Settings section 기준 |
| M002 | TCP/툴 좌표 설정 | 201-209 | 200-210 | Tool Settings, TCP, Tool Center Point, Tool Coordinate, offset | 매뉴얼 6.7.2 Tool Settings의 TCP/Tool Center Point 설명 기준 |
| M003 | UI/시스템 정보 확인 | 164-170; 349-350 | 163-171; 348-351 | Header, current time, menu button, System Information, Platform Version | DART-Platform 화면 구성 및 System Information section 기준 |
| M004 | 네트워크/포트 연결 | 148-153; 354-357 | 147-154; 353-358 | WAN, LAN, TCP/IP, Modbus, Ethernet/IP | 인터페이스 Network Connection 및 System Settings Network section 기준 |
| M005 | 비상/Backdrive | 169-170; 178-181 | 168-181 | Backdrive, brake, servo off, joint, release | DART-Platform Backdrive module section 기준 |
| M006 | 사용자 관리/권한 | 342-354 | 341-355 | user, account, supervisor, password, admin | Store account 및 Settings password section 기준 |
| M007 | 상태 확인/I/O Overview | 331-338 | 330-339 | Status, I/O Overview, digital input, digital output, analog input | Status module의 I/O Overview section 기준 |
| M008 | 설치/기구 고정 | 84-86; 115-118 | 83-87; 114-119 | robot base, M8, bolt, torque, 20Nm | 빠른 설치 및 설치 매뉴얼의 로봇 베이스 고정 section 기준 |
| M009 | 설치/로봇 운반 | 97-98; 160-162 | 96-99; 159-163 | transport, lifting point, carry, shaded area, packaging | 설치 매뉴얼 이동 및 설치를 위한 인양 지점 section 기준 |
| M010 | 설치/마운팅 설정 | 187-201 | 186-203 | Mount, installation angle, ceiling, wall, floor | DART-Platform Robot Settings의 Mount 설정 section 기준 |
| M011 | 설치/매니퓰레이터 연결 | 119-122 | 118-123 | manipulator cable, controller, fixing hook, system connection, cable lock | 설치 매뉴얼 System connection section 기준 |
| M012 | 설치/제품 개봉 | 83; 98-104 | 82-84; 97-105 | unpacking, package, box, robot, controller | 로봇 시작하기 패킹 뜯기 및 설치 매뉴얼 구성품 section 기준 |
| M013 | 설치/컨트롤러 배치 | 87-89 | 86-90 | controller, placement, ventilation, clearance, 50 mm | 컨트롤러 배치하기 section 기준 |
| M014 | 설치/케이블 노이즈 대책 | 116-118 | 115-119 | cable, electromagnetic noise, ferrite core, shield, malfunction | 로봇 설치 준비의 케이블 배치 및 노이즈 주의 section 기준 |
| M015 | 설치/케이블 방수 | 405-406 | 404-406 | cube module, cable, grommet, waterproof, frame cover | 부록 설치 가이드의 그로밋 결합 절차 기준 |
| M016 | 설치/케이블 배선 | 116-118 | 115-119 | cable, routing, minimum bending radius, teach pendant cable, manipulator cable | 로봇 설치 준비의 케이블 최소 곡률반경 section 기준 |
| M017 | 설치/케이블 연결 | 83-84; 119-122 | 82-85; 118-123 | teach pendant cable, robot cable, manipulator cable, controller, click | 빠른 설치 및 System connection의 케이블 연결 section 기준 |
| M018 | 수동 조작/Jog | 373-381 | 372-382 | Jog, manual, task motion, joint motion, linear | DART-Platform Jog module 화면 section 기준 |
| M019 | 시스템 관리/공장 초기화 | 366-371 | 365-372 | Factory Reset, database, log file, workcell item, task file | Settings Data management의 Factory Reset section 기준 |
| M020 | 시스템 관리/로그 | 339-342 | 338-342 | Logs, log, date filter, category, level | DART-Platform Logs module section 기준 |
| M021 | 시스템 관리/소프트웨어 업데이트 | 166-167; 360-366 | 165-168; 359-367 | module install, package file, .dm, Robot Update, update file | Footer module install 및 Robot Update section 기준 |
| M022 | 안전 I/O/보호정지 배선 | 144-147 | 143-148 | Safety I/O, TBSFT, PR, protective stop, safety input | 컨트롤러 Safety I/O 구성하기 section 기준 |
| M023 | 안전 I/O/비상정지 배선 | 144-147 | 143-148 | Safety I/O, TBSFT, EM, emergency stop, safety input | 컨트롤러 Safety I/O 구성하기 section 기준 |
| M024 | 안전 I/O/테스트 펄스 | 145-147 | 144-148 | test pulse, safety controller, SI1, SI2, SI3 | Safety Controller 전용 안전 입력 단자 설명 기준 |
| M025 | 안전 복구/Recovery | 181-184 | 180-185 | Recovery, safety violation, robot position, angle, joint | Recovery module 및 software recovery mode section 기준 |
| M026 | 안전 복구/패키징 | 90-91; 184-186 | 89-92; 183-187 | packaging pose, Pack, Unpack, Recovery, default home position | 패키징 자세 해제 및 Recovery Pack/Unpack section 기준 |
| M027 | 안전 설정/Safety Review | 246-249 | 245-250 | Safety Setting Review, Robot Parameter, safety settings, review, save | 6.7.4 Safety Setting Review section 기준 |
| M028 | 안전 설정/Zone 형상 | 226-246 | 225-247 | Zone, sphere, cylinder, cuboid, tilted cuboid | 6.7.3 Safety Settings의 Zone 형상 설정 section 기준 |
| M029 | 안전 설정/공간 제한 구역 | 226-238 | 225-239 | Space Limit, zone, point 1, point 2, 3 point | 6.7.3 Safety Settings의 Space Limit section 기준 |
| M030 | 안전 설정/구역 설정 | 224-230 | 223-231 | Zone, center position, X, Y, Z | 6.7.3 Safety Settings의 Zone 위치 입력 section 기준 |
| M031 | 안전 설정/충돌 민감도 감소 구역 | 240-246 | 239-247 | collision sensitivity, reduction zone, material, surface, sensitivity | 6.7.3 Safety Settings의 충돌 민감도 감소 구역 section 기준 |
| M032 | 안전 설정/협착 방지 구역 | 239-243 | 238-244 | Crushing Prevention Zone, finger, hand, safety zone, restricted space | 6.7.3 Safety Settings의 Crushing Prevention Zone section 기준 |
| M033 | 안전/전원/극성 | 397-404 | 396-404 | power input, polarity, reverse polarity, controller failure, DC controller | 부록 CS-12P 전원 입력 주의 section 기준 |
| M034 | 안전/전원/접지 | 86-87; 120-122; 397-404 | 85-88; 119-123; 396-404 | ground, earth, circuit breaker, power cable, controller | 컨트롤러 전원 연결 및 CS-12P 전원 공급 조건 section 기준 |
| M035 | 안전/전원/케이블 | 397-404 | 396-404 | cable, extension, modification, fire, controller failure | 부록 CS-12P 케이블/전원 안전 주의 section 기준 |
| M036 | 안전/특이점/동작 제한 | 173-175 | 172-176 | Singularity, wrist, shoulder, elbow, joint speed | DART-Platform Singularity 설명 section 기준 |
| M037 | 원격 제어/필수 설정 | 249-257 | 248-258 | Remote Control, module, task, safety input signal, servo on | Remote Control 설정 항목 및 실행 절차 section 기준 |
| M038 | 전원/컨트롤러 조작 | 88-89; 125-126 | 87-90; 124-126 | controller power switch, power on, power off, controller bottom, teach pendant | 컨트롤러 전원 켜기 및 설치 매뉴얼 전원 section 기준 |
| M039 | 제어기 I/O 배선 | 133-145 | 132-146 | controller I/O, configurable digital I/O, NPN, PNP, VCC | 컨트롤러 I/O 구성하기 section 기준 |
| M040 | 제어기 I/O/Sink 배선 | 141-143 | 140-144 | Sink type, Negative common, Oxx, GIO, TBCO | 디지털 I/O Sink type 배선 section 기준 |
| M041 | 제어기 I/O/디지털 입출력 | 139-144 | 138-145 | digital input, digital output, configurable I/O, 16 input, 16 output | Configurable digital I/O 구성 section 기준 |
| M042 | 제어기 I/O/디지털 출력 배선 | 141-142 | 140-143 | TBCO, Oxx, GIO, simple load, digital output | TBCO 단자블록 단순부하 배선 section 기준 |
| M043 | 제어기 I/O/엔코더 입력 | 137-138 | 136-139 | TBEN, encoder, A phase, B phase, Z phase | 외부 엔코더 입력 TBEN section 기준 |
| M044 | 제어기 I/O/외부 장치 연결 | 133-134 | 132-135 | external device, emergency stop switch, light curtain, safety mat, solenoid valve | 컨트롤러 I/O 외부 장치 연결 section 기준 |
| M045 | 좌표계/오른손 법칙 | 175-177 | 174-178 | coordinate, right-hand rule, X axis, Y axis, Z axis | DART-Platform 좌표계/축 방향 설명 section 기준 |
| M046 | 직접교시/Cockpit | 194-196 | 193-197 | Cockpit, direct teaching, freedrive, constrained motion, tool flange | Robot Settings의 Cockpit 직접 교시 설명 section 기준 |
| M047 | 직접교시/Cockpit 설정 | 196-200 | 195-201 | Cockpit, button 1, button 2, 1+2, guide image | Robot Settings의 Cockpit 설정 화면 section 기준 |
| M048 | 통신/PROFINET | 153-158 | 152-159 | PROFINET, Slot, Robot State, Slot#1, Ethernet/IP | 인터페이스 확장 프로토콜 PROFINET section 기준 |
| M049 | 툴 설정/Tool Shape | 207-210 | 206-211 | Tool Shape, name, tool item, simulation, robot end | Tool Settings의 Tool Shape section 기준 |
| M050 | 툴 설정/Tool Weight | 203-207 | 202-208 | Tool Weight, weight, center of gravity, tool settings, robot parameters | Tool Settings의 Tool Weight section 기준 |
| M051 | 툴 장착/플랜지 고정 | 93-94; 123-125 | 92-95; 122-126 | tool flange, M6, bolt, 9 Nm, bracket | 툴 설치하기 및 로봇과 툴 연결하기 section 기준 |
| M052 | 툴 플랜지/I/O 배선 | 127-130 | 126-131 | flange I/O, X1, 8 pin, pin map, Power | 플랜지 I/O Schematic Diagram section 기준 |
| M053 | 툴 플랜지/디지털 출력 | 130-131 | 129-132 | flange digital output, PNP, Photo coupler, output channel, +24V | 플랜지 디지털 출력 사양 section 기준 |
| M054 | 툴 플랜지/아날로그 입력 | 132-133 | 131-134 | flange analog input, voltage mode, current mode, 0-10V, 4-20mA | 플랜지 아날로그 입력 사양 section 기준 |
| M055 | 툴 플랜지/통신 배선 | 127-130 | 126-131 | RS-485, X1, pin 4, pin 6, RS-485+ | 플랜지 I/O X1 커넥터 pin map section 기준 |
| M056 | 티치 펜던트/USB 데이터 관리 | 102-103 | 101-104 | teach pendant, USB, log backup, task export, task import | 설치 매뉴얼 티치펜던트 각부 명칭 section 기준 |
| M057 | 티치 펜던트/비상정지 | 89-90; 102-103 | 88-91; 101-104 | teach pendant, emergency stop, top right, release, clockwise | 비상 정지 버튼 해제 및 티치펜던트 각부 명칭 section 기준 |
| M058 | 티치 펜던트/상태 확인 | 331-338 | 330-339 | Status, I/O Overview, joint angle, robot current position, controller input | Status module 및 I/O Overview section 기준 |
| M059 | 티치 펜던트/전원 조작 | 94-95; 102-103 | 93-96; 101-104 | teach pendant, power button, long press, 4 seconds, forced shutdown | 티치펜던트 각부 명칭 및 시스템 전원 끄기 section 기준 |
| M060 | 티치 펜던트/전원 종료 | 94-95 | 93-96 | system power off, shutdown popup, confirm, teach pendant, power off | 시스템 전원 끄기 section 기준 |
| M061 | 프로그래밍/Task Editor | 262-267 | 261-268 | Task Editor, command, task list, property, command list | DART-Platform Task Editor module section 기준 |
| M062 | 프로그래밍/모션 명령 | 267-276 | 266-277 | MoveJ, MoveL, motion, linear, joint | 로봇 모션 속성 및 기본 개념 section 기준 |
| M063 | 프로그램 실행/Home Position | 187-200 | 186-201 | Home Position, Default Position, Custom Position, program start, robot settings | Robot Settings의 Home Position section 기준 |
| M064 | 힘 제어/Custom Code | 299-311 | 298-312 | force control, external force, set_external_force_reset, Custom Code, compliance | 힘 제어 명령어 예제 및 Custom Code section 기준 |

## 산출 파일

- `SCIE용/data/11_stage_context_map_manual.csv`
- `SCIE용/excel/11_stage_context_map_manual.xlsx`

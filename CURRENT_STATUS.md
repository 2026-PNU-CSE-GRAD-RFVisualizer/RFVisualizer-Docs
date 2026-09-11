# RFVisualizer 현재 진행 상태

- 기준일: **2026-09-11**
- 기준: 각 저장소의 현재 구현, 최종보고서 반영 실험 산출물과 실기기 통합 시험

## 1. 한 줄 요약

3층 링 복도의 3D 장면·RF 분석, 다섯 대 ESP32 기반 RSSI 계측과 잔차 계산, RFHC Handheld Control,
3D RF Volume 및 RFJF(palette256 기본) 영상 송신을 구현했다. 다중 ESP32 계측 데이터는 최종 잔차
계산에 사용했고, Graphics→Relay→ESP32-S3→LCD 영상과 Handheld→Backend→Graphics 자세·버튼
경로를 실기기에서 종단 확인했다. 영상·IMU·버튼 통합 구성의 300초 이상 연속 시험도 안정적으로
완료했다.

## 2. 핵심 상태

| 항목 | 현재 상태 | 판단 |
|---|---|---|
| 3층 복도 PGSR·Proxy Scene | 구현·검증 완료 | 최종보고서 장면과 좌표계에 반영 |
| 3층 Marker 배치 | `ready` | TX 1, Calibration 4, Test 10 |
| 3층 Sionna RT | `depth12` 선정·실행 완료 | 깊이 민감도 분석 후 최종보고서에 반영 |
| RF Experiment Framework | 구현·테스트 완료 | 동시간 Calibration 매칭 지원 |
| 최종 링 복도 RSSI 측정 | 수집·분석 완료 | 정방향 10 + 역방향 10 = 20개 반복 관측 |
| 10×2 측정 계약 | 충족 | Test 1--10의 정·역방향 관측 확보 |
| Network Backend | 종단 검증 완료 | 실센서 수집·저장·Export·QC·복구 로직 확인 |
| RFJF Image Relay | 구현·검증 완료 | Graphics→Handheld 종단 및 300초 이상 안정 동작 확인 |
| Handheld RFJF·LCD | 구현·검증 완료 | palette256/RGB332 출력과 300초 이상 연속 운용 완료 |
| Handheld BNO085·LCD | 실물 검증 완료 | 약 50 Hz Quaternion과 LCD 동시 동작 확인 |
| Handheld Control RFHC v1 | 구현·종단 검증 완료 | 실제 두 버튼과 자세의 Backend·Graphics 반영 확인 |
| Graphics Handheld Consumer | 구현·종단 검증 완료 | 실제 BNO085 축, 버튼과 Viewer 동작 확인 |
| 3D RF Volume Bundle | 구현·테스트 완료 | 6개 높이 표시; 수직 Residual은 정성적 외삽으로 해석 |
| SIBR RF Volume·영상 Producer | 구현·실기기 검증 완료 | Viewer·Relay·LCD 통합 및 지속 운용 완료 |
| 최종보고서용 데이터 | 반영 완료 | 20개 반복 관측의 탐색적 결과로 사용 |

## 3. 최신 RF 실험 결과

기준 산출물은 최종보고서에 반영한 3층 링 복도 측정 데이터다. 원본 측정값과 제외 사유를 보존하고,
Test 1--10의 정방향·역방향 반복 관측을 모두 분석했다.

### 데이터 범위

| 항목 | 값 |
|---|---:|
| 정방향 Test Segment | 10개 |
| 역방향 Test Segment | 10개 |
| 전체 반복 관측 | 20개 |
| 동시간 Calibration | 모든 Test Segment에 C1--C4 존재 |
| 측정 장치 | ESP32 5대: Calibration 4대 + 이동 Test 1대 |

### 결과

| 방식 | MAE | RMSE |
|---|---:|---:|
| Raw Sionna RT | 7.64 dB | 9.32 dB |
| Plain IDW | 5.33 dB | 7.09 dB |
| Sionna RT + Residual IDW | 3.41 dB | 4.74 dB |
| Sionna RT + Global Bias | 8.26 dB | 9.83 dB |

같은 10개 위치의 정·역방향 반복 차이는 MAE 3.90 dB, 최대 10.00 dB(test-04)다.

### 판정

- 다중 ESP32 수집 경로는 실제 Calibration·Test 데이터와 잔차 계산 결과까지 종단 사용했다.
- 10개 위치의 정·역방향 20개 반복 관측과 모든 구간의 동시간 Calibration 데이터를 확보했다.
- 결과는 최종보고서의 탐색적 기술통계로 사용한다.
- 평가 위치의 한 관측값이 `max_depth` 재검토의 계기가 되었으므로 완전 독립 홀드아웃 성능으로
  해석하지 않으며, 다른 공간에 대한 일반화를 주장하지 않는다.

## 4. 파트별 진행 상태

### 그래픽스

완료 또는 로컬 검증:

- 3층 복도 PGSR Gaussian/Surface Mesh와 Metric Scene
- Proxy Envelope, Marker 배치, Sionna `depth12` 실행
- Backend Export 입력, 동시간 Calibration 매칭, Sionna/IDW/Residual 비교
- 6개 높이 Sionna Volume과 Viewer Bundle Export 구현
- Graphics Python 도구 전체 375개 통과, 2개 건너뜀 (`pgsr` 환경, `--import-mode=importlib`)
- 로컬 SIBR에 RF Volume 합성, Mesh Depth 가림, Offscreen 800×480, RFJF(palette256/RGB332/JPEG) 송신 코드와 빌드 결과 존재
- `PaletteChooser`(장면 팔레트 자동 선정, 재선정), RGB332 Bayer Ordered Dithering
- Backend WebSocket `/handheld/control` 구독과 Camera 자세 적용 구현
- **2026-08-28 기획 변경 반영**: Recenter·Position Update 버튼을 텔레포트·Height-cycle
  버튼으로 교체 구현. `ArcTeleportController`를 키보드 R·Handheld 버튼 양쪽에서 구동하고,
  Handheld 활성 중 텔레포트가 강제로 꺼지던 게이트 버그를 고쳤다. `RFVolumeRenderer`에
  Height-cycle 순환 추가
- `SIBR_handheld_control_test`(Fake Backend WebSocket 포함), `SIBR_arc_teleport_test` 통과
- 새 Build Directory에서 configure·build·CTest(6개) 통과
- **2026-08-27 실기기 확인**: Graphics→Relay→ESP32-S3→NT35510 LCD RFJF 영상 종단 출력
  (`flags=1` RGB332, `flags=2` palette256 둘 다), palette256이 화질 우위

후속 연구 범위:

- 계단·문·책상·AP 위치와 재질을 현장 기준으로 보정
- 장면 좌표 오차(현재 계획도 기반 약 ±0.5 m)와 Scale 재검증
- 다른 공간에서 장면 정합과 RF 잔차 보정의 일반화 평가
- 높이별 실측을 추가한 3D RF Volume의 수직 방향 정량 평가

### 임베디드

완료 또는 로컬 검증:

- ESP32 RSSI Node/Gateway, STM32 Parser, Serial-MQTT Bridge
- RSSI 허용 하한 `-110 dBm`과 AP Channel 기본값 6 반영
- Bridge Python 테스트 8개, STM32 Parser Host Test, RFJF Protocol Host Test 5개 통과
- RFHC v1 Serializer Host Test 7개 통과, Backend 공유 52-byte/CRC Vector와 버튼 bit1·bit2 일치
- 기존 ControlTxTask에 GPIO17·GPIO19 active-low 입력, 25 ms debounce, RFHC held-state 송신 통합
- BNO085 독립 Quaternion 실물 시험 완료
- 서버 더미 JPEG의 TCP 수신·디코드·NT35510 LCD 실물 출력 완료
- BNO085와 NT35510 LCD 동시 구동, 부팅 자세 Recenter와 Quaternion 기반 로컬 3D Wireframe 시점 이동 실물 검증
- 로컬 통합 시험에서 BNO085 약 50 Hz를 유지했고 LCD 색상 깨짐·녹색 줄 없이 동작함
- **2026-08-27**: 실제 Graphics Frame(palette256 기본, RGB332 호환)의 ESP32-S3→NT35510 LCD
  종단 출력 확인, RGB332 대비 화질 개선 확인
- **2026-09-06 최종 실물 확인**: 완성된 Handheld에서 BNO085 Yaw·Pitch·Roll 방향/부호와
  `q_mount=identity` 조합, GPIO17 텔레포트·GPIO19 Height-cycle 버튼의 held/released RFHC UDP
  상태를 확인함
- Handheld→Backend→Graphics 종단 경로에서 Camera 자세 갱신, 텔레포트 hold/release,
  Height-cycle press edge 동작 확인
- 다섯 대 ESP32를 Calibration 4대와 이동 Test 1대로 운용해 최종 잔차 계산용 데이터 수집 완료
- 고정 Channel과 장치별 Offset, 동시간 Calibration 정합을 적용한 20개 반복 관측 확보
- 영상·BNO085·버튼 통합 구성으로 300초 이상 연속 운용해 화면 정지와 기능 중단 없이 안정 동작 확인
- 2026-09-11 현재 Python Bridge 8개, RFJF Host Test 5개, RFHC Host Test 7개,
  STM32 Parser Host Test와 RGB565→RGB666 전 색상 등가성 시험 통과

완료 판정:

- 다중 ESP32는 잔차 계산에 사용되는 본 실험의 계측 장치다. 실제 분석 데이터를 생성했으므로
  별도의 ``향후 다중 노드 검증'' 항목으로 두지 않는다.
- 300초 이상 핸드헬드 통합 시험을 완료했으므로 영상·제어 지속 동작을 완료 상태로 판정한다.
- Broadcast/Unicast 비교나 소비전력 측정처럼 최종보고서의 평가 목표로 설정하지 않은 항목은
  구현 미완료가 아니라 범위 밖의 운영 개선 항목으로 구분한다.

### 네트워크

완료 또는 로컬 검증:

- Run/Segment, 사전·사후 Offset, SQLite/JSONL, Export/QC, 동시간 매칭
- 런타임 RSSI 허용 하한 `-110 dBm`
- 현재 테스트 65개 통과, 이 중 Handheld 관련 단위·통합 테스트 16개
- 별도 `image_relay` 프로세스와 RFJF 22-byte Frame 중계 테스트 8개 통과
- RFHC v1 52-byte Parser, CRC/Quaternion 검증과 UDP `9200` Listener
- Handheld Event 중복 제거, Sequence 통계, 500 ms stale 판정
- `PositionProvider`, `ConfiguredPositionProvider`, Position 유효성 검사
- Graphics WebSocket `/handheld/control`과 Handheld 관리 API

현재 상태:

- 실센서 5대의 Calibration·Test 수집과 분석용 Export를 완료했다.
- 독립 `ParseConfig()`와 런타임 `Settings`의 RSSI 하한은 모두 `-110 dBm`으로 일치한다.
- Image Relay는 Graphics producer·실제 Handheld와 연결해 2026-08-27 영상 종단 출력을
  확인했고, 통합 구성에서 300초 이상 안정 동작을 확인했다.

## 5. 공통 계약과 통합 상태

### RFJF Frame 기준 구현

Network Relay와 Embedded 수신 코드는 다음 기준을 공유한다.

```text
Graphics ─TCP 9101─▶ Image Relay ─TCP 9102─▶ Handheld
22-byte big-endian header + payload
magic='RFJF', version=1, flags(0=JPEG,1=RGB332+zlib,2=palette256+zlib), seq, ts_ms, length
payload 최대 8 MiB
```

**기본 형식은 2026-08-27부터 `flags=2` palette256+zlib다.** `flags=1` RGB332+zlib은 호환·진단
경로, `flags=0` JPEG은 단일 이미지·안정성 확인 경로로 유지한다. Network Relay·Embedded
수신 코드와 Graphics sender가 이 규격을 사용하며, Graphics C++ 소스는 Git에서 추적된다.
2026-08-27에 `flags=1`·`flags=2` 두 경로 모두 Graphics→Relay→ESP32-S3→NT35510 LCD 실기기
종단 출력을 확인했으며, 영상·IMU·버튼 통합 구성의 300초 이상 연속 시험도 안정적으로 완료했다.

### Handheld Control 기준 구현

Embedded와 Backend는 다음 RFHC v1 Wire 규격과 공유 Test Vector를 검증했다.

```text
Handheld ─UDP 9200, 50 Hz─▶ Backend ─WS /handheld/control─▶ Graphics
52-byte big-endian Packet
magic='RFHC', version=1, flags, device_id, session_id
sample_seq, event_seq(2026-08-28부터 미사용), timestamp_ms, quaternion x/y/z/w, CRC32/IEEE
500 ms timeout 후 stale
```

Backend Parser·Listener, Embedded Serializer, Graphics Consumer는 구현됐다. Graphics는
`/handheld/control`을 구독해 Camera 자세와 버튼 동작을 적용한다. Embedded는 실제 50 Hz
ControlTxTask에 두 버튼의 debounce된 레벨 상태 송신을 연결했다. 실제 ESP32-S3 버튼 UDP
송신, `q_mount`와 BNO085 Yaw·Pitch·Roll 축, Camera 회전, 텔레포트 및 Height-cycle 동작을
Handheld→Backend→Graphics 종단 경로에서 검증했다.
WebSocket이 끊긴 동안 Backend가 보낸 Position은 복구할 수 없다.

### 좌표 관리

- 고정 Calibration Node는 각 저장소의 최신 좌표를 사용한다.
- 이동 Node `node-02`의 `(0,0,0)`은 의도된 Placeholder다.
- Test 위치는 전역 `node_positions.json`이 아니라 Backend Experiment Assignment로 관리한다.
- 실험마다 Frame ID, 단위, 원점, 축, Transform, TX/RX 높이를 기록한다.

## 6. 결과 해석 시 주의사항

1. 최종 RF 정확도 수치는 단일 건물·단일 AP의 탐색적 결과이며 다른 공간에 대한 일반화를 뜻하지 않는다.
2. 평가 위치의 측정값이 `max_depth` 재검토에 사용되었으므로 완전히 독립적인 홀드아웃 결과는 아니다.
3. 단일 측정 높이의 잔차를 다른 높이에 적용한 RF Volume은 정성적 시각화로 해석한다.
4. ESP-NOW Packet의 BSSID가 현재 UART·STM32 JSON까지 전달되지 않으므로 AP BSSID는 실험 설정
   단위로 고정·기록했다. 이는 다중 ESP32 동작 완료 여부와 별개의 추적성 한계다.

## 7. 후속 연구 및 운영 개선

1. 다른 건물과 AP에서 잔차 보정의 일반화 가능성을 평가한다.
2. 여러 높이의 실측값으로 3D RF Volume의 수직 방향 정확도를 평가한다.
3. 배터리 구동 시간과 휴대형 Case를 포함한 사용자 운용성을 개선한다.
4. ESP-NOW의 AP BSSID를 UART·STM32 JSON까지 전달하도록 공통 Interface 문서를 정합한다.

## 8. 저장소 기준

2026-09-11 이번 문서 갱신 직전 확인:

| 저장소 | GitHub `main` | 확인 방법 |
|---|---|---|
| RFVisualizer-Docs | `a40b909` | 로컬 작업 트리 확인 후 본 상태 문서 갱신 |
| Embedded | `7a22d50` | 현재 소스와 Host Test 직접 확인 |

이번 갱신에서 Embedded의 Python Serial--MQTT Bridge 8개, RFJF Parser 5개, RFHC Serializer
7개, STM32 Parser/Preprocessor/JSON Host Test와 RGB565→RGB666 전 색상 등가성 시험을
직접 실행해 통과를 확인했다. 실기기 다중 ESP32 계측과 300초 이상 통합 안정성은 완료된 현장
시험 결과를 반영했다.

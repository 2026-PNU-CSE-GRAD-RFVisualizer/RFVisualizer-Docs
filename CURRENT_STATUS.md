# RFVisualizer 현재 진행 상태

- 기준일: **2026-09-01**
- 기준: 각 저장소 `main`과 `/data/RFVisualizer_Workspace`의 최신 실험 산출물

## 1. 한 줄 요약

3층 복도 장면·RF 분석, RFHC Handheld Control, 3D RF Volume과 RFJF(palette256 기본) 영상 송신, Graphics의 `/handheld/control` Camera 연결까지 구현했고 2026-08-27에 Graphics→Relay→ESP32-S3→LCD 영상 실기기 종단 출력을 확인했다. 남은 건 영상 경로 정량 성능(300초 FPS·지연), RFHC(자세·버튼) 실기기 UDP 종단 통합, 최종 논문용 RF 데이터 확보다.

## 2. 핵심 상태

| 항목 | 현재 상태 | 판단 |
|---|---|---|
| 3층 복도 PGSR·Proxy Scene | 구현·로컬 검증 완료 | 장면 정밀도는 추가 보정 필요 |
| 3층 Marker 배치 | `ready` | TX 1, Calibration 4, Test 10 |
| 3층 Sionna RT | `depth12` 실행 성공 | Scene/Solver 잠정, 논문 근거 불가 |
| RF Experiment Framework | 구현·테스트 완료 | 동시간 Calibration 매칭 지원 |
| 2026-08-21 Lounge 측정 | 분석 가능 | 정방향 8 + 역방향 10 = 18구간 |
| 엄격한 10×2 계약 | 미충족 | 정방향 Test 1·2 누락 |
| Network Backend | Export/QC/복구 로직 검증 | 실센서 전체 리허설은 미검증 |
| RFJF Image Relay | 구현·테스트 완료 | Graphics→Handheld 실기기 종단 확인(8/27), 300초 지속 성능 미검증 |
| Handheld RFJF·LCD | palette256/RGB332 Graphics producer→Relay→LCD 실기기 종단 출력 확인(8/27) | 300초 지속 FPS·지연·drop 미계측 |
| Handheld BNO085·LCD | 약 50 Hz Quaternion·로컬 3D 시점 이동 실물 검증 | 버튼·RFHC UDP·Graphics 실물 통합 미완료 |
| Handheld Control RFHC v1 | 50 Hz UDP 송신과 버튼 held-state Firmware 구현·Host Test 7개 통과 | 실제 버튼 UDP 송신 미검증 |
| Graphics Handheld Consumer | 구현·C++ Test 통과 | 실제 BNO085 축·버튼·실행 화면 미검증 |
| 3D RF Volume Bundle | 구현·테스트 완료 | 높이 방향 Residual은 외삽, 논문 근거 불가 |
| SIBR RF Volume·영상 Producer | C++ 소스 Git 반영, palette256 기본 전환, 새 Build Directory 빌드 통과 | Viewer 실행 화면(Display 필요)·300초 지속 성능 미검증 |
| 최종 논문용 데이터 | 미확정 | `paper_evidence_eligible=false` |

## 3. 최신 RF 실험 결과

기준 산출물은 `experiments/0821_lounge_201729`이다. 원본 측정값은 수정하지 않았고, 분석 가능한 18개 Test Segment만 사용했다.

### 데이터 범위

| 항목 | 값 |
|---|---:|
| 정방향 Test Segment | 8개 — Test 1·2 누락 |
| 역방향 Test Segment | 10개 |
| 전체 Test Segment | 18개 |
| 동시간 Calibration Window | 72개 — Segment당 C1~C4 |
| BSSID가 비어 있는 Raw Row | 19,648개 전체 |

### 결과

| 방식 | MAE | RMSE |
|---|---:|---:|
| Raw Sionna RT | 7.92 dB | 9.66 dB |
| Plain IDW | 5.47 dB | 7.28 dB |
| Sionna RT + Residual IDW | 3.52 dB | 4.89 dB |

정·역방향에서 공통으로 측정된 8개 위치의 반복 차이는 평균 4.13 dB, 최대 10.00 dB이다. Reverse Test 7은 샘플이 68개로 기본 기대치 72개보다 적다.

### 판정

- `usable_for_analysis=true`: 부분 데이터 분석은 가능하다.
- `strict_contract_complete=false`: 정방향 10개가 모두 없어 최종 계약은 미충족이다.
- `paper_evidence_eligible=false`: 3층 Scene/Solver가 잠정이고 현장 형상·재질 검증이 남아 있다.
- 사후 Offset이 없으므로 장시간 Drift를 검증할 수 없다.

기존 PNU 4층 결과는 파이프라인 검증용 **Pilot**으로만 유지하며, 3층 최종 결과와 한 표에 섞지 않는다.

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

남은 작업:

- 계단·문·책상·AP 위치와 재질을 현장 기준으로 보정
- 장면 좌표 오차(현재 계획도 기반 약 ±0.5 m)와 Scale 재검증
- Display가 있는 장비에서 SIBR 실행·Heatmap 실제 렌더 검증
- 실제 BNO085 축과 `q_mount`의 Yaw·Pitch·Roll 실물 시험
- Graphics→Relay→Handheld 300초 지속 FPS·지연·drop 정량 검증
- 임베디드 버튼 2개(GPIO·UDP)가 연결되면 실기기 텔레포트·Height-cycle 종단 시험

### 임베디드

완료 또는 로컬 검증:

- ESP32 RSSI Node/Gateway, STM32 Parser, Serial-MQTT Bridge
- RSSI 허용 하한 `-110 dBm`과 AP Channel 기본값 6 반영
- Bridge Python 테스트 8개, STM32 Parser Host Test, JPEG Protocol Host Test 4개 통과
- RFHC v1 Serializer Host Test 7개 통과, Backend 공유 52-byte/CRC Vector와 버튼 bit1·bit2 일치
- 기존 ControlTxTask에 GPIO17·GPIO19 active-low 입력, 25 ms debounce, RFHC held-state 송신 통합
- BNO085 독립 Quaternion 실물 시험 완료
- 서버 더미 JPEG의 TCP 수신·디코드·NT35510 LCD 실물 출력 완료
- BNO085와 NT35510 LCD 동시 구동, 부팅 자세 Recenter와 Quaternion 기반 로컬 3D Wireframe 시점 이동 실물 검증
- 로컬 통합 시험에서 BNO085 약 50 Hz를 유지했고 LCD 색상 깨짐·녹색 줄 없이 동작함
- **2026-08-27**: 실제 Graphics Frame(palette256 기본, RGB332 호환)의 ESP32-S3→NT35510 LCD
  종단 출력 확인, RGB332 대비 화질 개선 확인. 정량 FPS·지연·장시간 안정성은 미계측

실물 검증 필요:

- RSSI 장치 3~5대 정·역방향 전체 리허설과 1~2시간 안정성
- 고정 BSSID/Channel, 사전·사후 Device Offset, Fault Injection
- 실제 버튼의 RFHC held/released UDP 상태와 Handheld→Backend→Graphics 동작 검증
- 실제 Graphics Frame으로 800×480 palette256 수신·디코드·표시의 300초 지속 속도

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

현재 제한:

- 실센서 5대 전체 리허설과 재시작/재연결 실제 동작은 미검증이다.
- 독립 `ParseConfig()`와 런타임 `Settings`의 RSSI 하한은 모두 `-110 dBm`으로 일치한다.
- Image Relay는 Graphics producer·실제 Handheld와 연결해 2026-08-27 영상 종단 출력을
  확인했다. 300초 지속 성능은 아직 계측하지 않았다.

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
종단 출력을 확인했다. 300초 지속 FPS·지연·drop 등 정량 성능은 아직 계측하지 않았다.

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
송신, `q_mount`와 BNO085 실물 축 시험은 아직 남아 있다.
WebSocket이 끊긴 동안 Backend가 보낸 Position은 복구할 수 없다.

### 좌표 관리

- 고정 Calibration Node는 각 저장소의 최신 좌표를 사용한다.
- 이동 Node `node-02`의 `(0,0,0)`은 의도된 Placeholder다.
- Test 위치는 전역 `node_positions.json`이 아니라 Backend Experiment Assignment로 관리한다.
- 실험마다 Frame ID, 단위, 원점, 축, Transform, TX/RX 높이를 기록한다.

## 6. 현재 위험

1. **논문 위험:** 분석 수치는 좋아졌지만 누락 구간·BSSID 공란·사후 Offset 부재·잠정 Scene 때문에 최종 근거가 아니다.
2. **통합 위험(영상):** Graphics→Relay→Handheld 영상 경로는 2026-08-27 실기기 종단 출력을 확인했으나, 300초 지속 FPS·지연·drop 등 정량 성능은 아직 없다.
3. **통합 위험(제어):** RFHC(방향·버튼) 경로는 Graphics가 2026-08-28 신규 버튼 규격(텔레포트·Height-cycle)까지 구현·CTest 검증을 마쳤지만, Backend/Embedded는 아직 구 규격(Recenter·Position Update)이고 실제 UDP 종단 검증도 없다.
4. **환경 위험:** 현재 Workspace에는 Display가 없어 Viewer 실행 화면을 확인할 수 없다. Graphics Handheld 연결은 C++ Test까지만 검증됐고 실제 렌더 화면과 조작감은 미확인이다.

## 7. 다음 작업

1. 3층 Scene의 계단·문·책상·AP 위치와 재질을 확정하고 Sionna를 다시 실행한다.
2. 누락된 정방향 Test 1·2와 최소한의 Offset/BSSID 항목만 재측정해 엄격한 10×2 계약을 채운다.
3. 같은 분석을 재실행해 `paper_evidence_eligible`를 재판정한다.
4. Display가 있는 장비에서 SIBR를 실행해 Heatmap과 Handheld Camera 동작을 확인한다.
5. 실제 BNO085로 Yaw·Pitch·Roll 축과 `q_mount`를 확정한다.
6. 실제 버튼 RFHC UDP 송신과 Handheld→Backend→Graphics 텔레포트·Height-cycle 동작을 검증한다.
7. Graphics→Relay→Handheld 800×480 영상 경로의 300초 지속 FPS·지연·drop을 계측한다.

## 8. 저장소 기준

2026-08-28 이번 문서 갱신 직전, 이 Workspace에 로컬 clone이 있는 두 저장소의 `main`(=`origin/main`, clean):

| 저장소 | GitHub `main` |
|---|---|
| RFVisualizer | `fff09b1` (텔레포트·Height-cycle 버튼 구현이 아직 이 커밋 위 작업 트리에만 있고 커밋되지 않음) |
| RFVisualizer-Docs | `d4f8bc0` |

Embedded와 Network-Backend-Article은 이 Workspace에 로컬 clone이 없어 직접 확인할 수
없다. 각 파트 문서(`embedded/EMBEDDED.md`, `network/NETWORK.md`)에 적힌 팀원 보고를
기준으로 삼았으며, 이번 갱신에서 원격 `main` 해시나 테스트를 다시 확인하지 않았다.

이번 갱신에서 Graphics의 `handheld_control`·`arc_teleport`를 포함한 CTest 6개를 로컬
빌드로 재실행해 통과를 확인했다(§4 그래픽스 참고). Network·Embedded 테스트는 재실행하지
않았다 — 각 파트 테스트 수는 해당 저장소·문서의 최신 기록을 인용했다.

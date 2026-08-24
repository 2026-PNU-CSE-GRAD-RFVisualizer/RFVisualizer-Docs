# RFVisualizer 현재 진행 상태

- 기준일: **2026-08-24**
- 기준: 각 저장소 `main`과 `/data/RFVisualizer_Workspace`의 최신 실험 산출물

## 1. 한 줄 요약

3층 복도 장면·RF 분석, RFHC Handheld Control, 3D RF Volume과 JPEG 송신 로컬 프로토타입까지 진행했지만, Graphics 핵심 소스의 Git 반영, 실제 Handheld↔Backend↔Graphics 종단 통합과 최종 논문용 RF 데이터 확보는 남아 있다.

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
| JPEG Image Relay | 구현·테스트 완료 | 실제 Graphics→Handheld 종단 미검증 |
| Handheld JPEG·LCD | 서버 더미 JPEG 실물 출력 완료 | Graphics producer 종단·지속 성능 미검증 |
| Handheld BNO085·LCD | 약 50 Hz Quaternion·로컬 3D 시점 이동 실물 검증 | 버튼·UDP·Graphics 통합 미완료 |
| Handheld Control RFHC v1 | Backend/Embedded 구현·공유 Vector 일치 | 실제 UDP 송신·Graphics 축 미검증 |
| 3D RF Volume Bundle | 구현·테스트 완료 | 높이 방향 Residual은 외삽, 논문 근거 불가 |
| SIBR Heatmap·JPEG Producer | 로컬 프로토타입·빌드 완료 | 핵심 C++ 소스 Git 미반영, 종단 미검증 |
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
- 로컬 SIBR에 RF Volume 합성, Mesh Depth 가림, Offscreen 800×480, RFJF/JPEG 송신 코드와 빌드 결과 존재

남은 작업:

- 계단·문·책상·AP 위치와 재질을 현장 기준으로 보정
- 장면 좌표 오차(현재 계획도 기반 약 ±0.5 m)와 Scale 재검증
- `SIBR_viewers/src/projects/*` ignore 규칙을 수정하고 Graphics 확장 C++ 소스를 Git에 반영
- 깨끗한 Clone에서 SIBR 재빌드·Heatmap 실제 렌더 검증
- `/handheld/control` 구독과 Camera 축·Recenter·Position 적용
- Graphics→Relay→Handheld 300초 지속 FPS 검증

### 임베디드

완료 또는 로컬 검증:

- ESP32 RSSI Node/Gateway, STM32 Parser, Serial-MQTT Bridge
- RSSI 허용 하한 `-110 dBm`과 AP Channel 기본값 6 반영
- Bridge Python 테스트 8개, STM32 Parser Host Test, JPEG Protocol Host Test 4개 통과
- RFHC v1 Serializer Host Test 6개 통과, Backend 공유 52-byte/CRC Vector 일치
- BNO085 독립 Quaternion 실물 시험 완료
- 서버 더미 JPEG의 TCP 수신·디코드·NT35510 LCD 실물 출력 완료
- BNO085와 NT35510 LCD 동시 구동, 부팅 자세 Recenter와 Quaternion 기반 로컬 3D Wireframe 시점 이동 실물 검증
- 로컬 통합 시험에서 BNO085 약 50 Hz를 유지했고 LCD 색상 깨짐·녹색 줄 없이 동작함

실물 검증 필요:

- RSSI 장치 3~5대 정·역방향 전체 리허설과 1~2시간 안정성
- 고정 BSSID/Channel, 사전·사후 Device Offset, Fault Injection
- 버튼·RFHC UDP 송신·네트워크 JPEG-LCD 경로의 단일 Handheld Firmware 통합
- 실제 Graphics Frame으로 800×480 수신·디코드·표시 지속 속도

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
- Image Relay와 Graphics 로컬 producer 코드는 있으나 실제 Handheld와 함께 연결하지 않았다.

## 5. 공통 계약과 통합 상태

### JPEG Frame 기준 구현

Network Relay와 Embedded 수신 프로토타입은 다음 기준을 공유한다.

```text
Graphics ─TCP 9101─▶ Image Relay ─TCP 9102─▶ Handheld
22-byte big-endian header + JPEG payload
magic='RFJF', version=1, flags=0, seq, ts_ms, length
payload 최대 8 MiB
```

Network Relay·Embedded 수신 코드와 Graphics 로컬 sender 프로토타입이 이 규격을 사용한다. 다만 Graphics 핵심 C++ 소스는 아직 Git에 반영되지 않았고 실기기 종단 시험도 없으므로 전체 통합 완료로 보지 않는다. `flags=1` RGB332+zlib 경로는 실험용이며 공통 JPEG 계약에 포함하지 않는다.

### Handheld Control 기준 구현

Embedded와 Backend는 다음 RFHC v1 Wire 규격과 공유 Test Vector를 검증했다.

```text
Handheld ─UDP 9200, 50 Hz─▶ Backend ─WS /handheld/control─▶ Graphics
52-byte big-endian Packet
magic='RFHC', version=1, flags, device_id, session_id
sample_seq, event_seq, timestamp_ms, quaternion x/y/z/w, CRC32/IEEE
500 ms timeout 후 stale
```

Backend Parser·Listener와 Embedded Serializer는 구현됐다. 실제 ESP32-S3 UDP 송신, 버튼 Event, `q_mount`, Graphics Camera 축 적용은 아직 통합하지 않았다.

### 좌표 관리

- 고정 Calibration Node는 각 저장소의 최신 좌표를 사용한다.
- 이동 Node `node-02`의 `(0,0,0)`은 의도된 Placeholder다.
- Test 위치는 전역 `node_positions.json`이 아니라 Backend Experiment Assignment로 관리한다.
- 실험마다 Frame ID, 단위, 원점, 축, Transform, TX/RX 높이를 기록한다.

## 6. 현재 위험

1. **논문 위험:** 분석 수치는 좋아졌지만 누락 구간·BSSID 공란·사후 Offset 부재·잠정 Scene 때문에 최종 근거가 아니다.
2. **통합 위험:** RFHC와 JPEG의 개별 구성요소는 있으나 Handheld→Backend→Graphics→Relay→Handheld 실제 종단 검증이 없다.
3. **저장소 위험:** Graphics `main`은 원격과 일치하지만 `SIBR_viewers/src/projects/*` 규칙 때문에 RF Volume/JPEG 핵심 C++ 소스가 모두 무시되고, 재현에 필요한 소스 대신 일부 빌드 실행 파일만 Git에 포함돼 있다.

## 7. 다음 작업

1. 3층 Scene의 계단·문·책상·AP 위치와 재질을 확정하고 Sionna를 다시 실행한다.
2. 누락된 정방향 Test 1·2와 최소한의 Offset/BSSID 항목만 재측정해 엄격한 10×2 계약을 채운다.
3. 같은 분석을 재실행해 `paper_evidence_eligible`를 재판정한다.
4. Graphics의 SIBR RF Volume/JPEG C++ 소스를 Git에 반영하고 깨끗한 Clone에서 재빌드한다.
5. Graphics가 `/handheld/control`을 구독하고 Camera 축·Recenter·Position을 연결한다.
6. Embedded의 검증된 BNO085·LCD 로컬 통합에 버튼·RFHC UDP·네트워크 JPEG 경로를 연결해 단일 Firmware로 통합한다.
7. Graphics→Relay→Handheld를 연결해 800×480, 300초 지속 FPS를 검증한다.

## 8. 저장소 기준

2026-08-24 문서 수정 직전 확인한 원격 `main` 기준:

| 저장소 | GitHub `main` |
|---|---|
| RFVisualizer | `5408158` |
| Embedded | `a3cab20` |
| Network-Backend-Article | `bfd151d` |
| RFVisualizer-Docs | `3fa9f22` (이 문서 수정 전) |

이번 갱신에서 Graphics 테스트만 재실행했다. Network와 Embedded의 테스트 수는 각 저장소의 최신 기록을 인용했으며 다시 실행하지 않았다.

# RFVisualizer 현재 진행 상태

- 기준일: **2026-08-23**
- 기준: 각 저장소 `main`과 `/data/RFVisualizer_Workspace`의 최신 실험 산출물

## 1. 한 줄 요약

3층 복도 장면·RF 분석과 JPEG 중계/수신 프로토타입까지 구현했지만, 8월 21일 측정은 정방향 2구간이 빠진 **부분 데이터**이며 장면도 잠정 상태라 아직 최종 논문 근거로 사용할 수 없다.

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
| Handheld JPEG·LCD | 독립 프로토타입 구현 | 실제 장치 통합·성능 미검증 |
| Handheld BNO085 | 독립 시험 코드 구현 | 실제 성공 기록·통합 미확인 |
| SIBR Heatmap Viewer | 미구현 | Graphics JPEG producer도 미구현 |
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
- RF 분석 테스트 32개와 Sionna/Proxy 도구 테스트 242개 통과, 1개 건너뜀

남은 작업:

- 계단·문·책상·AP 위치와 재질을 현장 기준으로 보정
- 장면 좌표 오차(현재 계획도 기반 약 ±0.5 m)와 Scale 재검증
- SIBR Heatmap, Depth Pass, Offscreen 800×480, JPEG producer 구현

### 임베디드

완료 또는 로컬 검증:

- ESP32 RSSI Node/Gateway, STM32 Parser, Serial-MQTT Bridge
- RSSI 허용 하한 `-110 dBm`과 AP Channel 기본값 6 반영
- Bridge Python 테스트 8개, STM32 Parser Host Test, JPEG Protocol Host Test 4개 통과
- BNO085, NT35510 LCD, JPEG TCP 수신·디코드의 독립 프로토타입 코드 존재

실물 검증 필요:

- RSSI 장치 3~5대 정·역방향 전체 리허설과 1~2시간 안정성
- 고정 BSSID/Channel, 사전·사후 Device Offset, Fault Injection
- BNO085 + 버튼 + JPEG + LCD의 단일 Handheld 통합
- 실제 ESP32-S3에서 800×480 수신·디코드·표시 속도

### 네트워크

완료 또는 로컬 검증:

- Run/Segment, 사전·사후 Offset, SQLite/JSONL, Export/QC, 동시간 매칭
- 런타임 RSSI 허용 하한 `-110 dBm`
- 현재 테스트 49개 통과
- 별도 `image_relay` 프로세스와 RFJF 22-byte Frame 중계 테스트 8개 통과

현재 제한:

- 실센서 5대 전체 리허설과 재시작/재연결 실제 동작은 미검증이다.
- `backend/parsing.py`의 독립 `ParseConfig()` 기본값은 아직 `-100 dBm`이고, 실제 MQTT 경로는 `Settings(-110)`을 전달한다. 두 기본값을 맞춰야 한다.
- Image Relay는 독립 시험까지 완료했지만 Graphics producer와 실제 Handheld를 함께 연결하지 않았다.

## 5. 공통 계약과 통합 상태

### JPEG Frame 기준 구현

Network Relay와 Embedded 수신 프로토타입은 다음 기준을 공유한다.

```text
Graphics ─TCP 9101─▶ Image Relay ─TCP 9102─▶ Handheld
22-byte big-endian header + JPEG payload
magic='RFJF', version=1, flags=0, seq, ts_ms, length
payload 최대 8 MiB
```

이 규격의 코드·Host Test는 있으나 실제 Graphics sender가 없어 전체 통합 완료로 보지 않는다. `flags=1` RGB332+zlib 경로는 실험용이며 공통 JPEG 계약에 포함하지 않는다.

### 좌표 관리

- 고정 Calibration Node는 각 저장소의 최신 좌표를 사용한다.
- 이동 Node `node-02`의 `(0,0,0)`은 의도된 Placeholder다.
- Test 위치는 전역 `node_positions.json`이 아니라 Backend Experiment Assignment로 관리한다.
- 실험마다 Frame ID, 단위, 원점, 축, Transform, TX/RX 높이를 기록한다.

## 6. 현재 위험

1. **논문 위험:** 분석 수치는 좋아졌지만 누락 구간·BSSID 공란·사후 Offset 부재·잠정 Scene 때문에 최종 근거가 아니다.
2. **통합 위험:** 각 JPEG 구성요소는 있으나 Graphics→Relay→Handheld 실제 종단 검증이 없다.
3. **저장소 위험:** Graphics 로컬 변경은 GitHub `main`보다 앞서 있고, 일반 GitHub 제한을 넘는 약 184 MB PLY가 포함되어 Push 전 LFS 또는 산출물 분리가 필요하다.

## 7. 다음 작업

1. 3층 Scene의 계단·문·책상·AP 위치와 재질을 확정하고 Sionna를 다시 실행한다.
2. 누락된 정방향 Test 1·2와 최소한의 Offset/BSSID 항목만 재측정해 엄격한 10×2 계약을 채운다.
3. 같은 분석을 재실행해 `paper_evidence_eligible`를 재판정한다.
4. Graphics JPEG producer를 연결해 Relay→Handheld 실기기 종단 시험을 한다.
5. 대형 PLY를 저장소에서 분리하거나 LFS로 이관한 뒤 팀 GitHub와 동기화한다.

## 8. 저장소 기준

2026-08-23 확인 시점의 원격 `main` 최신 커밋:

| 저장소 | GitHub `main` |
|---|---|
| RFVisualizer | `e067e76` |
| Embedded | `3bbd984` |
| Network-Backend-Article | `96ae873` |
| RFVisualizer-Docs | `69414f2` |

Graphics 작업 폴더는 로컬 커밋 `102c2d1`까지 진행되어 원격보다 3개 커밋 앞서 있다. 이 문서는 로컬 구현과 실험 산출물을 기준으로 작성했으므로 GitHub 공개 상태와 구분해서 읽는다.

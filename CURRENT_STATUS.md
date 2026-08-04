# RFVisualizer 현재 진행 상태

- 기준일: **2026-08-04**
- 기준 Branch: 세 저장소의 `main`

## 1. 전체 요약

- **그래픽스:** PGSR 장면, 닫힌 Proxy Room, 미터 단위 보정, Sionna RT 연결, Proxy 장애물 편집을 구현했다. 실제 복도 측정값을 이용한 잠정 RF 분석까지 연결했으며, 최종 Viewer는 남아 있다.
- **임베디드:** `gw-01`과 `node-01~04`를 포함한 실물 Node 5대를 측정했다. Device Offset도 산출했지만 반복 안정성이 낮아 최종 보정값으로 확정하지 않았다.
- **네트워크:** Backend Export는 완료했다. 다만 원본 Export의 좌표와 Calibration/Test 역할에 오류·누락이 있어 복원 코드를 적용했으며, 좌표 포함 원본 Export는 아직 미완료다.
- **통합:** 실제 Experiment는 PNU 4층 복도의 `doors_glass_diffraction_scattering_authored_100m_d5` 조건으로 선택했다. Test 1·2를 사용한 잠정 분석은 가능하지만, 최종 논문용 데이터로는 재측정이 권장된다.

## 2. 완료 상태

| 영역 | 상태 |
|---|---|
| PGSR Gaussian Scene | 구현·실행 완료 |
| Room Envelope | 구현·검증 완료 |
| Metric Calibration | 구현·검증 완료 |
| Sionna RT Phase 2-A | 구현·검증 완료 |
| Proxy 장애물 Phase 2-B | 구현·검증 완료 |
| Proxy Placement Editor Phase 2-C | 구현 완료 |
| RF 실험 분석 도구 | 구현·잠정 분석 완료 |
| SIBR Heatmap Viewer | 다음 단계 |
| ESP32 RSSI Node | 구현 완료, 실물 5대 측정 완료 |
| ESP32 Gateway + Local Node 5 | 구현 완료, 실물 5대 측정 완료 |
| STM32 수신·전처리 | 구현·기본 검증 완료 |
| Serial-MQTT Bridge | 구현·기본 연결 완료 |
| 실제 Experiment 선택 | 완료 — PNU 4층 복도 Test 1·2 |
| 실물 Node 3대 이상 측정 | 완료 — 5대 |
| Device Offset 측정 | 완료, 반복 안정성 낮음 |
| 핸드헬드 IMU·버튼 | 계획 |
| JPEG·LCD | 계획 |
| Backend Export | 완료 |
| 좌표 포함 Export | 미완료 |
| Calibration/Test 역할 | 원본 오류, 복원 코드 구현 |
| 실측 RF 분석 | 잠정 분석 가능 |
| 최종 논문용 데이터 | 재측정 권장 |
| 실시간 Frame/WebSocket | 인터페이스 구현, 기본 비활성 |
| PositionEstimate | 인터페이스만 준비 |

## 3. 그래픽스

### 완료

- PGSR Gaussian Scene과 Surface Mesh
- Plane/Wall 후보 추출
- 평면 교점 기반 Room Envelope
- 양방향 Metric Transform
- Sionna Empty Room
- 동일 설정의 Obstacle A/B
- Proxy Placement Editor
- Point Cloud/Room/Mesh 독립 표시
- Box·Thin Panel과 Material Metadata

### 다음 작업

- 원본 Backend Export에 좌표와 Calibration/Test 역할을 포함하도록 수정
- 복원 코드가 아닌 원본 Export 기준으로 동일한 RF 분석을 재실행
- Device Offset과 Calibration 반복 안정성 재측정
- 잠정 분석의 `paper_evidence_eligible=false` 원인을 해소한 뒤 최종 지표 확정
- SIBR Heatmap Viewer 구현

### 최신 잠정 분석

기준 결과는 `PNU 4층 복도 / doors-glass / diffraction+authored scattering / 100m_d5`이며 Test 1·2만 사용했다. Test 3은 철문 상태가 Proxy와 달라 제외했다.

| 항목 | 현재 값 |
|---|---:|
| 실측 Node | 5대: `gw-01`, `node-01~04` |
| Calibration 위치 | 4개 |
| Test 위치 | 6개 독립 위치, Test 1·2 반복 |
| Raw Sionna MAE / RMSE | 14.90 / 15.54 dB |
| 전역 보정 후 MAE / RMSE | 7.48 / 8.58 dB |
| Pearson r | 0.970 |
| Calibration 반복 차이 | 평균 10.25 dB, 최대 16.00 dB |
| Test 반복 차이 | 평균 6.08 dB, 최대 13.00 dB |
| 논문 근거 사용 가능 여부 | 불가 (`paper_evidence_eligible=false`) |

현재 결과는 공간적 경향을 보는 잠정 분석으로만 사용한다. 개별 위치의 절대 RSSI 정확도와 재질·좌표의 최종 타당성은 재측정 뒤 다시 판정한다.

근거 산출물: `RFVisualizer/output/spreadsheet/pnu_4f_corridor_doors_glass_100m_d5_tests_1_2/RESULTS_SUMMARY.md`, `processed/analysis_report.json`

### 아직 미구현

- SIBR Heatmap
- Mesh Depth-only Pass
- Offscreen 800×480
- IMU Pose
- Position Update
- JPEG Streaming

## 4. 임베디드

### 완료 또는 기본 검증

- 실물 Node 5대 RSSI 측정: `gw-01`, `node-01~04`
- Moving Average 5
- ESP-NOW + CRC32
- Gateway Node Table
- Local Node 5
- UART Line Protocol
- STM32 Ring Buffer·Parser·Timeout
- MQTT-ready JSON
- Python Bridge
- `rssi/<node_id>`
- LWT/Heartbeat
- Device Offset 산출

### 실물 검증 필요

- Device Offset 반복 안정성
- Calibration 위치 반복 안정성
- ESP32 3~5대 동시 측정의 재현성
- Broadcast/Unicast 비교
- BSSID 고정
- 채널 고정
- 1~2시간 연속 동작
- Fault Injection
- 장치별 Offset 재측정·안정성 확인
- Raw/Filtered 의미와 배율 확인

### 미구현

- ESP32-S3 Handheld
- IMU와 버튼
- UDP Quaternion
- TCP JPEG
- NT35510 LCD

## 5. 네트워크

### 완료

- MQTT 구독과 Parser
- Raw/Filtered Alias
- x10 Scale
- Invalid Sample 보존
- Timestamp Skew
- Sequence Loss
- Experiment/Session/Assignment
- Device Offset
- SQLite/JSONL
- CSV/JSON Export
- QC
- Rehearsal

### 현재 제한

- Backend 원본 Export의 좌표 열이 완성되지 않아 좌표는 복원 코드로 보완했다.
- 원본 데이터의 Calibration/Test 역할이 잘못되거나 누락되어 복원 코드를 적용했다.
- 따라서 현재 RF 분석은 Export 원본만으로 재현되는 최종 결과가 아니라 잠정 결과다.

### 현재 기본 모드

```env
ENABLE_REALTIME=false
```

### 인터페이스만 구현

- 200 ms Window
- `WS /frames`
- Missing Node
- `GET /position/latest`

Position은 현재 `null`, confidence는 `0.0`이다.

## 6. 통합 시 해결할 항목

### 실제 Experiment 선택 완료

현재 기준 Experiment는 다음으로 고정한다.

- 장소: PNU 4층 복도
- 장면 조건: `doors_glass_diffraction_scattering_authored_100m_d5`
- 사용 반복: `Test_1_004838`, `Test_2_010416`
- 제외 반복: `Test_3_011702` — 철문 상태가 Proxy와 달라 제외
- 측정 Node: `gw-01`, `node-01`, `node-02`, `node-03`, `node-04`
- RF 평가: Calibration 4개, Test 6개 독립 위치

강의실 수치와 복도 수치를 하나의 결과표에 섞지 않는다. 현재 논문용 기준은 복도 Experiment이며, 기존 강의실 산출물은 파이프라인 검증·참고용으로만 둔다.

### Node Position Placeholder

`Embedded/node_positions.json`의 대부분이 `(0,0,0)`이다. 실제 좌표로 사용하면 안 된다.

### BSSID와 Channel

Bring-up SSID/Channel을 최종 실험 설정으로 간주하지 않는다.

### 좌표계

실험마다 다음을 기록한다.

- Frame ID
- 단위
- 원점
- 축
- Transform
- TX/RX 높이

### RSSI와 Sionna 결합 순서

1. 독립 비교
2. Global Offset
3. Residual IDW
4. 필요할 때만 Material Parameter 보정

현재는 위 순서의 잠정 분석까지 완료했다. 다만 Offset과 반복 측정의 변동이 커서 최종 논문용 수치로 확정하지 않는다.

## 7. 다음 작업

1. 각 코드 저장소가 Docs를 참조하도록 README/AGENTS 정리
2. 원본 Backend Export의 좌표와 Calibration/Test 역할 수정
3. 실물 Payload와 복원 결과를 대조하고 Export 재생성
4. Device Offset과 4개 Calibration 위치 반복 재측정
5. Test 1·2 반복 차이를 줄인 뒤 RF 분석 재실행
6. `paper_evidence_eligible=true` 판정 조건을 충족하는 최종 데이터 생성
7. 이후 SIBR Viewer와 Handheld 진행

# RFVisualizer 현재 진행 상태

- 기준일: **2026-08-03**
- 기준 Branch: 세 저장소의 `main`

## 1. 전체 요약

- **그래픽스:** PGSR 장면, 닫힌 Proxy Room, 미터 단위 보정, Sionna RT 연결, Proxy 장애물 편집까지 구현했다. 실제 측정값을 이용한 RF 분석과 최종 Viewer는 남아 있다.
- **임베디드:** ESP32 원격 노드 → Gateway → STM32 → PC MQTT Bridge 경로의 코드와 기본 시험은 구현했다. 다수 실물 노드의 장시간 검증과 핸드헬드는 남아 있다.
- **네트워크:** 논문 실험용 수집·저장·보정·Export 경로를 구현했다. 실시간 200 ms Frame/WebSocket 경로는 기본 비활성이고, 위치 알고리즘은 없다.
- **통합:** 저장소 간 메시지 규격은 연결 가능한 상태지만, 현장 장비·좌표·BSSID를 사용한 최종 End-to-End 시험은 완료되지 않았다.

## 2. 완료 상태

| 영역 | 상태 |
|---|---|
| PGSR Gaussian Scene | 구현·실행 완료 |
| Room Envelope | 구현·검증 완료 |
| Metric Calibration | 구현·검증 완료 |
| Sionna RT Phase 2-A | 구현·검증 완료 |
| Proxy 장애물 Phase 2-B | 구현·검증 완료 |
| Proxy Placement Editor Phase 2-C | 구현 완료 |
| RF 실험 분석 도구 | 구현 진행 |
| SIBR Heatmap Viewer | 계획 |
| ESP32 RSSI Node | 구현 완료, 실물 검증 필요 |
| ESP32 Gateway + Local Node 5 | 구현 완료, 실물 검증 필요 |
| STM32 수신·전처리 | 구현·기본 검증 완료 |
| Serial-MQTT Bridge | 구현·기본 연결 완료 |
| 실물 3대 이상 동시 측정 | 미완료 |
| 핸드헬드 IMU·버튼 | 계획 |
| JPEG·LCD | 계획 |
| 논문 실험 Backend | 구현·로직 검증 완료 |
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

- 실제 Scene과 Experiment 하나 선택
- 실제 장애물 위치·크기·방향 반영
- TX와 Calibration/Test 좌표 통합
- Backend Export 연결
- Raw Sionna, Plain IDW, Residual IDW 비교
- MAE·RMSE 생성

### 아직 미구현

- SIBR Heatmap
- Mesh Depth-only Pass
- Offscreen 800×480
- IMU Pose
- Position Update
- JPEG Streaming

## 4. 임베디드

### 완료 또는 기본 검증

- Node 1~4 RSSI 측정
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

### 실물 검증 필요

- ESP32 3~5대 동시 측정
- Broadcast/Unicast 비교
- BSSID 고정
- 채널 고정
- 1~2시간 연속 동작
- Fault Injection
- 장치별 Offset
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

### 실험 대상 통일

현재 서로 다른 실험이 있다.

- 강의실: Calibration 4 + Test 15
- PNU 4층 복도 예비 실험: Calibration 4 + Test 6, 높이 0.45 m

좌표와 QC 기준을 섞지 않는다.

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

## 7. 다음 작업

1. 각 코드 저장소가 Docs를 참조하도록 README/AGENTS 정리
2. 실제 Experiment 하나 선택
3. 실물 Payload를 `sniff.py`로 확인
4. Placeholder 좌표 제거
5. 장치 Offset과 다중 노드 측정
6. Backend Export → Graphics 연결
7. Sionna/IDW/Residual 결과 생성
8. 이후 SIBR와 Handheld 진행
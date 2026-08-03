# Network / Backend 파트

- 코드 저장소: [Network-Backend-Article](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Network-Backend-Article)
- 담당 범위: MQTT 수집, 데이터 검증·저장, 실험 관리, 장치 Offset, CSV Export, 실시간 WebSocket 인터페이스

## 1. 실행 모드

네트워크/백엔드 저장소에는 두 가지 실행 경로가 있다.

| 구분 | 논문·측정 실험 경로 | 졸업작품 실시간 경로 |
|---|---|---|
| 현재 기본 상태 | 활성 | 비활성 |
| 설정 | `ENABLE_REALTIME=false` | `ENABLE_REALTIME=true` |
| 측정 방식 | 위치별 정지 측정 | 이동 단말 실시간 추적 |
| 기준 저장소 | SQLite + JSONL | PostgreSQL 선택 |
| 파트 간 전달 | CSV/JSON Export | WebSocket |
| 시간 동기화 | 필수 아님 | 200 ms Window |
| PositionEstimate | 사용하지 않음 | 인터페이스만 구현 |

현재 프로젝트의 기본 실행 모드는 논문·측정 실험 경로다.

## 2. 전체 구조

```text
ESP32 / Serial-MQTT Bridge
        ↓
MQTT Broker
        ↓
MQTT Bridge
        ↓
Payload Parser
        ↓
Node Registry / Metrics
        ├─ Experiment Store
        │   ├─ JSONL Raw 저장
        │   ├─ SQLite 저장
        │   ├─ Device Offset
        │   └─ CSV/JSON Export
        │
        └─ Realtime Window
            ├─ 200 ms Frame
            ├─ Missing Node 표시
            └─ WebSocket /frames
```

## 3. MQTT 수집

Backend는 다음 Topic을 구독한다.

```text
rssi/#
gateway/#
status/+/lwt
```

### 개별 RSSI Topic

```text
rssi/<node_id>
```

예시:

```json
{
  "node_id": "node-01",
  "timestamp": 1785720000000,
  "rssi": -61,
  "rssi_raw": -62,
  "seq": 15234,
  "pos_x": 1.25,
  "pos_y": 3.40,
  "pos_z": 0.80,
  "ap_bssid": "AA:BB:CC:DD:EE:FF",
  "status": 0
}
```

### Gateway Batch Topic

```text
gateway/<gateway_id>
```

여러 Node의 Reading을 하나의 Payload로 전달할 때 사용한다.

### 상태 Topic

```text
status/<gateway_id>/lwt
```

LWT와 Heartbeat를 이용해 Gateway의 Online/Offline 상태를 판단한다.

## 4. Payload Parser

주요 코드:

```text
backend/parsing.py
```

Parser는 MQTT Client와 분리되어 있어 Broker 없이 단위 테스트할 수 있다.

### Canonical Field

Backend 내부의 기준 필드:

```text
node_id
timestamp
rssi
rssi_filtered
rssi_raw
sample_count
seq
status
valid
invalid_reason
ap_bssid
ap_channel
pos_x
pos_y
pos_z
rot_w
rot_x
rot_y
rot_z
```

### 호환 필드

| 의미 | 허용 필드 |
|---|---|
| Filtered RSSI | `rssi_filtered_dbm`, `rssi_filtered`, `rssi` |
| Raw RSSI | `rssi_raw_dbm`, `rssi_raw` |
| Channel | `ap_channel`, `channel` |
| Error | `error_flags`, `status` |

새 Producer는 다음 필드를 우선 사용한다.

```text
rssi
rssi_raw
status
```

### RSSI 규칙

```text
rssi = Filtered RSSI, dBm
rssi_raw = Raw RSSI, dBm
```

기본 유효 범위:

```text
-100 dBm ≤ RSSI ≤ -10 dBm
```

### 비정상 값 처리

구조 자체가 손상되어 Node ID와 Timestamp를 확인할 수 없는 메시지만 버린다.

RSSI 값이나 Error Flag가 비정상인 메시지는 삭제하지 않고 다음 상태로 저장한다.

```json
{
  "valid": false,
  "invalid_reason": "error_flags(1)"
}
```

이 방식으로 Raw 데이터는 보존하고, 분석 단계에서만 제외한다.

### Timestamp 처리

Node Timestamp와 Server 수신 시각의 차이가 허용 범위를 크게 벗어나면 Server 수신 시각으로 교체한다.

## 5. Node 상태 관리

Backend는 다음 정보를 관리한다.

- 마지막 수신 시각
- Sequence Number
- Packet Loss
- 중복 Packet
- Online/Offline
- Heartbeat Timeout
- 수집 지연
- Frame 수
- WebSocket 전송 상태

관련 Endpoint:

```text
GET /nodes/status
GET /metrics
GET /monitor
```

## 6. 논문·측정 실험 모델

### 주요 객체

- Experiment
- Measurement Point
- Node Assignment
- Measurement Session
- Device Offset
- TX 정보

### Point Role

| Role | 목적 |
|---|---|
| `offset` | 장치별 수신 감도 편차 측정 |
| `calibration` | RF Field 보정에 사용 |
| `test` | 보정에 사용하지 않고 평가에만 사용 |

### Node Assignment

Sample의 위치는 Session 이름만으로 결정하지 않는다.

고정 Sensor는 실험 전체 동안 같은 위치에 있고, 이동 Sensor만 위치를 바꿀 수 있기 때문이다.

```text
Node → Point Assignment
        ↓
해당 Node가 수신한 Sample의 위치 결정
```

따라서 동일한 Session 동안 여러 고정 Node의 데이터는 각자의 Calibration Point에 누적된다.

## 7. Device Offset

같은 위치에 여러 ESP32를 모아 측정한 `offset` Session을 이용해 장치별 수신 감도 차이를 계산한다.

각 Node의 Offset은 대표 Node 또는 전체 중앙값을 기준으로 계산한다.

최종 대표 RSSI:

```text
corrected_rssi = median_filtered + device_offset_db
```

그래픽스 파트는 기본적으로 `corrected_rssi`를 사용한다.

## 8. 데이터 저장

### JSONL Raw 저장

```text
data/ingest_raw.jsonl
```

MQTT에서 수신한 원본 메시지를 저장한다.

파싱에 실패한 메시지도 가능한 범위에서 원본을 남기는 비상 저장 경로다.

### SQLite

```text
data/experiment.db
```

논문·측정 실험 데이터의 기준 저장소다.

PostgreSQL이 없어도 실험 경로는 동작한다.

### PostgreSQL

기존 실시간 Frame과 WebSocket 경로에서 선택적으로 사용한다.

논문·측정 실험 결과의 기준 저장소는 아니다.

## 9. Experiment API

### 상태

```text
GET /health
GET /nodes/status
GET /metrics
GET /monitor
```

### Experiment

```text
POST /experiment/start
POST /experiment/end
POST /experiment/assign
POST /experiment/tx
POST /experiment/points/import
POST /experiment/offsets/compute
POST /experiment/export
```

### Session

```text
POST /session/start
POST /session/stop
GET  /session/current
```

### 결과 다운로드

```text
GET /experiment/download/{which}
```

## 10. Export

주요 코드:

```text
backend/export.py
```

Export 결과:

```text
experiments/<experiment_id>/
├── raw/
│   └── measurements_raw.csv
│
├── processed/
│   ├── measurements_summary.csv
│   ├── calibration_points.csv
│   └── test_points.csv
│
├── config/
│   ├── points.csv
│   ├── tx_rx.json
│   ├── device_offsets.json
│   └── sessions.json
│
├── qc_report.json
└── README.md
```

### `measurements_raw.csv`

전체 시계열을 저장한다.

주요 열:

```text
experiment_id
session_id
point_id
point_role
node_id
timestamp
server_ts_ms
seq
rssi_raw_dbm
rssi_filtered_dbm
sample_count
error_flags
device_offset_db
pos_x
pos_y
pos_z
ap_bssid
ap_channel
valid
invalid_reason
```

### `measurements_summary.csv`

Point와 Node별 대표값을 저장한다.

```text
point_id
point_role
node_id
x
y
z
sample_count
median_raw
median_filtered
mean_filtered
std_filtered
min_filtered
max_filtered
iqr_filtered
device_offset_db
corrected_rssi
```

### Graphics 기본 입력

그래픽스 파트가 주로 사용하는 열:

```text
x
y
z
corrected_rssi
```

파일 용도:

| 파일 | 용도 |
|---|---|
| `calibration_points.csv` | IDW 또는 Residual 보정 입력 |
| `test_points.csv` | MAE·RMSE 평가 |
| `tx_rx.json` | Sionna RT TX/RX 좌표 |
| `device_offsets.json` | 장치별 RSSI 보정값 |
| `measurements_raw.csv` | 원본 시계열 검증 |

## 11. Quality Check

Export 전에 다음 항목을 검사한다.

- Point별 Sample 수
- 좌표 미등록
- Device Offset 미계산
- Offset이 없는 Node
- TX 좌표 미등록
- Calibration Point 수
- Test Point 수
- Calibration/Test 역할 중복
- 여러 BSSID 혼합
- Invalid Sample 수
- 높은 RSSI 표준편차

### 실험별 QC 기준

현재 기본 QC에는 강의실 계획의 다음 기준이 들어 있다.

```text
Calibration Point: 4개
Test Point: 15개
```

PNU 4층 복도 예비 실험처럼 Test Point가 6개인 실험에서는 이 기준을 그대로 사용하면 Warning이 발생한다.

QC의 기대 Point 수는 Experiment 설정으로 분리하는 것이 필요하다.

## 12. 실시간 경로

실시간 경로는 다음 설정에서 활성화된다.

```env
ENABLE_REALTIME=true
```

현재 기본값은 다음과 같다.

```env
ENABLE_REALTIME=false
```

### 200 ms Window

주요 코드:

```text
backend/realtime/window.py
```

처리 과정:

```text
RSSI Measurement
    ↓
Server 수신 시각 기준 200 ms Bucket
    ↓
Node별 최신 Sample 유지
    ↓
Window 종료
    ↓
rssi_frame 생성
```

같은 Window에 한 Node의 Sample이 여러 개 있으면 가장 최신 Sample을 사용한다.

### WebSocket

Endpoint:

```text
WS /frames
```

Frame 예시:

```json
{
  "type": "rssi_frame",
  "window_ts": 1785720000000,
  "window_size_ms": 200,
  "nodes": {
    "node-01": {
      "rssi": -61,
      "ap_bssid": "AA:BB:CC:DD:EE:FF",
      "seq": 15234,
      "node_ts": 1785720000000,
      "server_receive_ms": 1785720000040,
      "pos": {
        "x": 1.25,
        "y": 3.40,
        "z": 0.80
      },
      "rot": {
        "w": null,
        "x": null,
        "y": null,
        "z": null
      }
    }
  },
  "missing": [
    "node-02"
  ]
}
```

`missing`에는 해당 Window에서 Sample을 받지 못한 Node가 들어간다.

## 13. PositionEstimate

Endpoint:

```text
GET /position/latest
```

현재는 인터페이스만 구현되어 있다.

```json
{
  "timestamp": 1785720000000,
  "position_x": null,
  "position_y": null,
  "position_z": null,
  "confidence": 0.0,
  "status": "interface_ready_algorithm_pending"
}
```

현재 상태:

- API 존재
- Position 자료구조 존재
- 실제 위치 추정 알고리즘 없음
- Graphics Viewer 소비 경로 미연결
- Handheld Position Update 경로 미연결

PositionEstimate를 구현 완료된 위치 추정 기능으로 취급하면 안 된다.

## 14. 테스트

### 계산 로직 테스트

```powershell
python .\tests\test_experiment_pipeline.py
python -m pytest -q
```

검증 내용:

- Calibration Node의 Session 간 누적
- Device Offset 복원
- Corrected RSSI 계산
- Graphics-ready Export
- Invalid Sample 보존
- QC
- 재측정
- 이동 Node의 Test Point 처리
- x10 Scale
- Field Alias

### MQTT End-to-End Rehearsal

```powershell
python .\rehearsal.py --seconds 2
```

이 테스트는 다음 실제 경로를 통과한다.

```text
가상 Node
  ↓ MQTT
Broker
  ↓
Backend
  ↓
Experiment API
  ↓
SQLite
  ↓
CSV Export
```

### UI 시험

```powershell
python .\load_test.py --nodes 5 --rate 1 --duration 900
```

브라우저:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/monitor
```

### 실물 Payload 확인

```powershell
python .\sniff.py
```

확인할 항목:

- Node ID
- Timestamp
- BSSID
- Channel
- `rssi`
- `rssi_raw`
- x10 Scale
- Error Flag
- Sequence

## 15. 현재 구현 상태

### 구현·로직 검증 완료

- MQTT 구독
- Payload Parser
- RSSI Alias
- x10 Scale
- Invalid Sample 보존
- Timestamp Skew 처리
- Sequence Loss
- Node Registry
- Metrics
- Experiment 관리
- Session 관리
- Node Assignment
- Device Offset
- SQLite
- JSONL
- CSV/JSON Export
- Quality Check
- Rehearsal
- 200 ms Window
- WebSocket Interface
- PositionEstimate Interface

### 환경별 재확인 필요

- 실제 개발 PC에서 Backend 기동
- 측정 UI 수동 조작
- 실제 ESP32 Payload
- PostgreSQL 경로
- 다수 WebSocket Client
- Graphics Viewer 연결

### 아직 미구현

- 실제 Position 추정 알고리즘
- Handheld Control Packet 처리
- Viewer Camera Position 전달
- JPEG Streaming Server
- End-to-End 실시간 Viewer 통합

## 16. 운영 원칙

### 측정 중 Reload 금지

측정 중에는 다음 옵션을 사용하지 않는다.

```text
uvicorn --reload
```

코드 파일이 변경되면 Backend가 재시작되어 진행 중인 Session이 중단될 수 있다.

### 실험 전 확인

- `.env`의 `ENABLE_REALTIME`
- `RSSI_FILTERED_SCALE`
- MQTT Host와 Port
- BSSID와 Channel
- Expected Sample Count
- 실험 ID
- TX 좌표
- Point 좌표
- Node Assignment

### 실험 종료 전 확인

- `qc_report.json`
- Calibration/Test 파일
- Device Offset
- 여러 BSSID 혼합 여부
- 좌표 누락 여부
- TX 좌표
- JSONL 백업
- SQLite 백업
- Export 폴더 백업

## 17. 다음 작업

1. 실제 ESP32 Payload를 `sniff.py`로 확인한다.
2. `rssi`가 Filtered dBm인지 최종 확인한다.
3. x10 Scale을 확인한다.
4. 실제 Experiment의 TX와 Point 좌표를 등록한다.
5. Device Offset을 계산한다.
6. 실물 Node를 이용한 End-to-End 측정을 수행한다.
7. Export 결과를 Graphics 파트에 전달한다.
8. QC의 기대 Point 수를 Experiment별 설정으로 분리한다.
9. 논문·측정 경로가 안정화된 뒤 Realtime 경로를 활성화한다.
10. PositionEstimate 알고리즘과 Graphics Viewer 연결을 구현한다.

## 18. 코드 저장소에 유지할 문서

다음 문서는 실제 설치·실행·시험 절차와 연결되므로 Network 저장소에 유지한다.

```text
README.md
TESTING.md
```

다만 다음 내용은 중앙 문서와 중복하지 않도록 축소한다.

- 프로젝트 전체 목표
- 다른 파트의 책임
- 공통 MQTT 규격
- Graphics Export 계약
- 전체 프로젝트 진행 상태

공통 인터페이스는 `RFVisualizer-Docs/INTERFACE.md`를 기준으로 한다.
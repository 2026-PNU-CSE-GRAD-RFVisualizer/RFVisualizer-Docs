# RFVisualizer 파트 간 인터페이스

이 문서는 그래픽스, 임베디드, 네트워크/백엔드 파트 사이에서 실제로 주고받는 데이터의 **현재 기준**을 정의한다.

공통 데이터 형식이나 Topic을 변경할 때는 각 코드 저장소의 문서를 먼저 수정하지 않고, 이 문서를 먼저 갱신한다.

---

## 1. 공통 규칙

### 1.1 시간

- 외부 메시지의 `timestamp`는 **Unix Epoch millisecond**를 사용한다.
- 임베디드 내부의 `uptime_ms`는 장치 부팅 후 경과 시간을 의미한다.
- Backend는 Node Timestamp가 Server 수신 시각과 크게 어긋나면 Server 수신 시각으로 교체할 수 있다.
- 시간 단위가 다른 값을 `timestamp`라는 동일한 필드명으로 전송하지 않는다.

### 1.2 RSSI

- 단위: `dBm`
- 기본 유효 범위: `-110 dBm` 이상, `-10 dBm` 이하
- `rssi`: 필터링된 RSSI
- `rssi_raw`: 필터링 전 원시 RSSI
- `rssi_filtered_x10`: 임베디드 내부에서 사용하는 10배 Fixed-point 값

예시:

```text
실제 값: -60.8 dBm
Fixed-point 값: -608
```

새 Producer는 MQTT 메시지에서 다음 규칙을 사용한다.

```text
rssi     = Filtered RSSI, dBm
rssi_raw = Raw RSSI, dBm
```

### 1.3 좌표

- 단위: `meter`
- `X`, `Y`: 바닥 평면
- `+Z`: 위쪽
- 원점과 `+X`, `+Y` 방향은 Experiment 또는 Scene별 설정에 기록한다.
- 강의실과 복도처럼 서로 다른 실험의 좌표를 혼합하지 않는다.
- Node 위치, TX 위치, RX 위치, Graphics Scene 위치는 같은 좌표계를 사용하는지 반드시 확인한다.

### 1.4 Node ID

현재 임베디드 내부 ID와 외부 ID의 기본 대응은 다음과 같다.

| 내부 숫자 ID | 외부 문자열 ID |
|---:|---|
| `1` | `node-01` |
| `2` | `node-02` |
| `3` | `node-03` |
| `4` | `node-04` |
| `5` | `gw-01` |

Gateway는 ESP-NOW 수신기 역할과 함께 로컬 RSSI Node 5 역할을 수행할 수 있다.

---

## 2. ESP32 RSSI Node → ESP32 Gateway

ESP32 RSSI Node는 특정 AP의 RSSI를 측정하고 ESP-NOW Binary Packet으로 Gateway에 전달한다.

### 2.1 Packet 구조

```c
#define RSSI_PACKET_MAGIC   0x52465349u
#define RSSI_PACKET_VERSION 1

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint8_t  version;
    uint8_t  node_id;
    uint16_t payload_len;

    uint32_t seq;
    uint32_t uptime_ms;

    uint8_t  ap_bssid[6];
    int8_t   rssi_raw_dbm;
    int16_t  rssi_filtered_x10;
    uint8_t  sample_count;
    uint16_t error_flags;

    uint32_t crc32;
} rssi_node_packet_t;
```

### 2.2 필드 의미

| 필드 | 의미 |
|---|---|
| `magic` | RSSI Packet 식별값 |
| `version` | Packet Schema Version |
| `node_id` | ESP32 Node의 숫자 ID |
| `payload_len` | Payload 크기 |
| `seq` | Packet 순번 |
| `uptime_ms` | Node 부팅 후 경과 시간 |
| `ap_bssid` | 측정 대상 AP의 BSSID |
| `rssi_raw_dbm` | 원시 RSSI |
| `rssi_filtered_x10` | 필터링된 RSSI의 10배 정수값 |
| `sample_count` | 필터 계산에 사용한 Sample 수 |
| `error_flags` | 측정 또는 통신 오류 상태 |
| `crc32` | Packet 무결성 검사용 CRC32 |

### 2.3 CRC 규칙

`crc32` 필드를 `0`으로 둔 상태에서 전체 Struct를 대상으로 CRC32를 계산한다.

### 2.4 Sequence 규칙

- `seq`는 Packet을 전송할 때마다 증가한다.
- Gateway와 STM32는 `seq`를 이용해 중복과 누락을 계산한다.
- Packet 전송 실패가 발생해도 다음 측정 Packet에서는 `seq`가 계속 증가해야 한다.

### 2.5 Channel 규칙

초기 프로토타입에서는 다음 조건을 사용한다.

```text
Target AP Channel == ESP-NOW Channel
```

대상 AP의 Channel이 바뀌면 모든 RSSI Node와 Gateway 설정을 함께 변경해야 한다.

---

## 3. ESP32 Gateway → STM32

Gateway는 ESP-NOW Packet을 검증한 뒤 UART Line Protocol로 STM32에 전달한다.

### 3.1 UART 설정

```text
Baudrate: 115200
Logic Level: 3.3 V

ESP32 Gateway TX → STM32 UART RX
ESP32 Gateway RX ← STM32 UART TX  (선택)
ESP32 GND        → STM32 GND
```

현재 단계에서는 STM32 ACK를 사용하지 않으므로 Gateway TX와 STM32 RX만으로 동작할 수 있다.

### 3.2 RSSI Line

```text
$RSSI,<node_id>,<seq>,<uptime_ms>,<rssi_raw>,<rssi_filtered_x10>,<sample_count>,<error_flags>*<checksum>
```

실제 전송 시 Line 마지막에 LF 문자(`\n`)를 추가한다.

예시:

```text
$RSSI,1,15234,3600123,-62,-608,5,0*5A
```

### 3.3 Gateway Status Line

```text
$GWSTAT,<uptime_ms>,<rx_count>,<crc_error_count>,<queue_drop_count>*<checksum>
```

### 3.4 Checksum 규칙

Checksum은 `$` 다음 문자부터 `*` 직전 문자까지 XOR한 값이다.

두 자리 대문자 16진수로 출력한다.

---

## 4. STM32 → Python Serial-MQTT Bridge

STM32는 UART Line을 파싱하고 Node별 최신 상태를 JSON으로 출력한다.

### 4.1 현재 권장 JSON 형태

```json
{
  "schema_version": 2,
  "gateway_id": "gw-01",
  "timestamp": 1785720000000,
  "readings": [
    {
      "node_id": 1,
      "rssi": -61,
      "rssi_raw": -62,
      "seq": 15234,
      "status": 0,
      "ap_bssid": "AA:BB:CC:DD:EE:FF"
    }
  ]
}
```

### 4.2 필수 의미

| 필드 | 의미 |
|---|---|
| `schema_version` | STM32 JSON Schema Version |
| `gateway_id` | 데이터를 전달한 Gateway ID |
| `timestamp` | JSON Snapshot 생성 시각 |
| `readings` | Node별 최신 RSSI 목록 |
| `readings[].node_id` | Node 숫자 ID 또는 문자열 ID |
| `readings[].rssi` | 필터링된 RSSI |
| `readings[].rssi_raw` | 원시 RSSI |
| `readings[].seq` | Node Packet Sequence |
| `readings[].status` | 오류 상태 |
| `readings[].ap_bssid` | 측정 대상 AP BSSID |

### 4.3 이전 Schema 호환

Python Bridge는 다음과 같은 이전 STM32 Payload도 읽을 수 있다.

```json
{
  "device_id": "stm32-01",
  "nodes": [
    {
      "node_id": 1,
      "rssi_filtered_x10": -608,
      "rssi_raw_dbm": -62,
      "seq": 15234,
      "error_flags": 0
    }
  ]
}
```

새 코드는 `readings` 배열을 사용하는 Schema Version 2 형식을 우선한다.

---

## 5. Python Serial-MQTT Bridge → MQTT

Python Bridge는 STM32 JSON을 정규화하고 MQTT Broker에 발행한다.

### 5.1 개별 RSSI Topic

```text
rssi/<node_id>
```

예시:

```text
rssi/node-01
rssi/node-02
rssi/gw-01
```

### 5.2 개별 RSSI Payload

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

### 5.3 필드 의미

| 필드 | 필수 여부 | 의미 |
|---|---:|---|
| `node_id` | 필수 | 외부 문자열 Node ID |
| `timestamp` | 필수 | Unix Epoch millisecond |
| `rssi` | 필수 | 필터링된 RSSI, dBm |
| `rssi_raw` | 권장 | 원시 RSSI, dBm |
| `seq` | 필수 | Packet 누락·중복 검사 |
| `pos_x` | 실험에 따라 필수 | Node X 좌표, meter |
| `pos_y` | 실험에 따라 필수 | Node Y 좌표, meter |
| `pos_z` | 실험에 따라 필수 | Node Z 좌표, meter |
| `ap_bssid` | 권장 | 측정 대상 AP BSSID |
| `status` | 필수 | `0`이면 정상 |

Node 위치는 Bridge의 위치 설정 또는 Backend의 Experiment Assignment 중 하나에서 관리한다.

두 위치 정보가 동시에 존재할 경우 어느 값이 기준인지 Experiment 문서에 명시한다.

### 5.4 Gateway Batch Topic

선택적으로 여러 Node Reading을 하나의 Payload로 발행할 수 있다.

```text
gateway/<gateway_id>
```

예시:

```text
gateway/gw-01
```

### 5.5 Gateway 상태 Topic

```text
status/<gateway_id>/lwt
```

Payload:

```json
{
  "node_id": "gw-01",
  "online": true,
  "timestamp": 1785720000000
}
```

상태 메시지는 다음 설정을 사용한다.

```text
QoS: 1
Retained: true
```

---

## 6. MQTT → Network Backend

Backend는 다음 Topic을 구독한다.

```text
rssi/#
gateway/#
status/+/lwt
```

### 6.1 Backend Canonical Field

Backend 내부에서는 다음 필드명을 기준으로 사용한다.

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

### 6.2 호환 Field Alias

| 의미 | 허용 필드 |
|---|---|
| Filtered RSSI | `rssi_filtered_dbm`, `rssi_filtered`, `rssi` |
| Raw RSSI | `rssi_raw_dbm`, `rssi_raw` |
| AP Channel | `ap_channel`, `channel` |
| 오류 상태 | `error_flags`, `status` |

새 Producer는 다음 필드를 사용한다.

```text
rssi
rssi_raw
status
```

### 6.3 비정상 Sample 처리

구조가 손상되어 `node_id`와 `timestamp`를 확인할 수 없는 메시지는 버릴 수 있다.

RSSI 값이나 Error Flag가 비정상인 Sample은 삭제하지 않고 다음 상태로 저장한다.

```json
{
  "valid": false,
  "invalid_reason": "error_flags(1)"
}
```

이 Sample은 Raw 데이터에는 남지만 대표 RSSI 계산과 RF Field 보정에서는 제외한다.

### 6.4 Timestamp 보정

Node Timestamp와 Server 수신 시각의 차이가 설정된 허용 범위를 초과하면 Backend가 Server 수신 시각으로 교체할 수 있다.

---

## 7. Backend Experiment 모델

Backend는 측정 데이터를 다음 단위로 관리한다.

```text
Experiment
├── TX
├── Measurement Point
├── Node Assignment
├── Measurement Session
├── Device Offset
└── Measurement Sample
```

### 7.1 Point Role

| Role | 목적 |
|---|---|
| `offset` | 여러 장치의 수신 감도 차이 계산 |
| `calibration` | RF Field 보정에 사용 |
| `test` | 보정에 사용하지 않고 평가에만 사용 |

### 7.2 Node Assignment

Sample 위치는 Session 이름만으로 결정하지 않는다.

```text
Node → Point Assignment
        ↓
해당 Node에서 수신된 Sample의 위치 결정
```

고정 Calibration Node는 여러 Session 동안 같은 Point에 계속 데이터를 누적할 수 있다.

이동 Test Node만 Session 사이에 다른 Point로 재배치한다.

### 7.3 Device Offset

같은 위치에서 여러 장치를 동시에 측정하여 장치별 수신 감도 차이를 계산한다.

대표 RSSI는 다음과 같이 계산한다.

```text
corrected_rssi = median_filtered + device_offset_db
```

| 값 | 의미 |
|---|---|
| `median_filtered` | 해당 Point와 Node의 Filtered RSSI 중앙값 |
| `device_offset_db` | 장치별 수신 감도 보정값 |
| `corrected_rssi` | Graphics 파트가 기본적으로 사용하는 보정 RSSI |

---

## 8. Network Backend → Graphics

Backend는 Experiment 결과를 다음 구조로 Export한다.

```text
experiments/<experiment_id>/
├── raw/
│   └── measurements_raw.csv
├── processed/
│   ├── measurements_summary.csv
│   ├── calibration_by_test_window.csv
│   ├── calibration_points.csv
│   └── test_points.csv
├── config/
│   ├── points.csv
│   ├── tx_rx.json
│   ├── device_offsets.json
│   ├── runs.json
│   └── test_segments.json
├── qc_report.json
└── README.md
```

### 8.1 `measurements_raw.csv`

전체 시계열 데이터를 저장한다.

주요 열:

```text
experiment_id
session_id
run_id
segment_id
direction
pass_index
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

### 8.2 `measurements_summary.csv`

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

### 8.3 Graphics 기본 입력

Graphics 파트는 다음 값을 기본 입력으로 사용한다.

```text
x
y
z
corrected_rssi
```

### 8.4 파일별 용도

| 파일 | 용도 |
|---|---|
| `processed/calibration_by_test_window.csv` | 각 Test Segment와 같은 시간창의 C1~C4, 평가 시 IDW/Residual IDW 입력 |
| `processed/calibration_points.csv` | Run 전체 Calibration 진단·Viewer 정적 Volume 입력, Test별 평가에 공통 재사용 금지 |
| `processed/test_points.csv` | MAE·RMSE 평가 |
| `processed/measurements_summary.csv` | 전체 Point의 대표값 |
| `config/tx_rx.json` | Sionna RT TX/RX 좌표 |
| `config/device_offsets.json` | 장치별 RSSI 보정값 |
| `config/runs.json` | 정·역방향 Run과 pre/post Offset 연결 |
| `config/test_segments.json` | Test 순서·시도·기록 시간·discard/supersede 상태 |
| `raw/measurements_raw.csv` | 원본 시계열 검증 |
| `qc_report.json` | 실험 품질 검사 결과 |

Test별 평가는 `test_points.csv.segment_id`와
`calibration_by_test_window.csv.segment_id`를 연결해 같은 시간창의 Calibration만 사용한다.
`calibration_points.csv`의 Run 전체 평균을 모든 Test에 공통 적용하지 않는다.

Test Point는 보정에 사용하지 않고 평가에만 사용한다.

---

## 9. 실시간 RSSI WebSocket

실시간 경로는 기본적으로 비활성 상태다.

```env
ENABLE_REALTIME=false
```

활성화하면 Backend는 RSSI Sample을 200 ms Window로 동기화할 수 있다.

### 9.1 WebSocket Endpoint

```text
WS /frames
```

### 9.2 RSSI Frame

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

### 9.3 Frame 규칙

- `window_ts`: 200 ms Window 시작 시각
- `window_size_ms`: 현재 기본값 `200`
- 동일 Window에 한 Node의 Sample이 여러 개 있으면 가장 최신 Sample을 사용
- `missing`: 해당 Window에서 Sample을 받지 못한 Node 목록
- Position과 Rotation이 없으면 `null`을 허용

---

## 10. PositionEstimate

실제 위치 추정 알고리즘은 아직 없다. Realtime의 `GET /position/latest`는 기존
PositionEstimate 인터페이스이고, Handheld 통합 시험은 별도의 설정 좌표 Provider를 사용한다.

```text
GET /position/latest
```

현재 응답:

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

Handheld 설정 좌표 Provider 상태:

- HTTP Endpoint 존재
- Position 자료구조 존재
- `PositionProvider`와 `ConfiguredPositionProvider` 존재
- 설정 좌표의 null, 2초 stale, confidence 0.5, `frame_id` 검증 존재
- Handheld 관리 API `/handheld/positions`, `/handheld/position/active` 존재
- 현재 시연 좌표: `pnu_3f_corridor_metric_v1`, `demo-1=(21.40, 17.80, 1.60)`
- 실제 위치 추정 알고리즘 없음
- Graphics Viewer의 `/handheld/control` Consumer는 구현·자동 검증 완료, 실기기 종단은 미검증
- Handheld Position Update의 Backend 처리와 accepted/rejected 응답은 구현됐고, Graphics는 §11.6 규칙으로 적용한다

설정 좌표 Provider는 통합 시연용이며 구현 완료된 위치 추정 알고리즘으로 취급하지 않는다. 좌표 단위는 meter, `+Z`는 위쪽이며 Backend Position과 Graphics Scene의 `frame_id`가 같아야 한다.

---

## 11. Handheld Control Interface

Embedded와 Backend가 RFHC v1 Wire 규격과 공유 Test Vector를 검증했다. Backend Parser·UDP Listener와 Embedded Serializer는 구현됐고, Graphics의 `/handheld/control` Consumer와 Camera 적용도 구현·자동 검증했다. 실제 ESP32-S3 UDP 송신과 BNO085 실물 축 시험은 남아 있다.

### 11.1 전송

| 항목 | 값 |
|---|---|
| Transport | UDP |
| Backend Port | `9200` |
| 주기 | 50 Hz, 20 ms |
| Byte Order | 모든 다중 Byte 필드 Big-endian |
| Float | IEEE-754 binary32의 32-bit 표현을 Big-endian 전송 |
| Packet 크기 | 52 byte 고정 |
| Timeout | 마지막 유효 Packet 이후 500 ms에 stale |

### 11.2 RFHC v1 Packet

Magic은 ASCII `RFHC`, 정수값 `0x52464843`이다. C Struct를 그대로 전송하지 않고 아래 Offset에 맞춰 직렬화한다.

| Offset | 크기 | 필드 | 설명 |
|---:|---:|---|---|
| 0 | 4 | `magic` | `0x52464843` (`RFHC`) |
| 4 | 1 | `version` | `1` |
| 5 | 1 | `flags` | 아래 Flag 정의 |
| 6 | 2 | `packet_length` | 항상 `52` |
| 8 | 4 | `device_id` | `1` = `handheld-01`, RSSI Node ID와 별도 Namespace |
| 12 | 4 | `session_id` | 부팅마다 바뀌는 non-zero 값 |
| 16 | 4 | `sample_seq` | Packet마다 1 증가, wrap 허용 |
| 20 | 4 | `event_seq` | 새 버튼 Event마다 1 증가 |
| 24 | 8 | `timestamp_ms` | SNTP 동기화 시 Unix epoch ms, 아니면 `0` |
| 32 | 4 | `quaternion_x` | Handheld 논리 축 Quaternion X |
| 36 | 4 | `quaternion_y` | Handheld 논리 축 Quaternion Y |
| 40 | 4 | `quaternion_z` | Handheld 논리 축 Quaternion Z |
| 44 | 4 | `quaternion_w` | Handheld 논리 축 Quaternion W |
| 48 | 4 | `crc32` | Offset 0~47에 대한 CRC32/IEEE |

CRC는 CRC-32/ISO-HDLC를 사용한다.

```text
Polynomial: 0x04C11DB7
RefIn/RefOut: true
Init: 0xFFFFFFFF
XorOut: 0xFFFFFFFF
Check("123456789"): 0xCBF43926
```

### 11.3 Flag와 Event

| Bit | 이름 | 의미 |
|---:|---|---|
| 0 | `ORIENTATION_VALID` | finite이며 norm 0.97~1.03인 Quaternion |
| 1 | `REQUEST_POSITION_UPDATE` | Backend 최신 유효 Position 적용 요청 |
| 2 | `RECENTER_ORIENTATION` | 현재 방향을 Graphics 기준 정면으로 설정 요청 |
| 3 | `TIME_SYNCED` | `timestamp_ms`가 Unix epoch ms로 유효 |
| 4~7 | Reserved | 송신 시 0, 수신 시 non-zero이면 거부 |

버튼 Event는 동일 Flag와 `event_seq`를 3개 연속 Packet에 반복한다. Backend는 `(device_id, session_id, event_seq, flag)`로 중복을 제거하고 정확히 한 번 처리한다.

`TIME_SYNCED=0`이면 `timestamp_ms=0`이며 Backend 수신 시각을 사용한다. `session_id`가 바뀌면 Backend는 Handheld 재부팅으로 처리하고 Sequence 상태를 초기화한다.

### 11.4 Quaternion 좌표축

LCD를 사용자가 정면에서 볼 때 Handheld 논리 축은 다음과 같다.

- `+X`: 화면 오른쪽
- `+Y`: 화면 위쪽
- `+Z`: 화면에서 사용자 방향

Wire Packet은 BNO085 Breakout 원시 축이 아니라 고정 장착 변환 `q_mount`가 반영된 Handheld 논리 축 Quaternion을 사용한다. 실제 `q_mount`와 Graphics Camera 축 변환은 장착 방향 고정 후 Yaw·Pitch·Roll 90도 실물 시험으로 확정한다.

### 11.5 공유 Test Vector

입력:

```text
version=1, flags=0x01, device_id=1, session_id=0x12345678
sample_seq=1, event_seq=0, timestamp_ms=0
quaternion=(0,0,0,1)
```

기대 52 byte:

```text
52464843010100340000000112345678000000010000000000000000000000000000000000000000000000003F8000000AE927E5
```

Embedded Serializer와 Backend Parser Test에서 전체 Byte와 CRC `0x0AE927E5`가 일치했다.

### 11.6 Backend → Graphics

Graphics는 Backend WebSocket `/handheld/control`을 구독한다. Transport는 plain `ws://`이고
Path는 `/handheld/control` 고정이다. Graphics는 application-level Message를 보내지 않는다.

#### Message

`handheld_state`

| 필드 | 형 | 비고 |
|---|---|---|
| `type` | string | `"handheld_state"` |
| `device_id` | string | 현재 Graphics는 `handheld-01`만 받는다 |
| `session_id`, `sample_seq`, `event_seq` | uint32 | wrap 허용 |
| `server_timestamp_ms` | integer | |
| `orientation_valid`, `recenter_event`, `position_update_event`, `stale` | boolean | |
| `quaternion` | `{x,y,z,w}` finite number | Handheld 논리 축 |

`position_update`

| 필드 | 형 | 비고 |
|---|---|---|
| `type` | string | `"position_update"` |
| `device_id` | string | |
| `event_seq` | uint32 | 대응하는 `handheld_state`의 `event_seq` |
| `accepted` | boolean | |
| `position` | object 또는 null | accepted면 `frame_id`, finite `x`,`y`,`z`, `confidence`, `source` |
| `reason` | string | rejected일 때 |

Malformed 또는 모르는 Message는 연결을 끊지 않고 경고 후 폐기한다.

#### Graphics 적용 규칙

- Orientation은 Position과 독립적으로 계속 적용한다.
- 새 sample은 `0 < (new_sample_seq - previous_sample_seq) mod 2^32 < 2^31`일 때만 Camera에 반영한다.
  duplicate와 out-of-order는 버린다. `stale=true`는 같은 `sample_seq`여도 먼저 처리한다.
- Session이 바뀌면 이전 Session을 물러나게 하고 sample·event 상태를 초기화한다.
  물러난 Session의 늦은 Packet은 영구 거부한다.
- Recenter와 Position은 `(device_id, session_id, event_seq, event 종류)`로 각각 중복을 제거한다.
  버튼 Event의 3회 반복, stale snapshot, 재접속 snapshot에서 최대 한 번만 적용한다.
- Position은 `position_update` 응답과 `position_update_event=true` state가 **같은 WebSocket
  연결 안에서** `(connection_epoch, device_id, event_seq)`로 짝지어졌고, `accepted=true`,
  숫자가 모두 finite, `position.frame_id`가 Scene manifest의 `frameId`와 정확히 같을 때만
  적용한다. 두 Message의 도착 순서는 어느 쪽이든 지원한다.
- Position은 Camera translation만 바꾸고 rotation은 보존한다.
- 연결이 끊기면 완성되지 않은 Position 짝은 버린다. Backend는 `position_update`를
  cache/replay하지 않으므로 **단절 중 놓친 Position은 복구할 수 없다.**
- WebSocket 재접속만으로는 Session/Sample/Event 중복 제거 상태를 초기화하지 않는다.

---

## 12. JPEG Frame Streaming Interface

Network `image_relay`와 Embedded Handheld 수신 프로토타입이 사용하는 **기준 구현**이다.
정수는 모두 big-endian이며 producer→relay와 relay→viewer가 같은 Frame을 사용한다.

```text
Graphics ─TCP 9101─▶ image_relay ─TCP 9102─▶ Handheld / Viewer

22-byte 고정 Header
magic   uint32  0x52464A46 ('RFJF')
version uint8   1
flags   uint8   0 (JPEG)
seq     uint32  Frame마다 1 증가
ts_ms   uint64  Unix Epoch millisecond
length  uint32  JPEG Payload 길이
payload bytes   length만큼의 JPEG, 최대 8 MiB
```

- Header 위반 또는 8 MiB 초과 Frame은 연결을 끊고 재접속으로 복구한다.
- 느린 Viewer는 오래된 Frame을 버리고 최신 완성 Frame을 우선한다.
- 권장 출력 해상도는 Handheld 화면 기준 800×480이다.
- `flags=1` RGB332+zlib는 실험용이며 이 공통 JPEG 계약에 포함하지 않는다.
- Network Relay와 Embedded Parser의 Host Test는 통과했다.
- 서버 더미 JPEG→ESP32-S3 수신·디코드·NT35510 LCD 실물 출력은 통과했다.
- Graphics Workspace에는 PBO Readback·JPEG Encoding·RFJF 송신 producer 프로토타입이 있다.
- 해당 Graphics C++ 소스는 `.gitignore`의 `!src/projects/gaussianviewer/**` 예외로 Git에서 추적된다.
- 실제 Graphics producer→Relay→Handheld 실기기 종단 시험은 아직 완료하지 않았다.

남은 확정 항목:

- JPEG Quality와 실제 목표 FPS
- 수신 Timeout과 장치별 재연결 정책
- ESP32-S3 Buffer 크기와 실제 LCD Throughput

---

## 13. 인터페이스 변경 절차

다음 항목은 각 코드 저장소에서 독립적으로 변경하면 안 된다.

- MQTT Topic
- `rssi`와 `rssi_raw`의 의미
- Node ID 형식
- Timestamp 단위
- 좌표 단위와 축
- ESP-NOW Packet 구조
- UART Line 구조
- STM32 JSON Schema
- Backend Field Alias
- CSV 열
- `corrected_rssi` 계산
- WebSocket Frame
- PositionEstimate
- Handheld Packet
- JPEG Frame Protocol

변경 절차:

1. 변경 이유와 영향을 `RFVisualizer-Docs` Issue 또는 PR에 작성한다.
2. `INTERFACE.md` 수정안을 먼저 검토한다.
3. 영향을 받는 파트 담당자가 합의한다.
4. `INTERFACE.md`를 병합한다.
5. 각 코드 저장소를 수정한다.
6. 관련 테스트를 실행한다.
7. `CURRENT_STATUS.md`를 갱신한다.

---

## 14. 현재 확인이 필요한 항목

- 실제 STM32 JSON이 `readings` Schema Version 2를 사용하고 있는지
- `rssi`가 실제로 Filtered RSSI인지
- Raw RSSI에도 x10 Scale이 적용되는지
- 최종 실험 BSSID
- 최종 실험 Wi-Fi Channel
- 실제 Node ID와 설치 위치의 대응
- Bridge 위치 정보와 Backend Assignment 중 어느 값을 기준으로 사용할지
- 강의실 Experiment와 복도 Experiment의 좌표계 분리
- `/handheld/control`을 Graphics Camera에 적용하는 축 변환·Recenter 규칙
- PositionEstimate 알고리즘
- BNO085 실제 장착 변환 `q_mount`와 Graphics Camera 축 변환
- Graphics C++ 소스 Git 반영과 깨끗한 Clone 재빌드
- JPEG 실기기 종단 연동과 300초 성능값

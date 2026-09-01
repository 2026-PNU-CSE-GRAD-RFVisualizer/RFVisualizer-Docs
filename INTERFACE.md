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

**2026-08-28 기획 변경**: Position Update 버튼 기획을 폐기하면서 위 Provider를 트리거하던
`position_update` WS Message(§11.6)도 폐기했다. `PositionProvider`/`ConfiguredPositionProvider`와
REST Endpoint(`/handheld/positions`, `/handheld/position/active`) 코드 자체는 지우지 않고
남겨둔다 — 다른 용도(수동 테스트, 향후 위치 추정 연동)로 다시 쓸 수 있으므로 Network 파트
재량으로 유지한다. 다만 버튼으로 이어지는 경로는 없다.

설정 좌표 Provider는 통합 시연용이며 구현 완료된 위치 추정 알고리즘으로 취급하지 않는다. 좌표 단위는 meter, `+Z`는 위쪽이며 Backend Position과 Graphics Scene의 `frame_id`가 같아야 한다.

---

## 11. Handheld Control Interface

Embedded와 Backend가 RFHC v1 Wire 규격과 공유 Test Vector를 검증했다. Backend Parser·UDP Listener와 Embedded Serializer는 구현됐고, Graphics의 `/handheld/control` Consumer와 Camera 적용도 구현·자동 검증했다. 실제 ESP32-S3 UDP 송신과 BNO085 실물 축 시험은 남아 있다.

**2026-08-28 기획 변경**: Position Update 버튼·Recenter 버튼 기획은 폐기했다. bit1·bit2를
**텔레포트 버튼**·**Height-cycle 버튼**으로 재정의한다(§11.3). 이 절은 새 정의를
반영했다. 2026-09-01 Embedded Firmware의 기존 50 Hz ControlTxTask에도 두 버튼의
debounce된 held-state 송신이 연결됐으며, 실제 장치 UDP 종단 검증은 남아 있다.

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
| 20 | 4 | `event_seq` | 2026-08-28부터 미사용, `0` 고정 송신(구조체·CRC 계산에는 영향 없음) |
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

### 11.3 Flag와 버튼 상태

| Bit | 이름 | 의미 |
|---:|---|---|
| 0 | `ORIENTATION_VALID` | finite이며 norm 0.97~1.03인 Quaternion |
| 1 | `TELEPORT_BUTTON_HELD` | 텔레포트 버튼을 지금 물리적으로 누르고 있으면 1 (레벨 상태) |
| 2 | `HEIGHT_CYCLE_BUTTON_HELD` | Height-cycle 버튼을 지금 물리적으로 누르고 있으면 1 (레벨 상태) |
| 3 | `TIME_SYNCED` | `timestamp_ms`가 Unix epoch ms로 유효 |
| 4~7 | Reserved | 송신 시 0, 수신 시 non-zero이면 거부 |

bit1·bit2는 **레벨 상태**다. Embedded는 debounce된 물리 버튼의 그 순간 상태를 매
Packet(50 Hz)에 그대로 싣는다. bit0(`ORIENTATION_VALID`)과 같은 취급이며, RECENTER/POSITION
UPDATE가 쓰던 "3-packet 반복 + `event_seq` dedup" 방식은 **쓰지 않는다.** Press/hold/release
edge 판정은 수신 측(Graphics)이 연속된 Frame의 레벨 값 변화로 직접 계산한다. Packet
하나가 유실돼도 다음 Packet에서 상태가 이어지므로 Backend가 중복 제거를 할 필요가 없다.

`TIME_SYNCED=0`이면 `timestamp_ms=0`이며 Backend 수신 시각을 사용한다. `session_id`가 바뀌면 Backend는 Handheld 재부팅으로 처리하고 Sequence 상태를 초기화한다.

> 2026-08-28 이전에는 bit1=`REQUEST_POSITION_UPDATE`, bit2=`RECENTER_ORIENTATION`이었고
> 둘 다 edge 이벤트였다. 그 기획은 폐기했다. `event_seq` 필드 자체는 Packet 구조에 남지만
> bit1·bit2에는 더 이상 쓰지 않는다.

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

`handheld_state` (유일한 Message 타입. `position_update`는 2026-08-28에 폐기했다)

| 필드 | 형 | 비고 |
|---|---|---|
| `type` | string | `"handheld_state"` |
| `device_id` | string | 현재 Graphics는 `handheld-01`만 받는다 |
| `session_id`, `sample_seq` | uint32 | wrap 허용 |
| `server_timestamp_ms` | integer | |
| `orientation_valid`, `teleport_button_held`, `height_cycle_button_held`, `stale` | boolean | 전부 그 순간의 레벨 상태 |
| `quaternion` | `{x,y,z,w}` finite number | Handheld 논리 축 |

Malformed 또는 모르는 Message는 연결을 끊지 않고 경고 후 폐기한다.

#### Graphics 적용 규칙

- Orientation은 계속 적용한다. Position은 이 경로로 갱신하지 않는다(§10 `PositionEstimate`
  경로와는 별개다).
- 새 sample은 `0 < (new_sample_seq - previous_sample_seq) mod 2^32 < 2^31`일 때만 Camera에 반영한다.
  duplicate와 out-of-order는 버린다. `stale=true`는 같은 `sample_seq`여도 먼저 처리한다.
- Session이 바뀌면 이전 Session을 물러나게 하고 sample 상태를 초기화한다.
  물러난 Session의 늦은 Packet은 영구 거부한다.
- `teleport_button_held`·`height_cycle_button_held`는 **레벨 상태를 그대로 받는다.**
  `event_seq` 기반 중복 제거나 3회 반복 처리는 하지 않는다 — Graphics가 연속 Frame의
  값 변화로 press(0→1)/hold(1)/release(1→0) edge를 직접 계산한다(키보드 입력과 동일 패턴).
  `stale=true`인 Frame은 두 값 모두 0으로 취급해 눌림이 이어진 것으로 오판하지 않는다.
- 텔레포트는 `teleport_button_held`의 hold~release로 `ArcTeleportController`를 그대로
  구동한다. 조준 방향은 이미 적용 중인 Camera rotation(§11.6 위 규칙)을 그대로 쓴다.
- Height-cycle은 `height_cycle_button_held`의 press edge마다 RF Volume manifest의 다음
  높이 층으로 1칸 순환한다.
- WebSocket 재접속만으로는 Session/Sample/Event 중복 제거 상태를 초기화하지 않는다.

---

## 12. RFJF Frame Streaming Interface

Network `image_relay`와 Embedded Handheld 수신 프로토타입이 사용하는 **기준 구현**이다.
정수는 모두 big-endian이며 producer→relay와 relay→viewer가 같은 Frame을 사용한다.

```text
Graphics ─TCP 9101─▶ image_relay ─TCP 9102─▶ Handheld / Viewer

22-byte 고정 Header
magic   uint32  0x52464A46 ('RFJF')
version uint8   1
flags   uint8   0 = JPEG, 1 = RGB332+zlib, 2 = 팔레트256+zlib
seq     uint32  Frame마다 1 증가
ts_ms   uint64  Unix Epoch millisecond
length  uint32  Payload 길이
payload bytes   length만큼의 Payload, 최대 8 MiB
```

Header는 세 형식이 완전히 같고 `flags`만 다르다. Relay는 `flags`를 해석하지 않고
22-byte Header와 length만큼의 Payload를 그대로 viewer(9102)로 중계한다.

### 12.1 `flags=2` 팔레트 256색+zlib (현재 채택 규격, 2026-08-27부터)

**Handheld 영상의 채택 규격이다.** 장면에서 고른 256색 팔레트를 Frame마다 함께 실어 보낸다.
픽셀당 1 byte와 수신 측 확장 비용은 `flags=1`과 같고, 고정 3-3-2 대신 장면에 실제로 있는
색을 써서 화질이 개선된다.

- 화면 크기는 Handheld LCD 기준 **정확히 800×480**이다. Producer는 다른 해상도로 이 형식을
  시작하지 않는다.
- 압축 전 Payload는 팔레트와 인덱스를 이어 붙인 **정확히 384,512 byte**다.

```text
offset      0   512 B       팔레트 256 entry, entry당 uint16 RGB565 big-endian
offset    512   384,000 B   인덱스, 픽셀당 1 byte, row-major, 위에서 아래로
합계            384,512 byte
```

- 팔레트 `entry[i]`가 인덱스 값 `i`의 색이다. RGB565 bit 배치는 `r5 << 11 | g6 << 5 | b5`다.
- 전송 Payload는 이 384,512 byte를 **표준 `zlib` Stream**(RFC 1950) level 1로 압축한 것이다.
- 수신 측은 해제 결과가 384,512 byte가 아니면 그 Frame을 버린다.
- **팔레트는 모든 Frame에 들어간다.** Producer가 세션 내내 같은 값을 보내더라도 수신 측은
  Frame마다 읽어야 한다. Relay는 상태를 갖지 않으므로 수신자가 중간에 붙거나 재접속할 수
  있고, 그때도 Frame 하나만으로 색을 복원할 수 있어야 한다.
- 수신 측은 팔레트가 Frame마다 바뀔 수 있다고 가정한다. Producer의 갱신 정책은 계약이 아니다.
- Graphics는 장면 색 분포로 팔레트를 고르는 `PaletteChooser`를 별도 Thread에서 돌리고,
  장면 전환이나 팔레트 적합도 저하 시 다시 고른다.
- 상태: **채택. 2026-08-27 Graphics→Relay→ESP32-S3→NT35510 LCD 실기 출력을 확인했고,
  RGB332 대비 화질 개선도 확인했다.** 300초 지속 FPS·지연·drop은 아직 계측하지 않았다.

### 12.2 `flags=1` RGB332+zlib (호환·진단 경로)

`flags=2` 채택 전까지 쓰던 규격이며 지금은 호환·진단용으로 유지한다.

- 화면 크기는 `flags=2`와 같이 **정확히 800×480**이다.
- 압축 전 Payload는 픽셀당 1 byte RGB332, row-major, stride 없음, 위에서 아래로
  **정확히 384,000 byte**다. bit 배치는 `rgb332 = (R & 0xE0) | ((G >> 3) & 0x1C) | (B >> 6)`이다.
  순수 Red는 `0xE0`, Green은 `0x1C`, Blue는 `0x03`, White는 `0xFF`다.
- 전송 Payload는 이 384,000 byte를 **표준 `zlib` Stream**(RFC 1950) level 1로 압축한 것이다.
  수신 측은 압축 수준에 의존하지 않는다.
- 수신 측은 해제 결과가 384,000 byte가 아니면 그 Frame을 버린다.
- Producer는 고정 4×4 Bayer Ordered Dithering을 걸 수 있다. 픽셀 값만 달라지고
  크기·배치·`flags`는 그대로이므로 **수신 측 계약에는 영향이 없다**.
- 2026-08-27 Graphics producer→Relay→Handheld 실기기 종단 연동을 이 경로로 먼저
  확인했다(렌더 송신과 `/handheld/control` IMU 회전 동시 구동).

### 12.3 `flags=0` JPEG (단일 이미지·안정성 경로)

- Payload는 JPEG Baseline Stream이다. 해상도 제약은 없고 권장값은 같은 800×480이다.
- 단일 이미지 전송과 안정성 확인 경로로 유지한다.
- **10 FPS를 목표로 하는 실시간 영상 경로로는 쓰지 않는다.** ESP32-S3의 소프트웨어 JPEG
  디코드는 800×480에서 Frame당 수백 ms가 걸린다. 실측에서 Quality를 10부터 100까지 바꿔도
  표시율은 약 2 FPS로 같았다. 디코드 비용이 압축률이 아니라 픽셀 수에 비례하기 때문이다.

### 12.4 공통 규칙

- Header 위반 또는 8 MiB 초과 Frame은 연결을 끊고 재접속으로 복구한다.
- 느린 Viewer는 오래된 Frame을 버리고 최신 완성 Frame을 우선한다.
  최신 Frame 우선 정책에서 생기는 `seq` 건너뜀은 정상이다.
- Network Relay와 Embedded Parser의 Host Test는 통과했다.
- 서버 더미 JPEG→ESP32-S3 수신·디코드·NT35510 LCD 실물 출력은 통과했다.
- `flags=1`·`flags=2` 두 경로 모두 Graphics producer→Relay→Handheld 실기기 종단
  연동을 확인했다.
- Graphics Workspace에는 PBO Readback·형식별 Encoding·RFJF 송신 producer가 있고,
  RGB332/팔레트256 변환·zlib round-trip·Header 계약은 `SIBR_frame_codec_test`로 검증한다.
- 해당 Graphics C++ 소스는 `.gitignore`의 `!src/projects/gaussianviewer/**` 예외로
  Git에서 추적된다.

남은 확정 항목:

- 300초 지속 성능값과 형식별 표시율(FPS·지연·drop)
- `flags=2` Dithering·팔레트 갱신 주기 최종값
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
- RFJF Frame Protocol (JPEG · RGB332+zlib · 팔레트256+zlib)

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
- PositionEstimate 알고리즘
- BNO085 실제 장착 변환 `q_mount`와 Graphics Camera 축 변환
- RFJF 300초 지속 성능값과 형식별 표시율(FPS·지연·drop)
- Embedded 버튼 Event·RFHC UDP 송신을 단일 Handheld Firmware로 통합

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
- 기본 유효 범위: `-100 dBm` 이상, `-10 dBm` 이하
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
│   ├── calibration_points.csv
│   └── test_points.csv
├── config/
│   ├── points.csv
│   ├── tx_rx.json
│   ├── device_offsets.json
│   └── sessions.json
├── qc_report.json
└── README.md
```

### 8.1 `measurements_raw.csv`

전체 시계열 데이터를 저장한다.

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
| `processed/calibration_points.csv` | IDW 또는 Residual IDW 보정 입력 |
| `processed/test_points.csv` | MAE·RMSE 평가 |
| `processed/measurements_summary.csv` | 전체 Point의 대표값 |
| `config/tx_rx.json` | Sionna RT TX/RX 좌표 |
| `config/device_offsets.json` | 장치별 RSSI 보정값 |
| `raw/measurements_raw.csv` | 원본 시계열 검증 |
| `qc_report.json` | 실험 품질 검사 결과 |

Calibration Point는 RF 보정에 사용한다.

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

PositionEstimate Endpoint는 현재 인터페이스만 구현되어 있다.

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

현재 상태:

- HTTP Endpoint 존재
- Position 자료구조 존재
- 실제 위치 추정 알고리즘 없음
- Graphics Viewer와 연결되지 않음
- Handheld Position Update와 연결되지 않음

이 Endpoint를 구현 완료된 위치 추정 기능으로 취급하지 않는다.

---

## 11. Handheld Control Interface

이 절은 현재 구현된 규격이 아니라 **계획 중인 초안**이다.

### 11.1 Control Packet 초안

```c
struct HandheldControlPacket {
    uint64_t timestamp;

    float quaternion_x;
    float quaternion_y;
    float quaternion_z;
    float quaternion_w;

    bool request_position_update;
    bool recenter_orientation;
};
```

의미:

- Quaternion은 Camera Orientation 갱신에 사용한다.
- `request_position_update=true`이면 최신 PositionEstimate 적용을 요청한다.
- `recenter_orientation=true`이면 현재 방향을 기준 방향으로 다시 설정한다.

### 11.2 미확정 항목

- Packet Version
- Byte Order
- Struct Padding
- CRC 또는 Checksum
- UDP Port
- Packet 전송 주기
- Timeout
- Quaternion 좌표축 규약
- Camera 축 변환 규칙

위 항목이 확정되기 전까지 이 Struct를 파트 간 최종 규격으로 사용하지 않는다.

---

## 12. JPEG Frame Streaming Interface

이 절은 현재 구현된 규격이 아니라 **계획 중인 초안**이다.

현재 우선 후보:

```text
Length Header + JPEG Payload over TCP
```

아직 확정하지 않은 항목:

- TCP Port
- Protocol Version
- Frame Header 구조
- Header Byte Order
- Frame Sequence
- Timestamp
- JPEG Quality
- 최대 JPEG 크기
- 수신 Timeout
- 손상 Frame 처리
- ESP32-S3 JPEG Buffer 구조
- 재연결 절차

Render, Encode, Network Thread는 분리하고 오래된 Frame을 폐기하는 구조를 우선한다.

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
- 실시간 WebSocket을 Graphics에서 실제로 사용할지
- PositionEstimate 알고리즘
- Handheld UDP/TCP Protocol

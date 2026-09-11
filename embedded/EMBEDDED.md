# Embedded 파트

- 코드 저장소: [Embedded](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Embedded)
- 담당 범위: RSSI 측정 노드, ESP32 Gateway, STM32 수신·전처리, MQTT Bridge, 핸드헬드 장치

## 1. 현재 임베디드 구조

현재 구현된 RSSI 측정 경로는 다음과 같다.

```text
ESP32 원격 RSSI 노드 1~4
        │ ESP-NOW
        ▼
ESP32 Gateway + 로컬 RSSI 노드 5
        │ UART 115200 bps
        ▼
STM32F107VCT6
        │ JSON over Serial
        ▼
Python Serial-MQTT Bridge
        │ MQTT
        ▼
Network Backend
```

현재 구조에서는 각 ESP32 노드가 MQTT Broker에 직접 접속하지 않는다.

원격 노드는 ESP-NOW로 Gateway에 데이터를 보내고, Gateway가 UART를 통해 STM32에 전달한다. STM32가 데이터를 검증·정리하여 JSON을 생성하면 PC의 Python Bridge가 MQTT에 발행한다.

## 2. 구현 범위

### 2.1 MVP-A: 고정 RSSI 측정 경로

현재 우선 구현 범위다.

- ESP32 원격 RSSI 노드 4대
- ESP32 Gateway 1대
- Gateway의 로컬 RSSI 노드 5 기능
- 특정 AP의 RSSI 측정
- RSSI 필터링
- ESP-NOW 전송
- UART 전달
- STM32 수신·전처리
- MQTT-ready JSON 생성
- PC Serial-MQTT Bridge
- Backend 전달

### 2.2 MVP-B: 핸드헬드 방향·버튼

BNO085 독립 Quaternion 실물 시험과 RFHC v1 Serializer 공유 Vector 검증은 완료했다.
추가로 `handheld_jpeg_stream`에서 BNO085와 NT35510 LCD를 동시에 구동하고, 부팅 자세를
정면으로 삼는 Recenter와 Quaternion 기반 로컬 3D Wireframe 시점 이동을 실물 검증했다.
`app_main`은 실제 50 Hz UDP 송신 Task에서 Serializer를 호출한다. 2026-09-01에는 같은
Task에 GPIO17 텔레포트·GPIO19 Height-cycle 버튼의 active-low 입력과 25 ms debounce를
통합했고, RFHC bit1·bit2와 `event_seq=0` 직렬화를 Host Test로 확인했다. 2026-09-06 최종
실물 시험에서는 두 버튼의 held/released UDP 상태와 BNO085 Yaw·Pitch·Roll 방향/부호를
확인했고, Handheld→Backend→Graphics 종단 경로의 Camera 자세 갱신, 텔레포트 hold/release,
Height-cycle press edge 동작까지 검증했다.

- ESP32-S3
- IMU Quaternion
- UDP Orientation 전송
- 텔레포트 버튼(누르는 동안 조준, 떼면 이동)
- Heatmap Z-height 프리셋 순환 버튼
- PC Viewer Camera 방향 갱신

2026-08-28에 기획이 바뀌어 방향 Recenter 버튼·Position Update 버튼은 폐기했다. 작업
지시서를 이 파트에 전달 완료했다. 상세 규격은 `INTERFACE.md` §11 참고.

### 2.3 MVP-C: JPEG·LCD

서버 더미 RFJF/JPEG의 수신·디코드·NT35510 LCD 실물 출력과 실제 Graphics producer를
포함한 종단 출력은 완료했다. 영상·IMU·버튼을 함께 활성화한 실기기 구성으로 300초 이상
연속 운용했으며 화면 정지나 기능 중단 없이 안정적으로 동작했다.

- TCP JPEG Frame 수신
- JPEG 디코딩
- RGB565 변환
- Waveshare 480×800 LCD 출력
- 최소 5 FPS
- 도전 목표 10 FPS
- 최신 Frame 우선 처리

## 3. ESP32 원격 RSSI Node

주요 코드 경로:

```text
rssi_esp32_to_stm32/esp32_node/
```

### 설정값

각 Node에서 다음 값을 설정한다.

```text
NODE_ID
TARGET_AP_USE_BSSID
TARGET_AP_SSID
TARGET_AP_BSSID
TARGET_AP_CHANNEL
ESPNOW_WIFI_CHANNEL
GATEWAY_ESPNOW_MAC
```

Node마다 `NODE_ID`는 고유해야 한다.

### RSSI 측정

현재 RSSI 측정은 Wi-Fi Scan을 기반으로 한다.

처리 과정:

```text
특정 AP Scan
  ↓
SSID 또는 BSSID 일치 확인
  ↓
Raw RSSI 획득
  ↓
유효 범위 검사
  ↓
Moving Average
  ↓
Filtered RSSI 생성
  ↓
ESP-NOW Packet 전송
```

현재 필터:

```text
Moving Average Window = 5
```

Filtered RSSI는 Fixed-point x10으로 전송한다.

```text
-60.8 dBm → -608
```

### ESP-NOW Packet

Packet에는 다음 정보가 포함된다.

- Magic
- Version
- Node ID
- Sequence Number
- Uptime
- AP BSSID
- Raw RSSI
- Filtered RSSI x10
- Sample Count
- Error Flags
- CRC32

`seq`는 누락과 중복을 판단하는 데 사용한다.

`error_flags=0`은 정상 상태를 의미한다.

### Task 구조

```text
RssiMeasureTask
EspNowTxTask
HealthTask
```

RSSI 측정과 ESP-NOW 전송은 서로 분리되어 있다.

## 4. ESP32 Gateway

주요 코드 경로:

```text
rssi_esp32_to_stm32/esp32_gateway/
```

Gateway의 역할:

- 여러 Node의 ESP-NOW Packet 수신
- Magic, Version, CRC 검증
- Node별 최신 Sequence 관리
- 중복 Packet 수 집계
- 누락 Packet 수 집계
- Queue Drop 집계
- UART Line 생성
- STM32로 전달
- Gateway 자체 RSSI 측정

Gateway는 자신을 로컬 RSSI 노드 5로 사용할 수 있다.

```text
GATEWAY_LOCAL_NODE_ID = 5
```

### Fake RSSI Mode

원격 Node가 준비되지 않은 초기 시험에서는 Gateway가 Fake RSSI Line을 생성할 수 있다.

Fake Mode는 통신 경로와 Parser 시험에만 사용한다. 실제 측정 데이터나 논문 실험에는 사용하지 않는다.

## 5. Gateway → STM32 UART

기본 설정:

```text
UART: UART1
Baudrate: 115200
TX GPIO: 17
RX GPIO: 18
Logic Level: 3.3 V
```

배선:

```text
ESP32 GPIO17 TX → STM32 UART RX
ESP32 GPIO18 RX ← STM32 UART TX
ESP32 GND       → STM32 GND
```

STM32에서 ACK를 사용하지 않는 현재 단계에서는 Gateway TX → STM32 RX만 연결해도 된다.

### RSSI Line

```text
$RSSI,<node_id>,<seq>,<uptime_ms>,<rssi_raw>,<rssi_filtered_x10>,<sample_count>,<error_flags>*<checksum>
```

### Gateway Status Line

```text
$GWSTAT,<uptime_ms>,<rx_count>,<crc_error_count>,<queue_drop_count>*<checksum>
```

Checksum은 `$` 다음부터 `*` 전까지의 문자를 XOR하여 계산한다.

## 6. STM32 수신·전처리

주요 코드 경로:

```text
rssi_esp32_to_stm32/stm32_receiver/
stm32_final_term/
```

### 주요 모듈

| 모듈 | 역할 |
|---|---|
| `rssi_line_parser` | UART Line과 Checksum 파싱 |
| `rssi_preprocessor` | Node Table, Timeout, Sequence Loss 관리 |
| `mqtt_payload` | MQTT-ready JSON 생성 |
| `uart_rx_ring` | UART RX Interrupt용 Ring Buffer |
| `test_parser_host` | PC Host Parser Test |

Parser와 Preprocessor는 Dynamic Allocation을 사용하지 않는다.

### UART 처리 원칙

UART Interrupt Callback에서는 무거운 처리를 하지 않는다.

```text
UART RX Interrupt
    ↓
Ring Buffer에 Byte 저장
    ↓
Main Loop 또는 Task
    ↓
Line Parser
    ↓
Checksum·Format 검증
    ↓
Node Table 갱신
```

### STM32 출력

STM32는 Node별 최신값을 모아 JSON을 생성한다.

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
      "status": 0
    }
  ]
}
```

STM32는 MQTT Client를 직접 실행하지 않는다. 현재 MQTT 전송은 PC Python Bridge가 담당한다.

## 7. Python Serial-MQTT Bridge

주요 파일:

```text
stm32_serial_mqtt_bridge.py
```

기본 설정:

```text
Serial Port: COM4
Baudrate: 115200
MQTT Port: 1883
Gateway ID: gw-01
Publish Mode: individual
```

주요 기능:

- STM32 JSON Line 읽기
- 이전·현재 JSON Schema 호환
- Node ID 정규화
- Filtered RSSI 변환
- Node 위치 결합
- MQTT QoS 1 Publish
- Publish Retry
- MQTT Reconnect
- LWT
- Heartbeat
- 중복 Sequence 발행 방지

### MQTT Topic

개별 Node:

```text
rssi/<node_id>
```

Gateway Batch:

```text
gateway/<gateway_id>
```

Gateway 상태:

```text
status/<gateway_id>/lwt
```

### RSSI 필드 의미

```text
rssi     = Filtered RSSI, dBm
rssi_raw = Raw RSSI, dBm
```

## 8. Node Position 관리

현재 저장소의 `node_positions.json`에는 대부분의 좌표가 `(0,0,0)`인 Placeholder 값이 들어 있다.

이 값을 실제 실험 좌표로 사용하면 안 된다.

권장 관리 방식:

```text
node_positions.example.json → 형식 예시
node_positions.local.json   → 실제 배치, Git에 Commit하지 않음
```

또는 논문 실험에서는 Node의 위치를 Backend의 Experiment Assignment 기능으로 관리한다.

Experiment별 위치를 전역 `node_positions.json`에 고정해서는 안 된다.

## 9. Wi-Fi Channel 규칙

ESP-NOW와 Wi-Fi Scan은 Channel의 영향을 받는다.

최종 계측에서는 다음 조건을 사용했다.

```text
Target AP Channel == ESP-NOW Channel
```

최종 실험에서 다음 항목을 확인하고 설정했다.

- 대상 AP의 실제 BSSID
- 대상 AP의 실제 Channel 6
- 모든 Node와 Gateway의 Channel 6 일치
- 다섯 장치의 Node ID와 Gateway 역할

실제 BSSID와 인증 정보는 공개 문서에 고정값으로 기록하지 않고 로컬 설정에서 관리했다.

## 10. 현재 검증 상태

### 구현 및 검증 완료

- ESP32 Node Firmware Build
- ESP32 Gateway Firmware Build
- Moving Average Filter
- ESP-NOW Packet
- CRC32
- Gateway Node Table
- Local Node 5
- UART Line Protocol
- STM32 Parser
- UART Ring Buffer
- Node Timeout
- MQTT-ready JSON
- Parser Host Test
- STM32 Flash 이력
- Python MQTT Bridge
- MQTT Publish
- Backend 연결
- BNO085 독립 시험 코드와 Quaternion 실물 시험
- NT35510 LCD 독립 시험 코드
- JPEG TCP 수신·RFJF Parser·LCD 출력 프로토타입
- 서버 더미 JPEG의 ESP32-S3 수신·디코드·LCD 실물 출력
- BNO085 약 50 Hz Quaternion과 NT35510 LCD 동시 구동
- 부팅 자세 Recenter와 Quaternion 기반 로컬 3D Wireframe 시점 이동 실물 검증
- 로컬 통합 시험에서 LCD 색상 깨짐·녹색 줄 없이 동작
- RFHC v1 52-byte Serializer와 Backend 공유 CRC Vector 일치
- 텔레포트·Height-cycle 버튼 GPIO 입력, 25 ms debounce, RFHC held-state bit 연결 구현
- 실제 버튼을 각각·동시에 조작해 RFHC bit1·bit2 held/released UDP 상태와 `event_seq=0` 확인
- BNO085 Yaw·Pitch·Roll 방향/부호와 `q_mount=identity`·Graphics 고정 축 변환 조합 확인
- Handheld→Backend→Graphics Camera 자세, 텔레포트 hold/release, Height-cycle press edge 종단 실물 검증
- 다섯 대 ESP32를 Calibration 4대와 이동 Test 1대로 사용한 최종 RSSI 계측 및 잔차 계산 완료
- Test 1--10 정방향·역방향 20개 반복 관측과 모든 구간의 동시간 Calibration 데이터 확보
- 고정 AP Channel과 장치별 RSSI Offset을 적용한 분석 입력 생성 완료
- 영상·BNO085·두 버튼 통합 상태의 300초 이상 실기기 연속 운용 및 안정 동작 확인
- Python Bridge 테스트 8개, RFJF Protocol Host Test 5개, RFHC Serializer Host Test 7개 통과
- STM32 Parser/Preprocessor/JSON Host Test 통과
- RGB565→RGB666 변환의 전 65,536색·두 Pixel 위치 및 추가 Pair/Guard 등가성 시험 통과

Host Test는 2026-09-11 현재 Embedded 저장소의 소스로 다시 실행해 통과를 확인했다. 실기기
통합 상태는 최종 RSSI 계측, 2026-09-06 자세·버튼 종단 시험과 300초 이상 연속 운용 결과를
반영한다.

### 완료 판정과 평가 범위

- 다중 ESP32 계측은 최종 잔차 계산의 입력을 생성한 핵심 실험 경로이며 검증 완료 상태다.
- Handheld 영상·자세·버튼 경로는 실기기 종단 동작과 300초 이상 지속 안정성을 확인했다.
- Broadcast/Unicast 비교, 대체 Filter 비교와 소비전력은 최종보고서의 완료 기준이 아니라
  선택적인 운영 최적화 또는 후속 연구 범위다.
- ESP32 RSSI의 장치·안테나 의존성과 UART 이후 표본 단위 BSSID 미전달은 정확도 및 추적성의
  한계로 기록하되, 완료된 다중 노드 계측을 미검증으로 분류하지 않는다.

## 11. 핸드헬드 하드웨어 구성

### ESP32-S3

기준 보드:

```text
ESP32-S3-DEVKITC-1-N16R8
Flash: 16 MB
PSRAM: 8 MB
```

핸드헬드는 다음 기능만 담당한다.

- IMU 읽기
- Quaternion 전송
- 버튼의 debounce된 현재 눌림 상태 전송
- RFJF Frame 수신
- zlib 해제와 palette lookup 또는 JPEG 디코딩
- LCD 출력

3DGS 렌더링, Sionna RT, 위치 추정 알고리즘은 PC 또는 Backend에서 실행한다.

버튼 배선:

| 기능 | GPIO | 극성·Pull | Debounce |
|---|---:|---|---:|
| 텔레포트 held | GPIO17 | active-low, 내부 Pull-up | 25 ms |
| Height-cycle held | GPIO19 | active-low, 내부 Pull-up | 25 ms |

텔레포트 버튼은 누른 채 조준하고 떼는 동작 중 손목 방향이 흐트러지지 않도록 검지로 누를
수 있는 측면에, Height-cycle 버튼은 동시에 잘못 누르지 않도록 윗면 또는 뒤쪽에 분리해 둔다.
GPIO19는 Native USB D-와 공유하므로 Flash·Log에는 USB-to-UART 포트를 사용한다.

### LCD

구매한 LCD:

```text
Resolution: 480×800
Driver: NT35510
Interface: 16-bit 8080 Parallel
Touch: XPT2046 SPI
Logic Level: 3.3 V
```

RGB565 전체 Frame 크기:

```text
480 × 800 × 2 byte = 768,000 byte
```

기본 Buffer 전략:

```text
RFJF Compressed Buffer A/B
        ↓
flags=2 zlib 해제 + RGB565 Palette Lookup
        ↓
RGB666 Panel DMA Tile Buffer
        ↓
LCD GRAM
```

전체 RGB565 Triple Buffer를 기본 전략으로 사용하지 않는다.

### IMU

우선순위:

1. BNO085/BNO080
2. BNO055
3. 순수 6축 IMU는 후순위

센서 퓨전 결과로 Quaternion 또는 Rotation Vector를 직접 제공하는 Smart IMU를 우선 사용한다.

## 12. 핸드헬드 Task 구성

```text
ImuTask
ControlTxTask (버튼 GPIO sample·debounce + RFHC 50 Hz UDP)
VideoRxTask
IndexedInflateTask / JpegDecodeTask
DisplayTask
ConnectionTask
HealthTask
```

### Orientation

- IMU Orientation은 지속적으로 갱신
- `INTERFACE.md`의 RFHC v1로 Backend UDP `9200`에 50 Hz 전송
- 부팅 자세 Recenter와 300초 이상 실기기 운용으로 자세 갱신의 안정 동작 확인
- 현재 장착은 Embedded `q_mount=identity`와 Graphics 고정 축 변환 조합으로 Yaw·Pitch·Roll 방향/부호 검증 완료
- 센서 장착 방향 변경 시 `q_mount` 또는 Graphics 고정 변환 재검증

### 버튼 (2026-08-28 기획 변경, 상세 규격은 `INTERFACE.md` §11)

방향 Recenter·Position Update 버튼 기획은 폐기했다. 물리 버튼 2개를 다음 용도로 쓴다.
그래픽스 쪽(`HandheldControlClient`·Viewer Consumer)은 이미 새 규격으로 구현·CTest
검증까지 마쳤다(`graphics/GRAPHICS.md` §8.3). 2026-09-06에는 실제 버튼이 연결된
Handheld로 RFHC UDP와 Viewer 종단 동작까지 실물 검증했다.
연속 6DoF 추적은 여전히 쓰지 않는다 — 실제 Position 계산은 PC/Backend 담당, 버튼은 값을
직접 계산하지 않고 상태만 올린다.

- **텔레포트 버튼**(RFHC bit1): 누르는 동안(레벨 상태) 1을 매 Packet 싣는다. PC Viewer가
  누른 동안 조준·뗄 때 이동을 전부 처리한다. Embedded는 debounce된 물리 상태만 올린다.
- **Height-cycle 버튼**(RFHC bit2): 누르는 동안(레벨 상태) 1을 매 Packet 싣는다. press
  edge마다 PC Viewer가 Heatmap Z-height 프리셋을 한 칸 순환한다.
- 두 버튼 모두 3-packet 반복이나 `event_seq` 관리가 필요 없다(기존 Recenter/Position
  Update 버튼과 다른 점 — §13 참고).
- 별도 InputTask를 만들지 않고 기존 ControlTxTask의 20 ms 주기에서 두 GPIO를 읽는다.

### Video

- TCP 기반 RFJF Frame 수신
- 기본 형식은 `flags=2` palette256+zlib, `flags=0/1`은 호환·진단용
- 해제 결과 384,512 byte 검증 후 512-byte RGB565 BE 팔레트를 Frame마다 다시 읽음
- 최신 완성 Frame 우선
- 해제·출력이 느릴 경우 오래된 Frame 폐기
- 최소 목표 5 FPS
- 도전 목표 10 FPS

2026-08-27 Graphics→Relay/Proxy→ESP32-S3→NT35510 실기 출력과 RGB332 대비 화질 개선을
확인했다. 이후 영상·BNO085·두 버튼을 함께 구동한 상태로 300초 이상 연속 운용하여 화면 정지와
기능 중단 없이 안정적으로 동작함을 확인했다.

## 13. 후속 연구 및 운영 개선

1. ESP-NOW Packet version 2의 `measurement_timestamp_ms`를 중앙 `INTERFACE.md`에 반영한다.
2. ESP-NOW Packet의 AP BSSID를 UART Line과 STM32 JSON까지 유지하도록 추적성을 개선한다.
3. 배터리 구동 시간, 휴대형 Case와 장시간 사용자 조작성을 평가한다.
4. 다른 건물·AP 환경에서 다중 노드 계측과 잔차 보정의 일반화 가능성을 평가한다.

## 14. 평가 범위 밖의 선택 항목

- 연속 6DoF 기반 핸드헬드 Position 추정
- 배터리와 전력 관리
- STM32 단독 MQTT Client 구성

현재 시연은 Viewer의 텔레포트 이동을 사용하며 연속 6DoF 위치 추정을 요구하지 않는다. LCD Pin
Mapping과 표시 경로는 구현·실물 검증을 완료했고, 영상·자세·버튼 통합 상태의 300초 이상 안정
동작도 확인했다. 위 항목은 현재 시스템의 미완료 기능이 아니라 향후 확장 선택지다.

## 15. 코드 저장소에 유지할 문서

다음 문서는 실제 코드·배선·시험 절차와 직접 연결되므로 Embedded 저장소에 유지한다.

```text
README.md
rssi_esp32_to_stm32/README.md
rssi_esp32_to_stm32/docs/protocol.md
rssi_esp32_to_stm32/docs/hardware_wiring.md
rssi_esp32_to_stm32/docs/test_plan.md
rssi_esp32_to_stm32/stm32_receiver/README.md
```

공통 MQTT 규격과 파트 간 데이터 형식은 이 저장소에 중복 작성하지 않고 `RFVisualizer-Docs/INTERFACE.md`를 기준으로 한다.

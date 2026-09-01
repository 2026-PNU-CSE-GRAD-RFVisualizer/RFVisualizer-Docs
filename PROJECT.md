# RFVisualizer 프로젝트

## 1. 한 줄 목표

실제 실내 공간을 3차원으로 재구성하고, 여러 ESP32에서 측정한 Wi-Fi RSSI와 공간 구조를 반영한 전파 시뮬레이션 결과를 결합하여 3D 장면 위에 신호 분포를 시각화한다.

## 2. 문제 정의

기존 Wi-Fi 신호 분석은 평면도 위 2D 히트맵이나 수치 로그를 주로 사용한다. 이 방식은 벽, 문, 높이 차이, 가구, 반사체 등 실제 공간 구조와 신호 변화의 관계를 보여주기 어렵다.

이 프로젝트는 다음 세 문제를 함께 다룬다.

1. 여러 센서 노드에서 RSSI를 안정적으로 측정하고 전달한다.
2. 사진으로 실제 실내 공간을 재구성하고 전파 계산에 사용할 기하 구조를 만든다.
3. 측정값과 전파 시뮬레이션 결과를 사용자가 이해하기 쉬운 3D 화면으로 보여준다.

## 3. 최종 시스템 개념

### 3.1 실제 RSSI 측정 흐름

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
        │
        ├─ 논문·실험용 SQLite / JSONL / CSV Export
        └─ 졸업작품용 200 ms Frame / WebSocket
```

현재 임베디드 구현은 각 ESP32가 MQTT에 직접 접속하는 구조가 아니다. 원격 노드는 ESP-NOW로 Gateway에 보내고, STM32와 PC Bridge를 거쳐 MQTT에 발행한다.

### 3.2 공간 재구성과 전파 계산 흐름

```text
실내 사진
  ↓
COLMAP Camera Pose
  ↓
PGSR 학습
  ├─ Gaussian Scene ─────────────→ 실시간 화면용
  └─ Surface Mesh
          ↓
Proxy Mesh / Room Envelope / Metric Calibration
          ↓
주요 장애물 및 재질 설정
          ↓
Sionna RT
          ↓
Radio Map / Path / Coverage 결과
```

시각적 장면은 3D Gaussian Splatting으로 표현한다. 전파 경로와 가림 판정에는 명확한 표면 교차가 가능한 Triangle Mesh 또는 Proxy Scene을 사용한다.

### 3.3 최종 시연 화면 흐름

```text
Gaussian Scene + Radio Map + Camera Pose
        ↓
PC Viewer에서 800×480 화면 렌더링
        ↓
RFJF Frame 전송 (palette256+zlib 기본)
        ↓
ESP32-S3에서 디코딩
        ↓
480×800 LCD에 표시
```

핸드헬드 ESP32-S3는 3DGS 또는 Sionna RT를 직접 실행하지 않는 Thin Client로 설계한다. 장치 방향과 버튼 입력을 PC에 보내고, PC가 렌더링한 화면을 수신해 표시한다.

이 흐름은 최종 목표다. 영상 경로(Viewer→RFJF 송신→ESP32-S3→LCD)는 구현되어 2026-08-27에 실기기 종단 출력을 확인했고, 방향 입력 경로(핸드헬드→Backend→Viewer Camera)도 구현·자동 검증까지 마쳤다. 실제 ESP32-S3에서 방향·버튼을 UDP로 송신하는 연결과 300초 지속 성능 검증은 아직 남아 있다. 현재 상세 진행도는 `CURRENT_STATUS.md`를 따른다.

## 4. 두 가지 사용 경로

### 4.1 측정·논문 실험 경로

```text
실제 RSSI 수집
  ↓
장치별 Offset 보정
  ↓
Calibration 지점과 Test 지점 분리
  ↓
Graphics-ready CSV Export
  ↓
Raw Sionna RT / Plain IDW / Sionna RT + Residual IDW 비교
```

네트워크 저장소는 이 경로를 기본 활성 상태로 구현했다. 실험 데이터의 기준 저장소는 SQLite이며, 수신 원본은 JSONL에도 보존한다.

### 4.2 졸업작품 실시간 시연 경로

```text
고정 RSSI 노드 + 핸드헬드 방향/버튼
  ↓
Backend / PC Viewer
  ↓
Gaussian Scene + 2.5D Heatmap
  ↓
RFJF Streaming (palette256+zlib)
  ↓
ESP32-S3 LCD
```

현재 네트워크 저장소에는 200 ms 동기화와 WebSocket 인터페이스가 격리되어 있으나 기본 비활성이다. 핸드헬드 방향 반영, Viewer의 RF Volume 렌더링, RFJF 영상 송신·LCD 표시는 구현·실기기 검증까지 진행됐다. 실제 위치 추정 알고리즘과 실기기 방향/버튼 UDP 송신, 300초 지속 성능 검증은 아직 완료되지 않았다.

## 5. 파트별 책임

### 그래픽스

- 사진 기반 PGSR 장면 재구성
- Gaussian Scene과 Surface Mesh 생성
- 전파 계산용 닫힌 Room Envelope 생성
- 실제 미터 단위 좌표계 정렬
- Proxy 장애물 배치 및 재질 설정
- Sionna RT Scene과 Radio Map 생성
- 실제 RSSI와 시뮬레이션 결과 분석
- SIBR 기반 3D RF Volume Viewer와 RFJF 영상 출력(실기기 종단 확인)

### 임베디드

- ESP32 다중 RSSI 노드 펌웨어
- ESP-NOW 패킷 전송
- ESP32 Gateway의 수신·누락 집계·UART 전달
- STM32 UART 수신, Checksum 검증, 노드 상태 관리
- Serial-MQTT Bridge를 통한 MQTT 발행
- ESP32-S3 IMU·LCD 로컬 통합 실물 검증, 버튼·RFHC UDP 송신 통합은 진행 중

### 네트워크/백엔드

- MQTT Broker와 메시지 구독
- RSSI 페이로드 검증과 필드 정규화
- 패킷 손실, 노드 상태, 수집 지연 관리
- 논문 실험의 세션·노드 배치·장치 Offset 관리
- SQLite·JSONL 저장과 Graphics-ready CSV Export
- 향후 200 ms Frame 동기화와 WebSocket 전달
- 위치 추정 결과를 제공할 인터페이스 유지

## 6. 현재 확정된 설계 원칙

1. **실제 RSSI 측정은 유지한다.**  
   Sionna RT는 실제 측정을 대체하지 않고 공간 기하를 반영한 예측값을 제공한다.

2. **화면과 전파 계산의 표현을 분리한다.**  
   화면은 Gaussian Scene, 전파 계산과 가림 판정은 Mesh/Proxy Scene을 우선 사용한다.

3. **Sionna RT는 매 Frame 실행하지 않는다.**  
   장면, 송신기, 주파수, 재질이 고정된 동안 Radio Map을 사전 계산하고 Viewer가 읽는다.

4. **MVP의 RF 표현은 단일 높이의 2.5D Radio Map이다.**

5. **핸드헬드는 Thin Client다.**

6. **Camera Orientation은 지속 갱신, 이동은 물리 버튼 2개로 조작한다(2026-08-28 기획 변경).**  
   버튼식 Position Update·Recenter는 폐기했다. 대신 버튼 1은 텔레포트 이동(누르는 동안 조준,
   떼면 이동), 버튼 2는 Heatmap Z-height 프리셋 순환을 맡는다. 실제 Position 추정 알고리즘은
   여전히 미확정이며 이 두 버튼과 무관하다.

7. **파트 간 규격은 현재 동작 코드에 맞춘다.**

8. **좌표는 실험별로 정의한다.**  
   공통 단위는 meter이고 `+Z`는 위쪽이다. 원점과 수평축은 Scene/Experiment 설정에 명시한다.

## 7. 최소 완료 기준

### 측정·분석

- 실제 ESP32 3대 이상 동시 측정
- 고정 BSSID와 채널 사용
- 원시값과 필터링값 보존
- 장치별 Offset 계산
- Calibration/Test 분리
- 좌표와 `corrected_rssi`가 포함된 결과 Export
- 실제 RSSI와 RF 예측값의 정량 비교

### 시각화

- PGSR Gaussian Scene 렌더링
- 실제 미터 단위 Proxy Scene
- Sionna RT Radio Map 생성
- Heatmap을 3D 장면 좌표에 배치
- Mesh Depth를 이용한 가림 처리
- 800×480 화면 생성

### 최종 통합

- 방향 입력이 Viewer Camera에 반영
- 텔레포트 버튼(누르는 동안 조준, 떼면 이동)
- Height-cycle 버튼(Heatmap Z-height 프리셋 순환)
- RFJF Frame 전송
- ESP32-S3 LCD 출력
- End-to-End 지연과 Frame Drop 측정

## 8. 최소 범위에서 제외된 항목

- ESP32에서 3DGS 또는 Sionna RT 직접 실행
- 핸드헬드의 연속 6DoF 위치 추적
- IMU 적분만으로 이동 거리 계산
- 초기 단계의 완전 자동 Material Segmentation
- 초기 단계의 완전한 3D RF Volume Rendering
- Gaussian 자체를 이용한 RF Ray Tracing 구현

GaussianRT-RF는 관련 연구와 Future Work로 참고하지만 현재 구현 기반은 PGSR Mesh와 Sionna RT다.

## 9. 주요 용어

| 용어 | 의미 |
|---|---|
| RSSI | 수신 신호 세기 지표. 단위는 dBm |
| 3DGS | 3D Gaussian Splatting. 실시간 장면 렌더링 표현 |
| PGSR | 평면 기반 Gaussian 재구성 |
| Proxy Scene | RF 계산에 필요한 큰 구조만 단순화한 장면 |
| Room Envelope | 바닥·벽·천장이 공통 꼭짓점을 공유하는 닫힌 방 Mesh |
| Sionna RT | Mesh 기반 전파 Ray Tracing 도구 |
| Radio Map | 위치별 RSS 또는 Path Gain Grid |
| Calibration Point | 실제 측정값으로 보정에 사용하는 위치 |
| Test Point | 보정에 사용하지 않고 평가에만 사용하는 위치 |
| `corrected_rssi` | Filtered RSSI 중앙값에 장치별 Offset을 더한 값 |
| Thin Client | 무거운 계산 없이 입력·영상 표시만 담당하는 장치 |
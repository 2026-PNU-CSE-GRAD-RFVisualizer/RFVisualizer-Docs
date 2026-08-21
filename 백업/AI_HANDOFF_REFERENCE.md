# RFVisualizer AI 작업 전달 레퍼런스

- 기준일: **2026-08-11**
- 사용 대상: 그래픽스, 네트워크/백엔드, 임베디드, 논문·통합 담당자가 사용하는 AI
- 사람용 실행 요약: [TEAM_EXECUTION_SUMMARY.md](TEAM_EXECUTION_SUMMARY.md)

> 이 문서는 AI가 과거 4층 파일럿, 새 3층 최종 실험, 8월 논문 범위, 9월 졸업작품 범위를 섞지 않도록 하는 공통 기준이다.

## 1. AI에게 전달하는 방법

팀원은 AI에게 다음 네 가지를 함께 전달한다.

1. 이 문서 전체
2. 담당 코드 저장소 URL 또는 로컬 경로
3. 현재 Branch·Commit과 작업할 파일 범위
4. 이번 요청의 목표와 완료 조건

AI가 문서만 보고 구현 완료를 가정하지 않게 한다. 코드를 변경하기 전 현재 코드, 호출 경로, 테스트, 작업 트리 상태를 직접 확인하도록 지시한다.

## 2. 기준 자료의 우선순위

내용이 충돌하면 다음 순서로 판단한다.

1. 현재 동작하는 코드와 통과한 테스트
2. 이 문서의 최종 실험·마감 계약
3. [INTERFACE.md](INTERFACE.md)
4. [TEAM_EXECUTION_SUMMARY.md](TEAM_EXECUTION_SUMMARY.md)
5. [CURRENT_STATUS.md](CURRENT_STATUS.md)와 파트별 문서
6. 과거 보고서·초기 계획서

`CURRENT_STATUS.md`는 2026-08-04 기준이라 최근 JPEG Relay, LCD, BNO085 시험을 모두 반영하지 못한다. AI는 이를 최신 구현 상태로 단정하면 안 된다.

## 3. 프로젝트 공통 문맥

### 3.1 목표

- 실제 복도를 3D Gaussian Splatting으로 시각화한다.
- Proxy Mesh와 Sionna RT로 공간 구조를 반영한 RF 예측값을 만든다.
- ESP32 5대의 실제 RSSI와 예측값을 비교·보정한다.
- 최종적으로 PC가 렌더링한 800×480 화면을 ESP32-S3 LCD에 표시한다.

### 3.2 저장소

| 파트 | 저장소 |
|---|---|
| 그래픽스 | [RFVisualizer](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/RFVisualizer) |
| 네트워크/백엔드 | [Network-Backend-Article](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Network-Backend-Article) |
| 임베디드 | [Embedded](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Embedded) |
| 공통 문서 | [RFVisualizer-Docs](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/RFVisualizer-Docs) |

### 3.3 전체 데이터 흐름

```text
ESP32 RSSI Node 1~4
        │ ESP-NOW
        ▼
ESP32 Gateway + Local Node 5
        │ UART
        ▼
STM32 → Python Serial-MQTT Bridge
        │ MQTT
        ▼
Network Backend
        ├─ SQLite / JSONL / CSV: 논문 실험
        └─ JPEG·제어 Relay: 졸업작품

3층 영상 → COLMAP → PGSR → Proxy Mesh → Sionna RT
                                      │
                                      ▼
                    RF 분석 / Heatmap Viewer / JPEG
```

## 4. 변경하면 안 되는 최종 실험 계약

- 장소: PNU 3층 ㅁ자 복도
- 이전 4층 결과: 최종 검증이 아닌 Pilot Evaluation
- 장비: RSSI 센서 5대
- Calibration: 4대 고정, 회차당 30분 연속 측정
- Test: 1대 이동, 서로 겹치지 않는 10개 위치, 위치당 2분
- 안정화: 각 Test 기록 전 20초
- 장비 Offset: 본 측정 전후 5대를 같은 위치에서 각각 5분 측정
- 반복: `T1→T10`, `T10→T1` 두 회차
- 시간 비교: Test가 측정된 같은 2분 동안의 C1~C4 중앙값을 사용
- RX 높이: 1.2m, 동일한 방향·거치 방식
- AP: 위치·높이·BSSID·채널·출력을 고정
- 평가 단위: Raw Sample 수가 아니라 Test 위치별 중앙값
- 비교 방법: Raw Sionna RT, Plain IDW, Global Bias, Residual IDW
- 논문 내부 내용 동결: 2026-08-28
- 졸업작품 제출: 2026-09-30

좌표와 실제 AP 설치 위치는 현장 측량으로 확정한다. AI가 임의 좌표를 만들어 코드나 논문에 넣으면 안 된다.

## 5. 공통 데이터 계약

최종 Export에서 다음 의미의 값이 누락되면 안 된다. 실제 필드명은 기존 코드와 [INTERFACE.md](INTERFACE.md)를 먼저 확인하고, 불필요하게 새 Schema를 만들지 않는다.

| 정보 | 목적 |
|---|---|
| Experiment·Run ID | 서로 다른 회차와 장소 분리 |
| Node ID·Sequence | 장치 식별, 중복·누락 계산 |
| Node 측정 시각 | 같은 실험 시각의 Calibration/Test 정렬 |
| Server 수신 시각 | 수집 지연과 Late Arrival 계산 |
| Node `uptime_ms` | 장치 재부팅·Clock Mapping 확인 |
| Raw·Filtered RSSI | 필터 전후 비교와 재처리 |
| AP BSSID·Channel | 다른 AP 또는 채널 변경 탐지 |
| `x`, `y`, `z`, 역할 | Calibration/Test 및 Sionna 좌표 연결 |
| RX 높이·방향 | 안테나 조건 재현 |
| Error·Queue·Heap 상태 | 장시간 안정성 판단 |

### 시간 처리 원칙

- RF Window는 Server 수신 시각이 아니라 **Node 측정 시각**을 기준으로 만든다.
- Node에 RTC가 없으면 `uptime_ms`와 Gateway/Server Epoch의 대응 관계를 기록한다.
- Server 수신 시각은 덮어쓰지 않고 별도 보존한다.
- 이전 지연 p95 244ms보다 큰 Late-arrival grace가 필요하므로 초기값은 500ms로 두고 예비 측정으로 확인한다.
- Test 2분당 1Hz 기준 유효 표본이 100개 미만이면 해당 위치를 재측정 대상으로 표시한다.

## 6. 현재 확인된 상태와 금지할 주장

### 구현·기본 검증됨

- Graphics의 4층 PGSR·Proxy·Metric·Sionna·RF 분석 경로
- Network의 MQTT 수집, 세션, 저장, Export, QC
- Network의 독립 JPEG Relay
- Embedded의 RSSI Node·Gateway·STM32·Bridge 경로
- Embedded의 LCD 정적 이미지 시험과 BNO085 단독 시험

### 아직 최종 통합되지 않음

- 3층 Scene과 Radio Map
- Node 측정 시각 기준 End-to-End 저장·Window
- Graphics JPEG Producer와 실제 Viewer
- ESP32-S3 JPEG 수신·Decode·LCD 출력
- BNO085·버튼·영상의 통합 펌웨어
- 실제 30분 End-to-End 안정성 결과
- 자동 실내 위치추정

### AI가 하면 안 되는 것

- 4층 결과를 최종 정확도 검증으로 표현하지 않는다.
- Global Bias를 제외하고 Residual IDW만 우수하다고 주장하지 않는다.
- `paper_evidence_eligible=false`를 근거 없이 `true`로 바꾸지 않는다.
- Test의 120개 Raw Sample을 120개의 독립 공간 실험으로 계산하지 않는다.
- 수신 시각을 센서 측정 시각처럼 사용하지 않는다.
- 코드·실물 로그 없이 하드웨어 통합 완료를 주장하지 않는다.
- 3층 실측 좌표·재질·문 상태를 추정해서 채우지 않는다.
- 자동 위치추정을 임의로 추가하지 않는다. 기본 시연은 버튼식 위치 선택이다.
- 다른 파트의 공통 필드를 조용히 변경하지 않는다. 공통 변경은 `INTERFACE.md`와 소비자까지 함께 확인한다.

## 7. 그래픽스 담당자가 AI에 줄 기준

### 현재 상태

- 4층의 COLMAP·PGSR·Proxy Mesh·Metric Calibration·Sionna RT·RF 분석은 존재한다.
- 3층 장면 폴더와 설정은 아직 없다.
- SIBR Heatmap Viewer, Depth-only 가림, 800×480 Offscreen, JPEG Producer는 미완성이다.

### 8월 작업

- 기존 4층 파이프라인을 복제 가능한 기준으로 사용하되 4층 산출물을 덮어쓰지 않는다.
- `pnu_3f_corridor` 장면을 별도로 만든다.
- 시계·반시계·코너 상세 촬영에서 추출한 프레임으로 재구성한다.
- 등록률, Loop Closure, Metric Scale, Proxy Mesh QA를 기록한다.
- 고정된 AP와 C1~C4·T1~T10 좌표로 Sionna RT 결과를 만든다.
- 네 가지 방법의 동일 조건 결과표·Figure를 생성한다.

### 9월 작업

- 3층 Gaussian Scene과 Radio Map을 Viewer에서 함께 표시한다.
- Mesh Depth를 이용해 Heatmap 가림을 처리한다.
- 800×480 Offscreen Frame을 생성하고 기존 JPEG Relay가 받는 형식으로 전송한다.
- 위치는 자동 추정 대신 미리 정의된 위치 선택을 기본으로 한다.

### 완료 증거

- 재현 가능한 명령과 Scene 설정
- 재구성 QA 수치와 카메라 경로 확인
- RF 결과 CSV/JSON, 표, Figure
- 실제 Viewer 화면과 Relay가 수신한 JPEG

## 8. 네트워크/백엔드 담당자가 AI에 줄 기준

### 현재 상태

- MQTT Parser, Experiment/Session, SQLite/JSONL, CSV/JSON Export, QC가 있다.
- JPEG Relay는 별도 구현되어 있다.
- 실시간 Window는 현재 수신 시각 의존 여부를 코드에서 다시 확인해야 한다.
- PositionEstimate는 인터페이스만 있고 유효 위치를 반환하지 않는다.

### 8월 작업

- Payload의 Node 측정 시각 또는 `uptime_ms` Clock Mapping을 끝까지 보존한다.
- Window를 Node 측정 시각 기준으로 만들고 수신 시각은 지연 계산용으로 보존한다.
- Late-arrival grace 기본 500ms를 적용하고 예비 측정의 p95로 확인한다.
- Export 종료 전에 BSSID·Channel·좌표·Calibration/Test 역할 누락을 검출한다.
- Sequence Loss, 최대 공백, Queue Drop, 재연결을 30분 Run 단위로 산출한다.

### 9월 작업

- 기존 JPEG Relay를 Graphics Producer와 Embedded Consumer에 연결한다.
- 버튼식 위치 선택과 IMU 방향 입력의 전달 경로를 확정한다.
- Latest-frame-wins 정책 아래 지연·Frame Drop·재연결을 측정한다.
- 자동 위치추정은 졸업작품 필수 조건이 확인되기 전에는 구현하지 않는다.

### 완료 증거

- 측정 시각과 수신 시각이 함께 남은 실제 Export
- 누락 필드가 실패하는 최소 테스트
- 30분 수집 QC Report
- Graphics 송신부터 Embedded 수신까지의 Relay 로그

## 9. 임베디드 담당자가 AI에 줄 기준

### 현재 상태

- ESP32 RSSI Node → ESP-NOW Gateway → STM32 → Python Bridge 경로가 있다.
- Packet에는 `seq`, `uptime_ms`, BSSID, Raw/Filtered RSSI가 있다.
- Node의 실제 측정 시각이 Backend Epoch까지 완전하게 연결됐는지는 미확정이다.
- LCD와 BNO085는 독립 시험이며 통합 Handheld의 증거가 아니다.

### 8월 작업

- `seq`, `uptime_ms`, BSSID, Channel, RSSI, 오류 상태가 Bridge까지 손실 없이 전달되는지 확인한다.
- Node `uptime_ms`를 Gateway/Server Epoch와 연결할 Sync 정보를 제공한다.
- 5대 사전·사후 5분 Offset 측정과 C1~C4 30분 연속 로그를 확보한다.
- Packet Loss, 재부팅, 최대 공백, Queue Drop, Free Heap을 기록한다.
- BSSID·Channel·측정 주기 1Hz를 최종 실험 설정으로 고정한다.

### 9월 작업

- BNO085, 버튼, JPEG 수신·Decode, LCD 출력을 하나의 ESP32-S3 Firmware로 통합한다.
- PC가 보낸 800×480 Frame을 실제 480×800 LCD 방향에 맞춰 표시한다.
- 연결 끊김·재연결·잘못된 JPEG·Frame 유실에서 장치가 멈추지 않는지 확인한다.
- 30분 End-to-End 실행 중 Heap과 Frame Drop을 기록한다.

### 완료 증거

- 실제 5대 Timestamp·Sequence 로그
- 사전·사후 Offset 비교표
- 30분 동안의 Packet Loss·Heap·재연결 결과
- IMU·버튼·JPEG·LCD가 함께 동작하는 영상

## 10. 논문·통합 담당자가 AI에 줄 기준

### 8월 작업

- 4층 결과를 Pilot Evaluation으로 분리한다.
- 3층 데이터의 촬영 조건, 좌표계, AP·RX 높이, 환경 상태를 기록한다.
- 네 가지 방법을 같은 표에 싣고 최적 결과만 골라 제시하지 않는다.
- 위치별 결과, 반복 차이, RF 지표와 시스템 안정성 지표를 분리한다.
- 8월 28일 내용 동결 후 HWP/PDF를 직접 렌더링해 표·Figure·한글을 확인한다.

### 9월 작업

- 각 파트의 실제 실행 명령, 배선, 네트워크 설정, 복구 방법을 모은다.
- 실제 End-to-End 30분 시연과 장애 대응 결과를 기록한다.
- 현장 실패에 대비해 동결된 실행 파일, 정적 Frame, 시연 영상을 준비한다.
- 최종 보고서에서 구현, 실물 검증, 계획을 구분한다.

### 완료 증거

- 3층 Evidence Freeze와 산출물 목록
- 최종 HWP/PDF 시각 검수본
- 설치·실행·복구 절차
- 실제 시연 영상과 장시간 시험표

## 11. AI 요청 템플릿

아래 블록에서 대괄호만 채워 AI에게 전달한다.

```text
첨부한 AI_HANDOFF_REFERENCE.md를 공통 계약으로 사용해라.

담당 파트: [그래픽스 / 네트워크 / 임베디드 / 논문·통합]
저장소·Branch·Commit: [경로 또는 URL / branch / commit]
이번 목표: [관찰 가능한 결과 한 문장]
작업 범위: [담당 파일 또는 모듈]
완료 조건: [실행·로그·파일·화면 등]
반드시 유지할 것: [기존 인터페이스·실험 계약]
하지 말 것: [범위 밖 변경·추정값·최종 검증 과장]
검증 방법: [빌드·테스트·실물 실행 명령]

먼저 현재 코드와 테스트를 확인하고, 최소 변경으로 구현한 뒤 실제 사용 경로에서 검증해라.
다른 파트의 변경이 필요하면 임의로 수정하지 말고 필요한 필드·송수신자·영향을 먼저 보고해라.
```

## 12. AI 작업 결과 보고 형식

AI에게 다음 네 항목으로 결과를 받는다.

```text
변경: 실제 동작이 어떻게 달라졌는가
검증: 실행한 명령과 관찰한 결과
미검증: 장비·환경 부족으로 확인하지 못한 것
공통 영향: INTERFACE.md 또는 다른 파트가 바꿔야 할 것
```

파일 목록만 받거나 “동작할 것”이라는 설명만 받으면 완료로 처리하지 않는다.

## 13. 근거 문서

- [팀 실행 요약](TEAM_EXECUTION_SUMMARY.md)
- [프로젝트 구조](PROJECT.md)
- [파트 간 인터페이스](INTERFACE.md)
- [그래픽스 문서](graphics/GRAPHICS.md)
- [네트워크 문서](network/NETWORK.md)
- [임베디드 문서](embedded/EMBEDDED.md)
- [4층 실험 Evidence Freeze](archive/paper/kmms_day1_2_evidence_freeze.md)
- [논문 원고](archive/paper/manuscript_kmms.md)
- [기업 자문 의견서](<archive/자문의견서/16_(이게왜됨연구회)망고부스트코리아_서준오_자문의견서.pdf>)


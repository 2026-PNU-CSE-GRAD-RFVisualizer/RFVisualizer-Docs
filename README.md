# RFVisualizer Project Docs

이 저장소는 RFVisualizer 졸업작품의 **공통 기준 문서 저장소**다.

그래픽스, 임베디드, 네트워크/백엔드 저장소는 코드를 독립적으로 관리한다. 프로젝트 전체 목표, 현재 진행 상태, 파트 간 데이터 규격, 파트별 설계 기준은 이 저장소에서 함께 관리한다.

> 마지막 통합 검토일: 2026-08-24

현재 구현 상태는 `CURRENT_STATUS.md`, 파트 간 Wire/File 계약은 `INTERFACE.md`를 기준으로 한다.
로컬에서만 존재하거나 Git에 무시된 코드는 구현 흔적으로는 기록하되, 팀이 재현 가능한 완료 상태로 보지 않는다.

## 코드 저장소

| 파트 | 저장소 | 담당 범위 |
|---|---|---|
| 그래픽스 | [RFVisualizer](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/RFVisualizer) | PGSR 장면 재구성, Proxy Scene, Sionna RT, RF Field 분석, Viewer |
| 임베디드 | [Embedded](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Embedded) | ESP32 RSSI 노드, ESP32 Gateway, STM32 수신·전처리, PC MQTT Bridge, 핸드헬드 장치 |
| 네트워크/백엔드 | [Network-Backend-Article](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Network-Backend-Article) | MQTT 수집, 데이터 검증·저장, 실험 제어, CSV Export, 실시간 WebSocket 경로 |
| 공통 문서 | [RFVisualizer-Docs](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/RFVisualizer-Docs) | 프로젝트 공통 기준과 파트 간 인터페이스 |

## 먼저 읽을 문서

| 목적 | 문서 |
|---|---|
| 프로젝트 전체 목표와 구조 파악 | [PROJECT.md](PROJECT.md) |
| 지금 구현된 것과 남은 작업 확인 | [CURRENT_STATUS.md](CURRENT_STATUS.md) |
| 파트 사이 데이터 형식 확인 | [INTERFACE.md](INTERFACE.md) |
| 그래픽스 구현 파악 | [graphics/GRAPHICS.md](graphics/GRAPHICS.md) |
| 임베디드 구현 파악 | [embedded/EMBEDDED.md](embedded/EMBEDDED.md) |
| 네트워크/백엔드 구현 파악 | [network/NETWORK.md](network/NETWORK.md) |

AI 또는 새 팀원이 작업을 시작할 때는 다음 순서로 읽는다.

1. `PROJECT.md`
2. `CURRENT_STATUS.md`
3. `INTERFACE.md`
4. 자신이 담당하는 파트 문서
5. 해당 코드 저장소의 `README.md`, 테스트 문서, 소스 코드

## 문서 우선순위

문서나 코드의 설명이 서로 충돌하면 다음 순서로 판단한다.

1. **현재 동작하는 코드와 통과한 테스트**
2. `INTERFACE.md`
3. `CURRENT_STATUS.md`
4. 각 파트 문서
5. `PROJECT.md`
6. 각 코드 저장소의 운영용 README
7. 과거 구현 계획서, 중간보고서, 회의 정리, AI 작업 지시서
8. 착수보고서와 최초 기획안

착수보고서와 중간보고서는 특정 시점의 기록이다. 현재 데이터 규격이나 완료 상태를 결정하는 문서로 사용하지 않는다.

## 상태 표기

- **구현·검증 완료:** 코드가 있고 관련 테스트 또는 실제 실행 결과가 확인됨
- **구현 완료, 실물 검증 필요:** 코드와 빌드는 있으나 실제 장치·현장 조건에서 최종 검증되지 않음
- **인터페이스만 준비:** API나 자료구조만 있고 실제 알고리즘 또는 소비자가 없음
- **계획:** 구현 방향만 정해짐
- **미확정:** 실험이나 팀 합의가 필요함

계획을 완료된 기능처럼 서술하지 않는다.

## 문서 갱신 규칙

### 공통 규격 변경

MQTT Topic, JSON 필드, CSV 열, 좌표계, 단위, WebSocket Frame처럼 두 파트 이상에 영향을 주는 내용은 먼저 `INTERFACE.md`를 수정한다.

### 진행 상태 변경

구현 또는 실험이 끝났다면 `CURRENT_STATUS.md`의 해당 항목과 날짜를 수정한다.

### 파트 내부 변경

한 파트 내부의 구조, 하드웨어, 모듈, 실행 절차가 바뀌면 해당 파트 문서를 수정한다.

### 코드 저장소 문서

코드 저장소에는 다음 내용만 남긴다.

- 설치와 실행 방법
- 빌드와 테스트 방법
- 코드 디렉터리 설명
- 하드웨어 배선
- 해당 코드에만 필요한 내부 프로토콜

프로젝트 전체 목표, 다른 파트의 현재 상태, 공통 인터페이스를 코드 저장소에 중복해서 작성하지 않는다. 필요한 경우 이 저장소의 문서로 링크한다.

## 문서 변경 점검표

- [ ] 현재 코드와 일치하는가
- [ ] 구현 완료와 계획을 구분했는가
- [ ] 다른 파트의 인터페이스를 임의로 변경하지 않았는가
- [ ] 실험별 좌표계를 전역 좌표계처럼 쓰지 않았는가
- [ ] 과거 보고서의 내용을 현재 상태로 잘못 옮기지 않았는가
- [ ] 관련 코드 저장소 README의 중복 설명을 정리했는가

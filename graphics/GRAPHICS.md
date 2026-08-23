# Graphics 파트

- 코드 저장소: [RFVisualizer](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/RFVisualizer)
- 담당 범위: 실내 장면 재구성, RF 계산용 기하 구조 생성, Sionna RT, RF 분석, 최종 Viewer

## 1. 그래픽스 파트의 역할

그래픽스 파트는 실제 실내 공간을 사진으로 재구성하고, 다음 두 종류의 장면 표현을 만든다.

| 표현 | 목적 |
|---|---|
| PGSR Gaussian Scene | 실제 사진과 유사한 3D 화면을 실시간 렌더링 |
| Triangle Mesh / Proxy Scene | 전파 Ray Tracing과 Heatmap 가림 판정 |

현재 프로젝트는 PGSR로 Gaussian Scene과 Surface Mesh를 얻고, RF 계산에 필요한 큰 구조를 별도의 Proxy Scene으로 정리한 뒤 Sionna RT에 입력하는 방식을 사용한다.

## 2. 전체 처리 흐름

```text
실내 사진
  ↓
COLMAP Camera Pose 추정
  ↓
PGSR 학습
  ├─ Gaussian Scene
  ├─ Gaussian Point Cloud
  └─ Surface Mesh
          ↓
Proxy Mesh Editor
          ↓
Room Envelope
          ↓
Metric Calibration
          ↓
Proxy Placement Editor
          ↓
Sionna RT Scene
          ↓
Radio Map / Path / Coverage 결과
          ↓
실제 RSSI와 비교·보정
          ↓
향후 SIBR 기반 실시간 Viewer
```

## 3. PGSR 장면 재구성

### 입력

- 실제 실내 공간을 촬영한 RGB 이미지
- Camera Intrinsics
- Camera Extrinsics
- COLMAP에서 계산한 Camera Pose
- Sparse Point Cloud

### 출력

- Gaussian Point Cloud
- 새로운 시점의 Render 결과
- Depth 및 Normal 정보
- Surface Mesh

### PGSR을 사용하는 이유

일반 3D Gaussian Splatting은 새로운 시점의 화면을 빠르게 렌더링하는 데 적합하지만, 전파가 충돌할 명확한 표면을 직접 제공하지 않는다.

PGSR은 Gaussian을 장면의 평면 및 표면 방향에 맞추고 Surface Mesh를 생성할 수 있어 다음 두 목적을 함께 지원한다.

```text
PGSR Gaussian Scene → 사용자에게 보여줄 화면
PGSR Surface Mesh   → 전파 계산 및 가림 판정
```

### PGSR Mesh의 한계

자동 생성된 Mesh에는 다음 문제가 있을 수 있다.

- 촬영되지 않은 영역의 Hole
- Floating Geometry
- 벽과 바닥의 불규칙한 표면
- 불필요하게 많은 Triangle
- 뒤집힌 Normal
- 작은 조각
- 자동 Material 분류 부재

따라서 원본 Mesh를 전파 계산에 그대로 사용하지 않고, RF 계산에 필요한 큰 구조를 Proxy Geometry로 다시 구성한다.

## 4. Proxy Mesh Editor

주요 코드 경로:

```text
tools/proxy_mesh_editor/
```

### 4.1 Plane Candidate 추출

Point Cloud에서 넓은 평면 구조를 추출한다.

- RANSAC 기반 Plane 추출
- Connected Component 검사
- 면적과 Inlier 비율 검사
- Horizontal/Vertical Orientation 분류
- Floor, Ceiling, Wall 후보 생성

### 4.2 Wall Candidate 추출

벽 후보는 일반 평면 추출 후 남은 점에만 의존하지 않는다.

같은 전처리 원본에서 다음 과정을 별도로 수행한다.

1. Point Normal이 수직면에 가까운 점 선택
2. Wall 전용 RANSAC 실행
3. Connected Component와 면적 검사
4. Wall Candidate 생성

이 단계에서는 벽 후보 사이를 자동 병합하거나 방의 모서리를 맞추지 않는다.

### 4.3 Room Envelope 생성

사람이 Floor, Ceiling, Wall 후보를 선택하고 벽의 순서를 지정한다.

선택된 평면을 직접 연결하는 대신, 무한 평면의 교점을 계산하여 공통 모서리를 만든다.

```text
선택한 Floor Plane
선택한 Ceiling Plane
순서가 지정된 Wall Plane
        ↓
평면 교점 계산
        ↓
공통 Vertex 생성
        ↓
닫힌 Room Envelope OBJ
```

Room Envelope의 특징:

- 바닥·천장·벽이 공통 Vertex를 공유
- 틈이 없는 닫힌 구조
- 전파가 잘못된 틈으로 빠져나가는 문제 감소
- 원본 PGSR Mesh와 분리
- 원본 Point Cloud를 수정하지 않음

현재 범위에 포함되지 않는 항목:

- 외곽 벽 후보 자동 선택
- 문과 창문 구멍 자동 생성
- 복잡한 실내 구조의 완전 자동 복원

## 5. Metric Calibration

3D 재구성 결과는 실제 meter 단위가 아닌 임의 Scale을 사용할 수 있다.

Metric Calibration은 Room Envelope를 실제 meter 좌표계로 변환한다.

### 기준 좌표계

- 설정에서 선택한 바닥점: 원점
- 선택한 바닥 모서리의 수평 방향: `+X`
- 장면 Up Vector: `+Z`
- `+Y`: 오른손 좌표계에 따라 결정
- 단위: meter

### 출력

- 실제 meter 좌표의 Room Envelope
- 원본 좌표 → Metric 좌표 4×4 Matrix
- Metric 좌표 → 원본 좌표 4×4 Matrix
- Round-trip Error
- Calibration Metadata

원본 장면과 Room Envelope는 수정하지 않고, 별도의 Metric 사본을 만든다.

Scene별 측정값과 Transform은 다른 Scene에 재사용하지 않는다.

## 6. Sionna RT 연결 단계

### 6.1 Phase 2-A: Empty Room 연결

Metric Room Envelope를 Sionna RT가 읽을 수 있는 PLY와 Mitsuba XML로 변환했다.

검증한 항목:

- Sionna RT Scene Import
- ITU Concrete 근사 재질
- 2.4 GHz 설정
- LoS 경로
- 최대 2회 정반사
- 특정 높이의 Coverage Grid
- Path Gain 계산
- Coverage Point의 원본 PGSR 좌표 역변환

이 단계의 목적은 물리적으로 정확한 강의실 RSSI를 얻는 것이 아니라, 좌표·Scene·Solver 연결이 정상적으로 동작하는지 확인하는 것이다.

### 6.2 Phase 2-B: Proxy Obstacle

Room Envelope를 수정하지 않고 장애물을 별도의 Layer로 추가한다.

지원 형태:

- Box
- Thin Panel
- External Mesh

각 장애물은 다음 정보를 가진다.

- 위치
- 크기
- Yaw
- Material
- 활성화 여부
- 측정 근거
- Confidence

동일한 TX/RX, Solver, Seed, Coverage Grid에서 Empty Room과 Obstacle Variant를 비교했다.

Synthetic Blocker 시험에서 확인한 내용:

- 직접 LoS 경로 차단
- Coverage 결과 변화
- Baseline 반복 오차와 Obstacle 효과의 분리

이 결과는 실제 강의실 재질이나 RSSI 정확도를 입증하는 결과가 아니라, 장애물 Layer와 A/B 비교 파이프라인이 동작함을 확인한 결과다.

### 6.3 Phase 2-C: Proxy Placement Editor

주요 코드 경로:

```text
tools/proxy_placement_editor/
```

Editor에서 다음 Reference를 독립적으로 표시한다.

- PGSR Gaussian Point Cloud
- Metric Room Envelope
- PGSR Output Mesh

주요 기능:

- Layer별 표시 On/Off
- Box와 Thin Panel 배치
- 위치·Yaw·크기 수정
- Material 설정
- Confidence 설정
- Measurement Source 기록
- Floor/Ceiling/Wall Clearance 검사
- Collision Warning
- Undo/Redo
- Scenario 저장
- Sionna Scene용 설정 Export

대형 PGSR Output Mesh는 원본을 수정하지 않고, 표시 전용으로 단순화한 Cache를 사용한다.

Candidate의 기본 크기와 위치는 Placeholder다. 사람이 실제 측정값을 확인하고 명시적으로 활성화하기 전에는 최종 Sionna Scene에 포함하지 않는다.

## 7. 실제 RSSI 실험 연결

그래픽스 파트는 네트워크/백엔드 파트가 생성한 다음 파일을 입력으로 사용한다.

```text
experiments/<experiment_id>/
├── processed/calibration_points.csv
├── processed/test_points.csv
├── config/tx_rx.json
├── config/device_offsets.json
└── qc_report.json
```

기본 RSSI 입력값:

```text
corrected_rssi
```

`corrected_rssi`는 다음과 같이 계산된다.

```text
corrected_rssi = median_filtered + device_offset_db
```

### 비교할 방식

1. Raw Sionna RT
2. Plain IDW
3. Sionna RT + Residual IDW

### 실험 원칙

- Calibration Point만 보정에 사용
- Test Point는 평가에만 사용
- 동일한 TX 위치와 주파수 사용
- 동일한 좌표계와 단위 사용
- MAE와 RMSE로 평가
- Geometry Error와 Material/RSSI Error를 분리해서 분석

## 8. 최종 Viewer 계획

최종 Viewer의 우선 기반은 공식 SIBR Real-time Viewer Fork다.

```text
공식 SIBR Viewer
        ↓
기존 Gaussian Renderer와 Camera 유지
        ↓
프로젝트 전용 기능 추가
```

추가할 기능:

- PGSR Gaussian Scene 로딩
- Radio Map Texture 로딩
- OpenGL Heatmap Plane
- PGSR Mesh Depth-only Pass
- Depth 기반 Heatmap Composite
- Dear ImGui 상태 UI
- Offscreen 800×480 Framebuffer
- IMU Pose 수신
- 버튼식 Position Update
- JPEG Encoding
- TCP Streaming

### Render Pass

```text
Pass 1: Gaussian Scene Color
Pass 2: PGSR Mesh Depth
Pass 3: Heatmap Color + Depth
Pass 4: Depth 비교 및 Alpha Composite
Pass 5: UI
Pass 6: Offscreen 800×480 출력
```

### Thread 구조

```text
Pose Receiver Thread
Render Thread
Encoder Thread
Network Thread
```

Frame Queue는 1~2개로 제한하고, 처리하지 못한 오래된 Frame은 폐기한다.

## 9. 현재 구현 상태

### 구현·검증 완료

- PGSR Gaussian Scene 생성
- PGSR Surface Mesh 생성
- Plane/Wall Candidate 추출
- Room Envelope 생성
- Metric Calibration
- Sionna RT Phase 2-A
- Proxy Obstacle Phase 2-B
- Proxy Placement Editor Phase 2-C
- RF Experiment Framework
- Backend Export 입력 처리
- Sionna/IDW/Residual 비교
- 평가 결과 Export
- 3층 복도 Marker 배치와 Sionna `depth12` 실행

### 부분 완료·추가 검증 필요

- 8월 21일 실측 분석: 정방향 8 + 역방향 10 Segment 사용 가능
- 3층 Scene: 계획도 기반 좌표·Scale과 계단/문/책상/AP 형상 보정 필요
- 분석 결과: Residual IDW MAE 3.52 dB, 단 `paper_evidence_eligible=false`

### 아직 미구현

- SIBR Heatmap Viewer
- Mesh Depth-only Pass
- Offscreen 800×480 Rendering
- IMU Pose 수신
- Position Update
- JPEG Encoding
- Frame Streaming

## 10. 다음 작업

1. 3층 Scene의 계단·문·책상·AP 위치와 재질을 현장 기준으로 보정한다.
2. 누락된 정방향 Test 1·2와 Offset/BSSID를 최소 재측정한다.
3. Sionna/IDW/Residual 분석을 재실행하고 논문 근거 사용 가능 여부를 판정한다.
4. 결과가 확정된 뒤 SIBR Viewer와 JPEG producer를 구현한다.

## 11. 미확정 항목

- 최종 Scene의 형상·재질과 Sionna Solver 설정
- Residual IDW 결과를 논문 최종 방식으로 사용할지 여부
- 핸드헬드 Position 추정 알고리즘
- PGSR Mesh Depth와 Unbiased Depth 중 최종 사용 방식
- 여러 높이의 Radio Map 확장 여부
- JPEG Encoder와 GPU Readback 방식

## 12. 참고 연구

### 현재 구현 기반

- PGSR
- Sionna RT
- 3D Gaussian Splatting
- SIBR Real-time Viewer

### Future Work

GaussianRT-RF-NVS는 Gaussian 자체를 이용해 RF Ray Tracing을 수행하는 연구 방향이다.

현재 프로젝트의 핵심 구현 기반으로 사용하지 않으며, 다음 목적으로 참고한다.

- Mesh 전처리를 줄이는 장기 방향
- 시각 장면과 RF 장면의 통합 표현
- 최종 발표와 보고서의 Future Work

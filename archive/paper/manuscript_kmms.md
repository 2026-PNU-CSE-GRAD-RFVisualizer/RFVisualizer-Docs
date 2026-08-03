# RFVisualizer KMMS 정본 (v0 생성용)

**제목(안 1)**: 3D Gaussian Splatting 장면과 실측 RSSI를 결합한 실내 무선 신호 분포 추정

**영문 제목(안)**: Indoor Wireless Signal Field Estimation by Combining 3D Gaussian Splatting Scenes and Measured RSSI

## Abstract

Indoor wireless signals are affected not only by distance but also by walls, doors,
furniture, and material properties. This paper presents a pipeline that combines a
photorealistic 3D Gaussian Splatting scene, triangle-mesh-based radio propagation
simulation, and measured received signal strength indicator (RSSI) values in a common
metric coordinate system. PGSR provides the Gaussian scene and surface information,
while a closed proxy scene is constructed for Sionna RT. Five ESP32 devices collect
RSSI samples through an ESP-NOW gateway, an STM32 preprocessor, and an MQTT backend.
Device-dependent sensitivity is compensated using measurements obtained at a common
reference position. Three estimators are evaluated using the same calibration and test
split: raw Sionna RT, inverse distance weighting (IDW) using measurements only, and
residual IDW that interpolates the difference between measurements and Sionna RT.
Functional tests show that a synthetic blocker removes the configured line-of-sight
path and changes valid coverage cells by up to 8.426 dB. Corridor measurements are
reserved for the final quantitative comparison of the three estimators.
[학생: 복도 실험 확정 후 초록 마지막 문장을 결과 수치와 H3 판정으로 교체]

**Keywords**: 3D Gaussian Splatting, PGSR, Sionna RT, RSSI, Residual IDW, ESP32, Radio Map

## 1. 서론

무선 네트워크의 품질을 분석할 때 수신 신호 세기 지표(Received Signal Strength Indicator, RSSI)는 접근이 쉽고 위치별 비교가 가능하다는 장점이 있다. 그러나 RSSI는 송신기와 수신기 사이의 거리만으로 결정되지 않는다. 직접 경로의 차폐, 벽과 바닥의 반사, 문과 금속 구조물, 수신기의 높이와 방향, 사람의 이동과 주변 무선 간섭이 측정값에 영향을 준다. 따라서 단순 거리 모델이나 소수 측정점의 보간만으로는 공간 구조에 따른 급격한 변화를 설명하기 어렵다.

기존 RSSI 시각화는 주로 평면 도면 위에 측정값을 보간한 2차원 히트맵을 활용한다. 이러한 방식은 신호가 강하거나 약한 위치를 빠르게 파악하는 데 유용하지만, 실제 공간의 벽과 물체를 함께 보면서 신호 변화를 해석하기 어렵다. 실내 공간을 수작업 CAD 모델로 구축하는 방법도 가능하지만 모델 구축 비용이 높고 공간이 달라질 때마다 작업을 반복해야 한다.

3D Gaussian Splatting(3DGS)은 다중 시점 영상으로부터 사실적인 장면을 재구성하고 새로운 시점을 빠르게 렌더링할 수 있어[1], 실제 공간의 모습과 무선 신호 분포를 결합하는 시각적 기반으로 적합하다. 그러나 이를 전파 계산과 계측에 연결하려면 해결해야 할 문제가 남는다. 3DGS의 반투명 Gaussian 집합은 전파가 어느 표면에 충돌하고 반사되는지를 결정하는 명시적 경계를 직접 제공하지 않으므로, 시각 장면과 전파 계산 장면 사이의 표현 차이를 해소해야 한다. 또한 광선 추적은 공간 기하를 반영할 수 있지만 실제 재질의 유전율과 전도도, 송신 출력, 안테나 특성, 장치별 수신 감도를 정확히 알기 어렵고, 반대로 측정값만 보간하면 실측되지 않은 위치의 벽과 차폐 구조를 반영하기 어려우므로, 공간 구조를 반영한 시뮬레이션과 소수의 실측을 결합하는 방법이 필요하다.

본 연구의 목표는 사진 기반 3차원 장면, Sionna RT 전파 시뮬레이션과 다중 장치 RSSI 측정을 하나의 좌표 및 데이터 계약으로 연결하는 것이다. 구체적으로 (1) PGSR 장면에서 전파 계산용으로 닫힌 프록시 장면(Proxy Scene)을 구성하고 구조 변화가 Sionna RT 결과에 반영되는지, (2) 보정 지점의 실측 잔차를 통해 Sionna RT 결과를 보정할 때 측정값만 보간한 일반 IDW와 비교하여 시험 지점 오차가 어떻게 달라지는지, (3) 다섯 대의 RSSI 장치에서 장치 편차와 품질 정보가 포함된 재현 가능한 분석 입력을 도출할 수 있는지를 검증한다.

{{본 연구의 기여는 다음과 같다. 사진 기반 3DGS 장면에서 전파 계산이 가능한 닫힌 프록시 장면을 구성하고 두 표현을 동일한 미터 좌표로 정합하는 절차를 제시한다. 또한 시뮬레이션의 공간 분포와 소수 실측을 결합하는 잔차 IDW를 도입하고, 세 추정 방법을 동일한 보정/시험 분할에서 비교하는 평가 틀을 마련한다. 마지막으로 다섯 대의 저비용 장치로 장치 편차와 품질 정보가 포함된 재현 가능한 계측 데이터를 도출하는 데이터 계약을 설계하고 자동시험을 통해 검증한다.}}

{{본 연구의 정량 평가는 복도에서 수집하는 데이터를 대상으로 진행한다.}} 실시간 SIBR Viewer 합성, IMU 기반 시점 제어와 LCD 영상 전송은 전체 프로젝트의 후속 계층이며 본 논문의 정량 평가 범위에서 제외한다. 2장에서는 관련 연구를 정리하고, 3장에서는 문제 정의와 제안 방법을 설명한다. 4장에서는 기능 검증과 복도 실험 결과를 제시하며, 5장에서 결론을 맺는다.

## 2. 관련 연구

### 2.1 3D Gaussian Splatting과 PGSR

Kerbl 등은 장면을 위치, 공분산, 불투명도와 구면 조화 계수로 구성된 3차원 Gaussian 집합으로 표현하는 3DGS를 제안하였다[1]. 각 Gaussian을 화면 공간으로 투영하고 깊이 순서에 따라 알파 블렌딩함으로써 높은 시각 품질과 실시간에 가까운 렌더링 속도를 달성한다. 그러나 3DGS는 영상 복원 오차를 중심으로 최적화되므로 Gaussian이 실제 표면에 정확히 정렬된다는 보장이 없다.

PGSR은 Gaussian을 평면에 가까운 형태로 정렬하고 Gaussian 평면의 법선과 카메라 원점에서 평면까지의 거리를 통해 비편향 깊이(unbiased depth)를 계산하며, 단일 시점과 다중 시점의 기하 일관성 제약으로 표면 복원 품질을 높인다[2]. 이를 통해 하나의 학습 결과에서 새로운 시점 렌더링용 Gaussian과 후처리 가능한 표면 메시를 함께 얻을 수 있다. 다만 메시에도 촬영되지 않은 영역의 구멍, 부유 기하와 과도한 삼각형이 남을 수 있으므로, 본 연구에서는 큰 평면과 실측 구조를 활용한 닫힌 프록시 장면을 별도로 구성한다. {{한편 3DGS 계열의 표면 복원으로는 Gaussian을 2차원 원판으로 평탄화하는 2DGS[3]와 표면 정렬 정규화로 메시를 추출하는 SuGaR[4]도 제안되었으나, 렌더링용 Gaussian과 표면 메시를 하나의 학습 결과에서 함께 얻을 수 있다는 점에서 본 연구는 PGSR을 선정하였다.}}

### 2.2 광선 추적 기반 전파 시뮬레이션

Sionna RT는 Mitsuba 3와 Dr.Jit을 기반으로 송신기와 수신기 사이의 직접 및 다중 반사 경로를 계산하고 지점별 채널과 전파 지도(radio map)를 생성할 수 있다[5]. 삼각형 메시와 물체별 전파 재질(radio material)을 명시적으로 다룰 수 있어, 사진 기반으로 구성한 프록시 장면이 전파 계산에 미치는 영향을 시험하기에 적합하다. {{또한 미분 가능 광선 추적을 제공하므로 실측으로부터 전파 재질을 학습하는 보정도 시도되고 있다[6]. 본 연구는 재질 파라미터를 직접 학습하는 대신 시뮬레이션과 실측의 차이를 잔차로 보간하는 경량 보정을 택한다. WinProp, Wireless InSite 등 상용 전파 시뮬레이터도 있으나, 공개 소스이며 파이썬 파이프라인과 직접 결합할 수 있다는 점에서 Sionna RT를 활용한다.}}

### 2.3 측정 기반 RSSI 공간 추정

{{실측 RSSI로 공간의 신호 분포를 구성하는 연구는 실내 측위의 핑거프린팅 계열에서 출발하였다. RADAR[7]는 다수 기지국의 신호 세기를 사전 수집한 라디오 맵과 대조하여 실내 사용자를 측위한 초기 대표 연구이고, 국내에서도 RSSI 거리 추정의 성능 개선[8]과 딥러닝 기반 핑거프린팅 동향 정리[9] 등 관련 연구가 이어지고 있다. 이들 연구는 조밀한 사전 측정을 전제로 하는 반면, 본 연구는 소수의 보정 지점만으로 공간 분포를 추정하는 상황을 다룬다.}}

IDW(Inverse Distance Weighting)는 알려진 표본과 질의점 사이의 거리에 따라 가중치를 부여하는 결정론적 공간 보간 방법이다[10]. 구현이 단순하고 별도의 학습 데이터가 필요하지 않아 제한된 수의 RSSI 측정점에서 기준 방법으로 활용할 수 있다. 그러나 벽이나 코너가 있어도 유클리드 거리가 가까우면 큰 가중치를 부여하므로 실제 전파 경로의 차이를 직접 반영하지 못한다. {{가우시안 프로세스로 신호 세기의 공간 상관을 학습하는 접근[11]도 있으나 하이퍼파라미터 추정에 충분한 표본이 필요하므로, 보정 지점이 4개뿐인 본 연구 환경에서는 파라미터가 적고 결정론적인 IDW를 기준 방법으로 선정하였다.}} 본 연구의 잔차 IDW는 시뮬레이션이 제공하는 공간적 분포를 유지하면서 보정 지점에서 관측된 시뮬레이션 잔차만 보간한다.

### 2.4 다중 장치 계측과 메시지 전달

MQTT는 발행자와 구독자를 브로커로 분리하는 경량 메시징 프로토콜로 제한된 장치의 주기적 측정값 전달에 적합하다[12]. ESP-NOW는 ESP32 사이에서 연결 설정 부담을 줄인 직접 통신을 제공한다[13]. 본 연구에서는 네 대의 원격 ESP32가 ESP-NOW를 통해 게이트웨이로 측정값을 전송하고, 게이트웨이 자체를 다섯 번째 측정 노드로 활용한다.

### 2.5 {{신경 표현 기반 무선 채널 모델링}}

{{시각 분야의 신경 표현을 무선 채널에 적용하는 연구도 최근 활발하다. NeRF2[14]는 신호 측정으로 학습한 신경 방사장으로 임의 위치의 수신 신호를 예측하고, WiNeRT[15]는 신경망으로 무선 광선 추적을 근사하여 미분 가능한 채널 시뮬레이션을 제공하며, WRF-GS[16]는 3DGS 표현으로 무선 방사장을 재구성한다. 이들은 환경마다 상당한 양의 채널 측정 데이터를 학습에 요구하는 반면, 본 연구는 명시적 기하와 물리 기반 광선 추적을 유지한 채 소수의 실측만으로 지역 편향을 보정하므로, 측정 비용이 제한된 실무 환경을 겨냥한다는 점에서 방향이 다르다.}}

{{정리하면, 기존 연구는 사진 기반 장면 재구성, 물리 기반 전파 시뮬레이션, 측정 기반 공간 추정과 신경 표현 기반 채널 모델링을 각각 발전시켜 왔으나, 이들을 하나의 미터 좌표와 데이터 계약으로 연결하여 사실적 3차원 장면 위에서 시뮬레이션과 다중 장치 실측을 함께 검증한 사례는 확인되지 않는다. 본 연구는 이 통합 지점을 다룬다.}}

## 3. 제안 방법

### 3.1 문제 정의와 검증 가설

실내 공간을 나타내는 시각 장면을 {{V}}, 전파 계산용 표면 장면을 M이라 하자. {{V}}는 위치, 공분산, 색상과 불투명도를 가진 Gaussian 집합이고, M은 물체별 삼각형과 전파 재질의 집합이다. 장면 좌표를 미터 좌표로 옮기는 동차변환과 그 역변환은 서로 역의 관계를 이루어야 하며, 변환의 품질은 검증점 집합의 각 점을 정변환 후 역변환했을 때 원래 점과 벌어지는 거리의 최댓값(왕복 오차)으로 정의한다.

위치 x에서 Sionna RT가 계산한 선형 경로 이득을 G(x), 설정한 송신 전력을 P_TX dBm이라 하면, Sionna RT 원시 예측 R̂_S(x)는 송신 전력에 경로 이득의 데시벨 환산값 10 log_10 G(x)를 더해 얻는다. 실제 측정값 R(x)과의 차이는 기하, 재질, 안테나, 장치 특성과 환경 변화가 결합된 결과로 보고 식 (1)로 나타낸다.

<!-- 식 (1): R(x) = R̂_S(x) + b(x) + η(x) -->
EQ(1) R(x)`=`{hat R} _{S} (x)`+`b(x)`+`eta (x)

여기서 b(x)는 공간적으로 비교적 완만한 모델 편향이고 η(x)는 측정 노이즈와 일시적 환경 변화다. 시험 위치는 b(x)를 추정하거나 파라미터를 선정하는 데 사용하지 않는다. 또한 각 장치가 측정한 값에는 장치별 수신 감도 편차가 더해질 수 있으므로, 서로 다른 위치에 서로 다른 장치를 배치하기 전에 동일 위치에서 다섯 장치를 측정하여 편차를 추정해야 한다. 실측 표본은 실험에서 고정한 BSSID와 채널에 일치하고, RSSI가 허용 범위 안에 있으며, 오류 플래그와 타임스탬프 조건을 만족하고, 장치 ID와 지점 ID의 배치 관계가 기록된 경우에만 분석에 활용한다. 무효 표본은 분석에서 제외하지만 원본 데이터에서 삭제하지 않는다.

이러한 정의 위에서 본 연구는 다음 가설을 검증한다. H1: 송신기와 수신기 사이를 교차하는 프록시 차폐 구조를 추가하면 Sionna RT의 가시선(LoS) 경로와 전파 지도가 수치 재현성 오차보다 크게 변한다. H2: 공통 위치에서 계산한 장치별 편차 보정값은 다섯 ESP32의 수신 감도 차이를 줄인다. {{판정은 보정값 적용 후 공통 위치 중앙값의 장치 간 범위가 적용 전 범위보다 감소하는지로 한다.}} H3: 복도 시험 지점에서 Sionna RT + 잔차 IDW의 MAE와 RMSE가 일반 IDW보다 낮다. H3은 특정 방법의 우수성을 전제로 하지 않는다. 잔차 IDW가 더 높은 오차를 보이는 경우도 결과로 인정하고 기하, 재질과 보정 지점 배치의 한계와 함께 분석한다.

### 3.2 전체 파이프라인

[학생: 다섯 단계(장면 구축·계측·전파 계산·측정 보정·비교 평가)와 데이터 흐름을 나타내는 전체 아키텍처 그림 작도 — 메인 논문 Fig. 1의 역할·구도 참고]

제안 방법은 장면 구축, 계측, 전파 계산, 측정 보정, 비교 평가의 다섯 단계로 구성된다. 먼저 실내 공간의 다중 시점 영상으로부터 COLMAP을 활용해 카메라 자세를 추정하고, PGSR을 학습하여 시각화용 Gaussian 장면과 표면 메시를 생성한다. 생성된 장면을 실제 길이 단위의 미터 좌표계로 변환한 뒤, 표면 메시와 실측 구조를 참고하여 바닥, 천장, 벽과 주요 차폐물이 닫힌 표면을 이루는 전파 계산용 프록시 장면을 구성한다.

프록시 장면에는 실제 송신기 위치와 측정 지점을 동일한 미터 좌표로 배치한다. Sionna RT는 각 측정 지점의 지점 RSSI와 단일 높이 평면의 격자 RSSI를 계산한다. 지점 RSSI는 같은 위치의 실측값과 정량 비교하는 데 활용하고, 격자 RSSI는 공간 전체의 신호 분포를 생성하는 데 활용한다.

실측 RSSI는 다섯 대의 ESP32에서 수집한다. 네 원격 장치는 측정값을 게이트웨이로 전달하고, 게이트웨이는 자신의 측정값을 포함한 데이터를 STM32와 MQTT 백엔드를 거쳐 저장한다. 동일한 기준 위치의 동시 측정값으로 장치별 편차 보정값을 계산한 뒤, 이를 적용한 RSSI를 보정 데이터와 시험 데이터로 구분한다. 최종적으로 Sionna RT의 예측값만 사용하는 원시 예측, 보정 실측값을 직접 보간하는 일반 IDW, Sionna RT와 실측값 사이의 잔차를 보간하는 잔차 IDW를 동일한 시험 위치에서 비교한다. 구성 요소 사이의 핵심 데이터 계약은 Table 1과 같다.

**Table 1.** Key data contracts between system components.

| Data | Required fields | Role |
| --- | --- | --- |
| MQTT measurement | node_id, timestamp, rssi, seq, status | Node identification and validity check |
| Optional fields | rssi_raw, sample_count, ap_bssid, ap_channel | Raw value and AP condition preservation |
| Summary RSSI | point_id, point_role, node_id, x/y/z, corrected_rssi | IDW input and test evaluation |
| Sionna point value | point_id, x/y/z, sionna_rssi_dbm | Simulated prediction at the same point |
| Sionna grid value | row, column, x/y/z, sionna_rssi_dbm | 2D radio map generation |

### 3.3 PGSR 장면과 프록시 장면 생성

다중 시점 영상에서 COLMAP으로 카메라 자세와 희소 점군을 계산하고 PGSR을 학습하여 Gaussian 장면과 표면 메시를 도출한다. 원본 메시에서 바닥, 천장과 벽 후보를 검출한 후 실제 공간과 비교하여 주요 평면을 선정한다. 선정한 평면의 교차로 경계 꼭짓점을 계산하고 면이 동일 경계 꼭짓점을 공유하도록 닫힌 외피(envelope)를 만든다. 문, 벽, 주요 가구와 금속 구조는 독립 프록시 물체로 추가하며, 물체별 기하, 재질, 신뢰도와 측정 출처를 기록한다. Fig. 1은 개발용 장면에서 추출한 표면 메시를, Fig. 2는 평면 후보로 생성한 닫힌 프록시 외피를 나타낸다.

**Fig. 1.** Surface mesh extracted from the development scene using PGSR.

**Fig. 2.** Closed proxy envelope generated from planar candidates.

원본 Gaussian, PGSR 출력 메시와 프록시 장면은 별도 계층으로 보존한다. 프록시 배치 편집기는 미터 좌표에서 이동, 회전, 크기 조절, 바닥 스냅, 벽·천장 여유와 충돌 검사를 수행한다. 실측하지 않은 물체는 잠정(provisional) 상태로 유지하여 물리 검증 결과에 자동 포함되지 않도록 한다.

장면 좌표를 실제 단위로 변환하기 위해 서로 독립적인 길이 기준을 측정하고 균일 배율과 축 방향을 계산한다. 원점은 현장에서 재현할 수 있는 바닥 기준점으로 정하며, +Z는 위쪽, +X와 +Y는 도면의 축과 일치시킨다. 회전 행렬의 직교성과 행렬식, 정방향과 역방향 변환 오차, 검증점의 왕복 오차, 변환 전후 메시 위상, 송신기·수신기와 프록시 물체의 좌표계 ID를 검사한다. 복도 실험은 pnu_4f_corridor 좌표계, 미터 단위와 오른손 좌표계를 사용한다.

### 3.4 Sionna RT 지점 및 격자 계산

미터 단위의 프록시 장면을 객체별 PLY와 Mitsuba XML로 변환하고 물체별 Sionna 전파 재질을 연결한다. 기본 계산은 2.4 GHz 대역, 가시선과 최대 2회의 정반사를 사용한다. 지점 예측은 보정·시험 기준점 좌표에서 위치별 RSSI를 생성하고, 격자 예측은 측정 높이 평면에서 방법별 히트맵의 기준 격자를 생성한다. 두 출력은 동일한 송신 출력과 10 log_10 G 변환을 사용한다. 기준점과 요약 데이터의 같은 지점 ID가 좌표 허용오차 안에서 일치하지 않으면 분석을 중단한다. Fig. 3은 프록시 기하, 송신기와 수신기를 포함한 Sionna RT 기능 검증 장면을 나타낸다.

**Fig. 3.** Sionna RT functional-verification scene with proxy geometry, a transmitter, and receivers.

### 3.5 RSSI 계측과 장치 편차 보정

원격 ESP32 노드 1~4는 목표 AP의 RSSI를 200 ms 주기로 측정하고 최근 다섯 유효 표본의 이동평균을 계산한다. 약 1초마다 노드 ID, 시퀀스, 원시 RSSI, 필터링 RSSI, 표본 수와 오류 플래그를 CRC32가 포함된 ESP-NOW 패킷으로 게이트웨이에 전송한다. 게이트웨이는 원격 패킷을 검사하고 자체 RSSI를 로컬 노드 5로 추가한다. 게이트웨이는 측정값을 115200 bps UART로 STM32F107VCT6에 전달하고, STM32는 체크섬, 형식, 시퀀스와 타임아웃을 검사하며, PC의 직렬-MQTT 브리지가 JSON 스냅숏을 정규화하여 MQTT 토픽으로 발행한다. 백엔드는 원시 페이로드를 JSONL에 먼저 기록하고 활성 세션의 정규화된 표본을 SQLite에 저장한다. 무효 값도 삭제하지 않고 무효 표시와 제외 이유를 기록한다. Fig. 4는 ESP32 노드에서 분석 입력까지의 계측 경로를 나타낸다.

**Fig. 4.** RSSI measurement path from ESP32 nodes to the analysis input. [TODO: 계측 경로 다이어그램 작도 후 삽입]

장치별 편차 보정값은 공통 위치에서 얻은 다섯 장치의 유효 필터링 RSSI 중앙값의 중앙값에서 해당 장치의 중앙값을 뺀 값으로 정의하며, 보정된 측정값은 원 측정값에 이 보정값을 더해 얻는다. 편차 보정값은 동일한 한 세션에서 다섯 장치가 모두 최소 표본 수를 만족할 때만 계산한다. 특정 장치 하나가 아니라 전체 중앙값을 기준으로 사용하여 기준 장치의 이상치 영향을 줄인다.

### 3.6 실측값과 시뮬레이션의 결합

보정 위치를 x_i, 보정된 측정값을 R_i라 할 때 IDW 가중치는 식 (2)와 같다. 본 구현은 p = 2를 기본값으로 사용하며, 질의 위치가 보정 위치와 허용오차 안에서 일치하면 해당 위치의 표본을 직접 사용한다.

<!-- 식 (2): w_i(x) = 1 / (‖x − x_i‖_2^p + ε) -->
EQ(2) w _{i} (x)`=`{1} over {{VERT x-x _{i} VERT} _{2} ^{p}`+`epsilon}

비교하는 세 방법은 다음과 같다. Sionna RT 원시 예측은 별도의 실측 보정 없이 시뮬레이션 예측 R̂_S(x)를 그대로 사용하고, 일반 IDW는 보정 RSSI를 식 (2)의 가중치로 가중 평균한다. Sionna RT + 잔차 IDW는 보정 위치에서 잔차 e_i = R_i − R̂_S(x_i)를 계산하고 이를 보간하여 시뮬레이션 예측에 더한다(식 (3)).

<!-- 식 (3): R̂_hybrid(x) = R̂_S(x) + Σ_i w_i(x) e_i / Σ_i w_i(x) -->
EQ(3) {hat R} _{hybrid} (x)`=`{hat R} _{S} (x)`+`{SUM _{i} w _{i} (x) e _{i}} over {SUM _{i} w _{i} (x)}

세 방법은 같은 보정/시험 분할과 좌표를 사용한다. 시험 값은 IDW 지수, 재질 또는 송신 출력을 선정하는 데 사용하지 않는다.

### 3.7 평가지표

시험 위치의 실제값과 예측값 사이의 평균 절대 오차(MAE), 제곱근 평균 제곱 오차(RMSE), 평균 오차(ME)와 최대 절대 오차를 통상적인 정의에 따라 계산한다. 일반 IDW 대비 잔차 IDW의 MAE 개선율은 두 MAE의 차이를 일반 IDW의 MAE로 나눈 백분율로 정의하며, 값이 양수이면 잔차 IDW의 MAE가 더 낮다. 시험 위치가 6개뿐이므로 유의성 검정보다 위치별 오차와 공간 구조를 함께 해석한다.

## 4. 실험 및 결과

### 4.1 구현 환경

그래픽스, 백엔드와 임베디드는 서로 다른 실행 환경을 사용하되 파일 및 메시지 계약으로 연결한다. 주요 구현 환경은 Table 2와 같다.

**Table 2.** Implementation environment.

| Area | Environment and tools |
| --- | --- |
| Scene reconstruction | COLMAP, PGSR, CUDA training environment |
| Geometry processing | Python, Open3D 0.18/0.19, OBJ, PLY, JSON, YAML |
| Radio simulation | Python 3.10.20, Sionna RT 1.2.2, Mitsuba 3.8.0, Dr.Jit 1.3.1, NVIDIA RTX 4090 |
| Backend | Python, FastAPI, MQTT, SQLite, JSONL, optional PostgreSQL |
| ESP32 | ESP-IDF, ESP-NOW, FreeRTOS task |
| STM32 | STM32F107VCT6, CMake/Ninja, UART 115200 bps |

### 4.2 프록시 기하와 좌표 변환 검증

개발용 PGSR 장면에서 바닥, 천장과 네 벽을 선정하여 꼭짓점 8개, 삼각형 12개의 닫힌 외피를 생성하였다. 경계 모서리와 비다양체 모서리는 모두 0개였고 연결 요소는 1개였다. 변환 전후 삼각형 수와 위상 구조가 유지되었으며, 미터-장면-미터 지점 왕복 오차는 최대 약 1.99×10^-15 m로 나타났다. 이러한 결과는 개발용 입력에서 닫힌 전파 계산 기하와 가역적인 좌표 변환을 생성할 수 있음을 보여 준다. 다만 해당 장면은 복도 정확도 평가에 사용하지 않는다.

### 4.3 합성 차폐판 실험

H1을 검증하기 위해 동일한 송신기·수신기, 시드와 커버리지 격자를 가진 빈 기준 장면과 합성 차폐판 장면을 구성하였다. 차폐판은 0.15×2.5×2.0 m의 닫힌 상자로 만들고 송신기와 가시선 수신기 사이 선분을 교차하도록 배치하였다. 이는 실제 재질을 모사하기 위한 물체가 아니라 기하와 계산기 연결을 검증하기 위한 합성 물체다.

기준 장면을 같은 시드로 두 번 실행한 결과 공통 151개 셀의 커버리지 최대 반복 차이는 약 5.20×10^-6 dB로 나타났다. 차폐판 장면에서는 가시선 수신기의 직접 경로가 1개에서 0개로 감소했고 두 수신기의 전체 경로는 53개에서 35개로 감소하였다. Fig. 5는 두 장면 사이의 커버리지 차이를, Fig. 6은 차폐판 장면의 직접 및 반사 전파 경로를 나타내며, 정량 결과는 Table 3과 같다.

**Fig. 5.** Coverage difference between the empty baseline and the synthetic-blocker scene.

**Fig. 6.** Direct and reflected propagation paths in the synthetic-blocker scene.

**Table 3.** Synthetic blocker A/B test results.

| Item | Baseline | Blocker | Change / verdict |
| --- | --- | --- | --- |
| Direct paths of the LoS receiver | 1 | 0 | Removed by the blocker |
| Total paths of both receivers | 53 | 35 | -18 |
| Common valid coverage cells | 151 | 151 | Identical grid and mask |
| Mean coverage change | - | - | -1.012 dB |
| Maximum absolute change | - | - | 8.426 dB |
| Cells with abs. change > 1 dB | - | - | 48 |
| Baseline repeat max. error | - | - | 5.20e-6 dB |

모든 유효 셀의 변화가 반복 수치 오차보다 컸으며 설정한 가시선의 기하 교차와 직접 경로 제거가 함께 확인되었다. 따라서 H1은 합성 장면의 기능 검증 범위에서 지지된다. 이는 실제 복도 RSSI 예측 정확도나 합성 재질의 물리 정확도를 입증하는 결과는 아니다.

### 4.4 계측·분석 파이프라인 검증

백엔드는 MQTT 페이로드 구문 분석, 장치 상태, 실험과 세션, SQLite 저장, 장치 편차 보정, CSV 내보내기와 품질 검사를 모듈로 분리하였다. 전체 19개 시험이 통과했고, 그중 논문의 측정 절차를 재현하는 9개 시험은 독립 실행으로도 다시 통과하였다. 자동시험의 범위와 결과는 Table 4와 같다. 자동시험은 계산과 저장 로직의 일관성을 검증하지만 실제 무선 구간의 패킷 손실과 복도 현장 운용을 대신하지 않는다.

**Table 4.** Backend automated test coverage and results.

| Category | Verified behavior | Result |
| --- | --- | --- |
| Parsing | Field aliases, scaled RSSI, range and error flags | Pass |
| Device offset | Recovery of known device bias, corrected RSSI | Pass |
| Session | Fixed-offset accumulation, moving-test separation | Pass |
| Raw preservation | Invalid samples stored with exclusion reasons | Pass |
| Re-measurement | Discarded-session replacement without data loss | Pass |
| Export | Raw, summary, corrected and test CSV generation | Pass |
| Quality checks | Missing coordinates, mixed-BSSID detection | Pass |
| All tests | 19 tests | 19 passed |
| Paper-procedure subset | 9 of 19 tests | 9/9 passed |

임베디드 계측 경로에서 ESP32 노드/게이트웨이 펌웨어는 RSSI 측정, 이동평균, ESP-NOW 패킷, CRC와 시퀀스 관리를 구현하였다. STM32 모듈은 동적 메모리를 사용하지 않는 UART 구문 분석기, 노드 테이블과 MQTT JSON 생성기로 구성하였다. 이식 가능한 C 모듈의 호스트 시험에서 정상 라인 구문 분석, 잘못된 체크섬 거부, 두 노드의 상태 갱신과 JSON 스냅숏 생성을 확인하였다(Table 5).

**Table 5.** Verification scope of the embedded subsystem.

| Component | Verified | Not covered |
| --- | --- | --- |
| ESP32 node/gateway | Successful build records | Long-term operation of five nodes |
| STM32 parser | Host tests passed | UART noise, long-term operation |
| STM32 on device | Flash and execution records | Full end-to-end field performance |
| Serial-MQTT bridge | JSON normalization and publishing | Corridor BSSID/channel preservation |

분석 도구는 요약, Sionna 지점과 Sionna 격자 데이터를 입력으로 받아 세 방법을 계산한다. 보정 행만 IDW와 잔차 IDW의 입력으로 사용하고 시험 행은 지표 계산에만 사용한다. 합성 입력 시험에서는 보정 좌표 직접 반환, IDW 지수와 엡실론 검사, 보정 잔차만을 활용한 하이브리드 격자, 세 방법의 MAE/RMSE 계산과 동일 색상 범위 적용을 확인하였다. 합성 요약 데이터는 코드 연결 검증에만 활용하며 복도 실측 결과에는 포함하지 않는다.

### 4.5 복도 실험 설계

복도 실험은 H2와 H3을 검증하기 위한 실험이다. {{실험 공간은 직선 구간과 코너가 공존해 차폐에 따른 신호 변화가 뚜렷하고, 출입 통제가 쉬워 측정 조건을 일정하게 유지할 수 있는 복도로 선정하였다.}} 다섯 ESP32의 공통 위치 편차 보정값을 측정한 뒤 네 장치는 보정 위치에 고정하고 한 장치는 여섯 시험 위치를 순서대로 이동한다. 보정 값은 일반 IDW와 잔차 IDW의 입력으로 사용하고 시험 값은 세 방법의 평가에만 사용한다. 실험 구성은 Table 6과 같으며, 결과 표와 그림의 빈칸은 복도 측정 후 채우고 추정값을 넣지 않는다.

**Table 6.** Corridor experiment configuration.

| Item | Setting |
| --- | --- |
| Site | 4F corridor, Pusan National University |
| Coordinate system | pnu_4f_corridor, meters, right-handed |
| Transmitter | 1 dedicated AP |
| Receivers | 5 ESP32 devices |
| Fixed calibration receivers | 4 |
| Moving test receiver | 1 |
| Common height | 0.45 m |
| Device-offset measurement | 60 s at a common position |
| Test measurement | 30 s per position |
| Representative value | Median of valid filtered RSSI + device offset |
| Calibration / test points | 4 / 6 |
| Compared methods | Raw Sionna RT, plain IDW, residual IDW |

복도 도면의 왼쪽 아래 기준점을 원점으로 하고 도면 오른쪽을 +X, 위쪽을 +Y, 바닥 위쪽을 +Z로 정한다. 모든 송신기와 수신기는 z = 0.45 m에 둔다. Fig. 7은 복도의 좌표계와 측정 위치를 나타내며, 송신기·보정 지점과 시험 지점의 좌표는 각각 Table 7, Table 8과 같다.

**Fig. 7.** Coordinate system and measurement positions in the 4F corridor. [TODO: 원점·좌표축·송신기·보정 4지점·시험 6지점을 표시한 복도 도면 작도 후 삽입]

**Table 7.** Transmitter and calibration positions.

| Role | Point ID | X (m) | Y (m) | Z (m) | Device |
| --- | --- | --- | --- | --- | --- |
| Transmitter | tx-01 | 3.15 | 0.50 | 0.45 | [TODO: AP] |
| Calibration | cal-01 | 3.13 | 3.93 | 0.45 | [TODO] |
| Calibration | cal-02 | 8.08 | 3.93 | 0.45 | [TODO] |
| Calibration | cal-03 | 10.56 | 10.68 | 0.45 | [TODO] |
| Calibration | cal-04 | 8.69 | 15.63 | 0.45 | [TODO] |

**Table 8.** Test positions and measurement sessions.

| Order | Point ID | X (m) | Y (m) | Z (m) | Session |
| --- | --- | --- | --- | --- | --- |
| 1 | test-01 | 0.65 | 3.93 | 0.45 | [TODO] |
| 2 | test-02 | 5.60 | 3.93 | 0.45 | [TODO] |
| 3 | test-03 | 10.56 | 3.93 | 0.45 | [TODO] |
| 4 | test-04 | 6.92 | 11.20 | 0.45 | [TODO] |
| 5 | test-05 | 6.92 | 15.63 | 0.45 | [TODO] |
| 6 | test-06 | 10.56 | 15.63 | 0.45 | [TODO] |

실험 전에 AP의 SSID, BSSID, 채널과 송신 설정을 기록한다. 다섯 수신기는 같은 높이와 방향을 유지하고 고정 보정 수신기는 시험 측정이 끝날 때까지 이동하지 않는다. 먼저 다섯 장치를 공통 위치에 놓고 60초간 측정하여 장치 편차 보정값을 계산한다. 이후 네 장치를 보정 위치에 고정하고 이동 장치를 시험 위치에 순서대로 배치하여 각 30초간 측정한다. 표본 부족, 장치 이동, 장시간 차폐 또는 통신 단절이 있으면 현장에서 재측정한다. 실험 환경 기록 항목은 Table 9와 같고, Fig. 8은 현장 배치를 나타낸다.

**Table 9.** Field conditions of the corridor experiment.

| Item | Value |
| --- | --- |
| Experiment ID | pnu_4f_corridor_[TODO] |
| Date and time | [TODO] |
| AP model | [TODO] |
| SSID / BSSID | [TODO] |
| Channel / center frequency | [TODO] |
| TX power setting | [TODO] |
| Receiver orientation | [TODO] |
| Door / elevator states | [TODO] |
| Traffic and notes | [TODO] |
| Software / firmware versions | [TODO] |

**Fig. 8.** On-site arrangement of the transmitter and RSSI receivers. [TODO: 현장 사진 촬영 후 삽입]

### 4.6 복도 실험 결과

공통 위치 측정과 장치 편차 보정값은 Table 10과 같다. 보정 전 중앙값 범위는 [TODO: 값] dB였고 보정값 적용 후 범위는 [TODO: 값] dB로 나타났다. 가장 큰 절대 보정값은 [TODO: 값] dB로 [TODO: 노드 ID]에서 나타났다. 이에 따라 H2는 [TODO: 지지/부분 지지/기각]로 판단한다.

**Table 10.** Common-position measurements and device offsets.

| Node | Valid samples | Median (dBm) | Std. (dB) | Offset (dB) | Corrected median (dBm) |
| --- | --- | --- | --- | --- | --- |
| [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| [TODO] | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |

데이터 품질 검사 결과는 Table 11과 같다. 품질 기준을 만족하지 못한 세션은 [TODO: 없음 또는 세션 ID와 처리]이며 최종 분석에는 [TODO: 채택 기준]만 사용한다.

**Table 11.** Data quality checks.

| Check | Criterion | Result | Verdict |
| --- | --- | --- | --- |
| Device offsets | Computed for all 5 devices | [TODO] | [TODO] |
| Calibration points | 4 positions | [TODO] | [TODO] |
| Test points | 6 positions | [TODO] | [TODO] |
| Valid samples per test | Target 25-30, min. 18 | [TODO] | [TODO] |
| BSSID | Fixed to one | [TODO] | [TODO] |
| Channel | Fixed during the experiment | [TODO] | [TODO] |
| Missing coordinates | 0 | [TODO] | [TODO] |
| Raw preservation | JSONL and SQLite backups | [TODO] | [TODO] |
| CSV contract | Raw and summary checks passed | [TODO] | [TODO] |

시험 위치에서의 방법별 예측 오차는 Table 12와 같고, 위치별 실측값과 예측값은 Table 13과 같다. 일반 IDW 대비 잔차 IDW의 MAE 개선율은 [TODO: 값]%, RMSE 개선율은 [TODO: 값]%로 나타났다. 이에 따라 H3은 [TODO: 실측 결과에 따른 판정]로 판단한다.

**Table 12.** Prediction errors per method at the corridor test positions.

| Method | MAE (dB) | RMSE (dB) | ME (dB) | Max. abs. error (dB) |
| --- | --- | --- | --- | --- |
| Raw Sionna RT | [TODO] | [TODO] | [TODO] | [TODO] |
| Plain IDW | [TODO] | [TODO] | [TODO] | [TODO] |
| Sionna RT + residual IDW | [TODO] | [TODO] | [TODO] | [TODO] |

**Table 13.** Measured and predicted RSSI per test position.

| Point | Measured | Raw Sionna | Plain IDW | Residual IDW | Best method |
| --- | --- | --- | --- | --- | --- |
| test-01 | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| test-02 | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| test-03 | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| test-04 | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| test-05 | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |
| test-06 | [TODO] | [TODO] | [TODO] | [TODO] | [TODO] |

**Fig. 9.** Measured RSSI versus predicted values at the corridor test positions. [TODO: y=x 기준선 산점도 작성 후 삽입]

**Fig. 10.** Corridor RSSI fields estimated by the three methods. [TODO: 동일 색상 범위의 방법별 지도 작성 후 삽입]

Sionna RT 원시 예측의 MAE와 RMSE는 각각 [TODO: 값] dB와 [TODO: 값] dB로 나타났다. [TODO: 평균 오차 기준 과대/과소 추정 서술]. 이는 [TODO: 송신 출력·재질·기하 관련 원인]과 관련된 것으로 해석한다. 일반 IDW의 MAE와 RMSE는 각각 [TODO: 값] dB와 [TODO: 값] dB로 나타났다. 보정 지점과 가까운 [TODO: 지점 ID]에서는 [TODO: 관찰]한 반면, 벽 또는 코너를 사이에 둔 [TODO: 지점 ID]에서는 [TODO: 관찰]하였다. 이는 IDW가 유클리드 거리를 사용하고 차폐 구조를 직접 반영하지 않는 특성과 관련된다. 잔차 IDW의 MAE와 RMSE는 각각 [TODO: 값] dB와 [TODO: 값] dB로 나타났다. 일반 IDW와 비교하여 [TODO: 개선/악화]되었으며 가장 큰 차이는 [TODO: 지점과 오차 차이]에서 나타났다. Sionna RT의 공간적 분포가 실제 복도 구조와 일치한 영역과 기하 또는 재질 오차가 큰 영역을 나누어 해석한다.

### 4.7 고찰 및 한계

본 연구에서는 시각화와 전파 계산을 하나의 표현에 강제로 통합하지 않고 Gaussian과 메시의 역할을 분리하였다. 동일 장면을 두 번 관리해야 한다는 비용이 있지만 기존 3DGS 렌더러와 검증된 삼각형 기반 전파 계산기를 각각 활용할 수 있다. 합성 차폐판 시험에서 직접 경로와 커버리지가 수치 재현성 오차보다 크게 바뀐 결과는 프록시 계층이 실제 전파 계산에 참여함을 보여 준다. 다만 합성 장면에서 변화가 발생했다는 사실과 실제 환경의 RSSI를 정확히 예측한다는 주장은 구분해야 한다.

Sionna RT 원시 예측은 공간 기하를 사용하지만 실제 재질과 장치의 불확실성에 민감하고, 일반 IDW는 실측값을 직접 사용하지만 벽과 코너를 고려하지 않는다. 잔차 IDW는 Sionna RT의 공간 분포 위에 실측된 지역 편향을 더한다. 복도 결과가 오차 감소를 보이면 제한된 측정점이 시뮬레이션의 지역 편향을 보완했음을 의미한다. 개선되지 않으면 시뮬레이션의 공간적 형태가 실제 환경과 충분히 일치하지 않거나 보정 지점이 잔차장을 대표하지 못한 것으로 해석할 수 있다.

다중 장치 실험에서는 알고리즘뿐 아니라 측정 조건의 통제가 결과의 신뢰도를 결정한다. 장치 편차 보정값, BSSID, 채널, 지점 배치와 무효 사유를 원본과 함께 보존해야 대표값 계산 방법이 바뀌어도 다시 분석할 수 있다. 자동시험은 데이터 처리의 결정론적 부분을 검증하지만 실제 ESP-NOW 충돌, UART 잡음, 브로커 단절과 장시간 안정성을 직접 측정하지 않는다.

본 연구의 주요 한계는 시험 위치가 6개이고 모든 측정 높이가 0.45 m라는 점, 보정과 시험의 관측 시간이 다르다는 점, 문과 엘리베이터 및 사람 이동을 완전히 통제할 수 없다는 점, Sionna 재질이 실제 복도 재질의 전자기 측정값이 아니라는 점이다. 또한 ESP32의 RSSI는 전문 채널 사운더를 대체하지 않으며, 단일 날짜 측정으로는 시간대와 날짜 변화의 재현성을 평가할 수 없다. 본 논문의 시각화 계층은 전파 분포 파일 생성까지를 다루고 SIBR 실시간 합성의 프레임률과 지연은 평가하지 않는다.

## 5. 결론 및 향후 연구

본 연구에서는 사진 기반으로 재구성한 실내 3D Gaussian Splatting 장면, 삼각형 메시 기반 Sionna RT 전파 시뮬레이션과 다중 ESP32 RSSI 측정을 연결하는 무선 신호 분포 추정 파이프라인을 제안하였다. 시각화용 Gaussian과 전파 계산용 프록시 메시를 분리하고 미터 변환과 공통 기준점을 통해 정합하였다. 실측 RSSI는 ESP32, ESP-NOW 게이트웨이, STM32와 MQTT 백엔드를 통해 수집하고 공통 위치 측정으로 장치별 편차를 보정하였다.

개발용 장면의 기능 검증에서 합성 차폐판은 설정한 가시선을 제거하고 공통 유효 커버리지 셀에서 최대 8.426 dB의 변화를 발생시켰다. 기준 장면의 반복 변화가 약 5.20×10^-6 dB였던 것과 비교하면 기하 변경이 전파 계산 결과에 반영되었음을 확인할 수 있다. 백엔드의 19개 시험과 STM32 호스트 구문 분석 시험도 통과하여 장치 측정값을 보존하고 분석 입력으로 변환하는 경로를 검증하였다. 복도 실험에서 Sionna RT 원시 예측, 일반 IDW와 잔차 IDW의 MAE는 각각 [TODO: 값] dB였으며 RMSE는 각각 [TODO: 값] dB로 나타났다. [TODO: 핵심 결과와 H2·H3 판정 요약].

본 연구의 결과는 제한된 수의 복도 시험 위치와 단일 높이에서 진행한 예비 검증이다. 따라서 특정 결합 방법의 일반적인 우수성을 주장하기보다, 사진 기반 장면의 기하, 전파 광선 추적과 실제 RSSI를 동일 좌표에서 비교할 수 있는 재현 가능한 기반을 마련했다는 데 의미가 있다. 향후 연구로는 다음을 계획한다. 복도 측정을 다른 날짜와 높이에서 반복하고 보정 위치 수와 배치의 민감도를 비교한다. 또한 기하와 좌표를 먼저 검증한 뒤 전역 편차, 송신 출력 또는 소수의 재질 파라미터를 보정하는 방법을 검토하며, 시각화 계층에서는 SIBR Viewer에 단일 높이 전파 지도를 합성하고 PGSR 메시 깊이를 활용해 벽 뒤 히트맵을 가리는 방법을 평가한다.

## REFERENCE

[1] B. Kerbl, G. Kopanas, T. Leimkühler, and G. Drettakis, "3D Gaussian Splatting for Real-Time Radiance Field Rendering," *ACM Transactions on Graphics*, Vol. 42, No. 4, 2023.
[2] D. Chen, H. Li, W. Ye, Y. Wang, W. Xie, S. Zhai, et al., "PGSR: Planar-Based Gaussian Splatting for Efficient and High-Fidelity Surface Reconstruction," *arXiv Preprint*, arXiv:2406.06521, 2024.
[3] B. Huang, Z. Yu, A. Chen, A. Geiger, and S. Gao, "2D Gaussian Splatting for Geometrically Accurate Radiance Fields," *ACM SIGGRAPH 2024 Conference Papers*, 2024.
[4] A. Guedon and V. Lepetit, "SuGaR: Surface-Aligned Gaussian Splatting for Efficient 3D Mesh Reconstruction and High-Quality Mesh Rendering," *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition*, pp. 5354-5363, 2024.
[5] F. Ait Aoudia, J. Hoydis, M. Nimier-David, S. Cammerer, and A. Keller, "Sionna RT: Technical Report," *arXiv Preprint*, arXiv:2504.21719, 2025.
[6] J. Hoydis, F. Ait Aoudia, S. Cammerer, M. Nimier-David, N. Binder, G. Marcus, et al., "Sionna RT: Differentiable Ray Tracing for Radio Propagation Modeling," *arXiv Preprint*, arXiv:2303.11103, 2023.
[7] P. Bahl and V. N. Padmanabhan, "RADAR: An In-Building RF-Based User Location and Tracking System," *Proceedings of IEEE INFOCOM*, pp. 775-784, 2000.
[8] J.-H. Park, J.-G. Lee, and S.-C. Kim, "Performance Improvement Algorithm for Wireless Localization Based on RSSI at Indoor Environment," *The Journal of Korean Institute of Communications and Information Sciences*, Vol. 36, No. 4C, pp. 254-264, 2011.
[9] H.-M. Noh, Y. Oh, N. Lee, and W. Shin, "A Survey of Deep Learning-Assisted Indoor Localization with Wi-Fi Fingerprinting: Current Status and Research Challenges," *The Journal of Korean Institute of Communications and Information Sciences*, Vol. 46, No. 5, pp. 848-862, 2021, DOI: 10.7840/kics.2021.46.5.848.
[10] D. Shepard, "A Two-Dimensional Interpolation Function for Irregularly-Spaced Data," *Proceedings of the 23rd ACM National Conference*, pp. 517-524, 1968.
[11] B. Ferris, D. Hahnel, and D. Fox, "Gaussian Processes for Signal Strength-Based Location Estimation," *Proceedings of Robotics: Science and Systems*, 2006.
[12] MQTT Specification(2026). https://mqtt.org/mqtt-specification/ (accessed July 28, 2026).
[13] ESP-NOW SDK: ESP32 API Reference(2026). https://docs.espressif.com/projects/esp-now/en/latest/esp32/api-reference/index.html (accessed July 28, 2026).
[14] X. Zhao, Z. An, Q. Pan, and L. Yang, "NeRF2: Neural Radio-Frequency Radiance Fields," *Proceedings of the 29th Annual International Conference on Mobile Computing and Networking*, 2023.
[15] T. Orekondy, P. Kumar, S. Kadambi, H. Ye, J. Soriaga, and A. Behboodi, "WiNeRT: Towards Neural Ray Tracing for Wireless Channel Modelling and Differentiable Simulations," *Proceedings of the International Conference on Learning Representations*, 2023.
[16] C. Wen, J. Tong, Y. Hu, Z. Lin, and J. Zhang, "WRF-GS: Wireless Radiation Field Reconstruction with 3D Gaussian Splatting," *Proceedings of IEEE INFOCOM*, 2025.

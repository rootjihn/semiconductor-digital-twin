# Throughline Dashboard Redesign Research References

## 조사 목적

Throughline 메인 그래프 화면을 `로봇/설비/서버/디지털 트윈/데이터`가 한 장면 안에서 읽히는 현대적 관제 UI로 재설계하기 위한 레퍼런스 조사다.

## 현재 전제 재확인

- 실제 프론트 구현 경로: `WebSocket/`
- 기존 React는 참고용이고 새 구현은 Vue 기반
- 사용자가 싫어하는 것: 누운 3D 바닥판, 요소 겹침, 사각 박스 남발, 임시 패치 느낌
- 사용자가 원하는 것: 넓고 명확한 배치, 절제된 글래스/투명 표현, 마우스 인터랙션/모션, Vue Router 기반 페이지 구조, Chart.js는 일부 지표에만 제한적으로 사용

## 검색/수집 메모

- `web_search`는 Tavily 432 오류로 실패
- `hsearch backend-status`는 현재 프로필 경로 문제로 바로 사용 불가
- 그래서 이번 조사는 다음 우회 조합으로 수행했다.
  - DuckDuckGo HTML 결과 직접 조회
  - 브라우저로 Reddit/Behance 렌더링 확인
  - 공개 문서/제품 페이지 HTML 직접 파싱
- 즉, 아래 레퍼런스는 검색 백엔드 장애 상황에서도 재현 가능한 URL 중심 목록이다.

## 레퍼런스 목록

### 1) Reddit / Vue analytics 라이브러리 토론
- URL: https://www.reddit.com/r/vuejs/comments/1adylyp/what_vuebased_libs_are_people_using_for/
- 분류: 커뮤니티 / 개발자 토론
- 배운 점:
  - 실사용자 댓글에서 `ApexCharts는 느리고 무겁다`, `Chart.js는 너무 high-level이라 자유도가 부족하다`, `Apache ECharts는 만족도가 높다`는 식의 trade-off가 반복됐다.
  - 즉, 대시보드 차트는 "많이 붙이는 것"보다 "적은 수를 목적에 맞게 쓰는 것"이 중요하다.
- Throughline 적용:
  - 메인 화면은 차트 중심이 아니라 공정/로봇 상태 흐름 중심으로 두고, 차트는 KPI 카드/보조 패널로 제한한다.
  - 복잡한 네트워크/관계 표현은 일반 차트보다 SVG/커스텀 그래픽 쪽이 낫다.
- 피해야 할 점:
  - 메인 히어로 화면을 차트 라이브러리 위젯 모음처럼 만드는 것
  - Chart.js를 모든 시각 요소에 남용하는 것

### 2) Reddit / Vue graph libraries 토론
- URL: https://www.reddit.com/r/vuejs/comments/v6yeoa/graph_libraries/
- 분류: 커뮤니티 / 개발자 토론
- 배운 점:
  - `ApexCharts는 쉽고 차트 종류가 많다`는 의견과 함께, `bundle size`, `vue-chart-js는 데이터 포맷팅이 번거롭다`, `Highcharts는 강력하지만 유료` 같은 현실적인 피드백이 같이 나왔다.
- Throughline 적용:
  - 메인 그래프 영역은 차트 라이브러리 의존보다 SVG + Vue 컴포넌트 조합이 유지보수와 표현력 모두에서 유리하다.
  - 상용 차트처럼 "예쁘지만 비싼 범용 프레임"보다, 필요한 상호작용만 직접 설계하는 편이 적합하다.
- 피해야 할 점:
  - 번들 크기와 제약을 무시하고 범용 라이브러리를 메인 장면에 덕지덕지 붙이는 것

### 3) Reddit / Best visualization libraries 토론
- URL: https://www.reddit.com/r/vuejs/comments/17m8omk/best_visualization_libraries/
- 분류: 커뮤니티 / 개발자 토론
- 배운 점:
  - `Apache ECharts는 매우 강력하다`, `D3는 유연하지만 직접 reactive하게 붙여야 한다`, `Highcharts는 좋지만 가격 장벽이 있다`는 의견이 나왔다.
  - "복잡한 sankey/관계 그래프는 아무 라이브러리나 가져다 붙이는 것보다 구현자가 제어 가능한 구조가 필요하다"는 시사점이 있다.
- Throughline 적용:
  - 메인 화면은 라이브 chart보다 상태 노드 + 연결선 + hover/selection 상호작용을 직접 제어하는 구조로 설계한다.
  - 복잡한 시각화가 필요하면 보조 페이지로 분리한다.
- 피해야 할 점:
  - 메인 화면 하나에 복잡한 시각화 요구를 모두 집어넣는 것

### 4) GSAP Forum / Objects interact with mouse move
- URL: https://gsap.com/community/forums/topic/40134-objects-interact-with-mouse-move/
- 분류: 커뮤니티 / 개발자 토론
- 배운 점:
  - GSAP 포럼 답변에서 Hello Monday 류의 마우스 반응 인터랙션은 단순 border-radius가 아니라 `masking` 같은 기법으로 접근하는 게 맞다고 짚었다.
  - 즉, "고급스러워 보이는 상호작용"은 CSS 한두 줄이 아니라 레이어/마스킹/좌표 설계가 핵심이다.
- Throughline 적용:
  - 메인 그래프 화면의 마우스 반응은 카드 전체 흔들기보다, 연결선 glow, 선택 노드 강조, 포인터 기반 미세 tilt 정도로 제한한다.
  - 복잡한 reveal 효과가 필요하면 SVG mask/clip-path 계열로 설계한다.
- 피해야 할 점:
  - 눈에 띄는 효과를 위해 과한 왜곡/변형을 넣는 것
  - 산업 관제 화면인데 포트폴리오 랜딩페이지처럼 과도한 연출을 넣는 것

### 5) Building a Custom Grid UI for Robotics Control
- URL: https://bylazar.com/blog/grid-ui-ftcontrol-panels/
- 분류: 개발 블로그 / 로봇 UI 사례
- 배운 점:
  - 글에서 기존 로봇 대시보드를 `button-heavy nightmare`에서 `fluid, grid-based playground`로 바꿨다고 설명한다.
  - 핵심은 drag, resize, customize가 가능한 `grid-based` 정보 구조였다.
- Throughline 적용:
  - 현재 Throughline도 박스 나열보다 `영역 우선순위가 보이는 레이아웃`으로 가야 한다.
  - 라우터 기반 하위 페이지에서는 카드 재배치/패널 구성을 확장 포인트로 고려할 수 있다.
- 피해야 할 점:
  - 버튼과 상태 박스를 수평/수직으로만 잔뜩 쌓는 운영툴 느낌

### 6) How to Build Dashboards with Chart.js: A Practical Guide
- URL: https://embeddable.com/blog/how-to-build-dashboards-with-chart-js
- 분류: 개발 문서 / Chart.js
- 배운 점:
  - Chart.js는 대시보드 전체 프레임이 아니라 `specific chart component`로 쓰는 쪽이 자연스럽다.
  - 차트는 KPI, trend, 비교 같은 목적이 분명할 때만 가치가 있다.
- Throughline 적용:
  - Chart.js는 상단 KPI 미니차트, throughput 추이, cycle time 추이 등 제한된 지표에만 사용한다.
  - 메인 공정도/장비 관계도는 Chart.js가 아니라 SVG/컴포넌트 기반으로 유지한다.
- 피해야 할 점:
  - 메인 시각 구조를 차트 라이브러리 문법에 끼워 맞추는 것

### 7) Dashboard Design: best practices and examples
- URL: https://www.justinmind.com/ui-design/dashboard-design-best-practices-ux
- 분류: UX 문서
- 배운 점:
  - 대시보드는 가장 중요한 정보를 먼저 보여줘야 하고, hierarchy와 clutter control이 중요하다는 고전적인 원칙을 다시 확인해준다.
  - 운영 화면일수록 "보이는 정보량"보다 "즉시 읽히는 구조"가 중요하다.
- Throughline 적용:
  - 첫 화면은 전체 시스템 상태, 로봇/공정 위치, 경고 건수, 연결 상태를 즉시 읽게 해야 한다.
  - 세부 telemetry는 drill-down 페이지로 분리한다.
- 피해야 할 점:
  - 모든 상태값을 첫 화면에 다 노출하는 것
  - 중요도 구분 없이 같은 크기의 카드만 반복하는 것

### 8) GSAP SVG
- URL: https://gsap.com/svg/
- 분류: 공식 문서 / 인터랙션
- 배운 점:
  - GSAP는 SVG 기반에서 morph, draw, drag 같은 표현을 지원한다.
  - 즉, Throughline이 원하는 `노드 + 연결선 + 흐름 강조`는 SVG/GSAP 조합이 잘 맞는다.
- Throughline 적용:
  - 데이터/제어/물류 흐름선을 SVG path로 두고, hover·alarm·selection 상태에 따라 glow/opacity/animation을 다르게 준다.
  - 라우팅 전환 시 노드 강조, 패널 진입 애니메이션 정도만 절제해서 사용한다.
- 피해야 할 점:
  - 3D 모델링 흉내를 내는 과한 입체감
  - 페이지 전체가 계속 움직이는 산만한 애니메이션

### 9) InOrbit Product
- URL: https://www.inorbit.ai/product
- 분류: 제품 레퍼런스 / 로봇 운영 플랫폼
- 배운 점:
  - InOrbit은 `engineers/operators/executives` 각각이 다른 관점으로 같은 로봇 플랫폼을 본다는 구조를 전면에 둔다.
  - `fleet utilization`, `real-time problem resolution`, `observability`를 핵심 가치로 제시한다.
- Throughline 적용:
  - Throughline도 한 화면 안에서 "운영자 관점의 즉시성"을 우선해야 한다.
  - 로봇 자체 상태보다 `문제 발생 위치`, `연결 이상`, `공정 영향도`가 먼저 보여야 한다.
- 피해야 할 점:
  - 개발자용 디버그 패널처럼 내부 변수만 많이 보이는 UI

### 10) Formant / Fleet management
- URL: https://docs.formant.io/docs/getting-started-fleet-management
- 분류: 제품 문서 / 로봇 fleet 관리
- 배운 점:
  - Formant는 `fleet-level views`, `aggregate health/status`, `configuration templates`, `provision many robots at once`를 명시한다.
  - 즉, 관제의 핵심은 개별 장비 예쁘게 그리기가 아니라 집계/상태/일괄관리다.
- Throughline 적용:
  - 메인 화면에서는 개별 센서 raw값보다 `전체 라인 정상/지연/경고/중단` 같은 집계 레벨을 우선 배치한다.
  - 세부 장비 설정은 하위 페이지에서 다룬다.
- 피해야 할 점:
  - 메인 랜딩에서 저수준 파라미터를 과다 노출하는 것

### 11) Formant / Fleet observability
- URL: https://docs.formant.io/docs/fleet-observability
- 분류: 제품 문서 / observability
- 배운 점:
  - Formant 문서 구조 자체가 observability를 별도 개념으로 분리한다.
  - 운영 화면에서는 telemetry 수집보다 `health/status를 해석 가능하게 보여주는 방식`이 핵심이라는 뜻이다.
- Throughline 적용:
  - 센서값 나열보다 `연결 상태`, `지연`, `에러 이벤트`, `장애 위치`를 시각적으로 우선 표현한다.
  - 이벤트 로그는 화면 아래쪽 보조 영역으로 유지하는 편이 맞다.
- 피해야 할 점:
  - 그래프 화면에 로그/숫자/배지를 한꺼번에 겹쳐 읽기 어렵게 만드는 것

### 12) Digital Twin Synchronization for Robot Fleets
- URL: https://i.partenit.io/knowledge-base/digital-twin-synchronization-for-robot-fleets/
- 분류: 개념 레퍼런스 / 디지털 트윈
- 배운 점:
  - 제목과 설명이 보여주듯, 디지털 트윈은 단순 3D 뷰가 아니라 `robot fleet synchronization` 문제를 다루는 개념이다.
  - 즉, 트윈은 "예쁜 장식"이 아니라 실제 상태와의 동기화 관점에서 읽혀야 한다.
- Throughline 적용:
  - 메인 화면에서 RoboDK/디지털트윈은 독립 오브젝트가 아니라 공정 흐름과 연결된 분석 노드로 보여주는 편이 맞다.
  - 트윈 표현은 3D 바닥판보다 `simulation/optimization` 의미를 전달하는 카드/보드형 표현이 적합하다.
- 피해야 할 점:
  - 디지털 트윈을 장식용 3D 오브젝트처럼 소비하는 것

### 13) Behance / Terafab Control – Ai Smart Factory Automation Ecosystem
- URL: https://www.behance.net/gallery/250459191/Terafab-Control-Ai-Smart-Factory-Automation-Ecosystem
- 분류: 디자인 레퍼런스
- 배운 점:
  - Behance 검색 결과에서 smart factory automation ecosystem 맥락으로 노출되는 대표 사례다.
  - 제목 자체가 Throughline과 유사하게 `factory + control + ecosystem` 구조를 지향한다.
- Throughline 적용:
  - 화면을 단일 기계 UI가 아니라 `생산 라인 + 주변 시스템 생태계`로 읽히게 배치하는 방향이 맞다.
- 피해야 할 점:
  - 화면을 한 장비 상세 화면처럼 좁게 설계하는 것

### 14) Behance / Hyperfab AR Interface and Robotics Dashboard Design
- URL: https://www.behance.net/gallery/249305831/Hyperfab-AR-Interface-and-Robotics-Dashboard-Design
- 분류: 디자인 레퍼런스
- 배운 점:
  - Behance 검색 결과에서 robotics dashboard와 AR interface가 함께 전면에 드러난다.
  - 즉, 산업/로봇 화면에서도 `차갑기만 한 제어판`보다 spatial metaphor와 clear labeling이 중요하다는 힌트를 준다.
- Throughline 적용:
  - 로봇/공정/서버를 서로 다른 종류의 노드로 시각 구분하고, 라벨 구조를 분명히 둔다.
- 피해야 할 점:
  - 아이콘만 있고 텍스트 의미가 불분명한 화면

## Throughline 메인 그래프 화면에 적용할 디자인 원칙 10개

1. 메인 화면의 주인공은 `차트`가 아니라 `공정/장비/시스템 관계 그래프`여야 한다.
2. `데이터 흐름`, `제어 흐름`, `물류 흐름`을 색/선 스타일로 분리해 한눈에 구분되게 한다.
3. 로봇, 컨베이어, 비전, 클라우드, RoboDK, 게이트웨이/서버는 `동등한 카드 목록`이 아니라 역할이 다른 노드로 보이게 한다.
4. 상단에는 숫자 카드 남발 대신 `운영 상태 요약(System, Robot, Vision, PLC, WebSocket)`만 얇고 빠르게 읽히게 둔다.
5. Chart.js는 throughput, cycle time, quality 같은 `2차 지표`에만 제한적으로 사용한다.
6. 메인 장면 인터랙션은 hover, select, focus, route transition 정도로 제한하고 과한 3D/패럴랙스는 피한다.
7. 디지털 트윈은 바닥판 3D 장식이 아니라 `simulation / optimization / sync` 의미를 가진 분석 노드로 표현한다.
8. 로그/알람/제어 패널은 메인 장면을 가리지 않도록 우측/하단 보조 영역으로 분리한다.
9. 각 노드는 `이름 + 역할 + 상태`가 즉시 읽히게 하고, 아이콘만으로 의미를 추측하게 만들지 않는다.
10. 첫 화면은 상세 제어보다 `무엇이 정상이고 어디가 문제인지`를 가장 빨리 알려줘야 한다.

## 바로 반영 가능한 UI 방향 메모

- 중앙: 생산 라인 + 두봇 + 비전 + 배출 게이트를 가장 크게
- 좌상단/상단: 시스템 상태 스트립
- 우상단: 클라우드 / 서버 / 게이트웨이 / RoboDK
- 좌하단: 터틀봇 + 자재 투입 흐름
- 우하단: 데이터 분석 / 이력 / 알람 진입점
- 하단: 이벤트 로그, 우측: 선택 노드 상세 패널
- 시각 스타일: dark base + green/blue neon accent는 유지 가능하되, glass/blur는 보조 수준만 사용

## 제외/보류 메모

- Solink는 이번 환경에서 Cloudflare 차단으로 본문 확인 실패
- Figma Community `IoT Device Monitoring Dashboard`는 403으로 본문 확인 실패
- Dribbble `AI Smart Robotic Management Realtime Dashboard UI/UX Design`는 공개 HTML 확인이 불안정해 참고 후보로만 남김

## 다음 설계 단계 제안

1. 이 문서를 바탕으로 `02-layout-principles.md`에 화면 정보구조를 고정
2. 메인 화면을 `노드/링크/상태 패널` 3계층으로 나눈 wireframe 작성
3. 그 다음에만 Vue 컴포넌트 구조와 Router 페이지 맵으로 내려가기

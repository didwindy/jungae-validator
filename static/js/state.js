/**
 * AppState — 전역 상태 객체
 * 모든 탭이 이 객체를 공유하여 데이터를 주고받음
 */
const AppState = {
  // ── 탭1: 주소/건축물 대장 데이터 ───────────────────────────────────
  address: {
    jibunInput: "",
    fullAddress: "",
    sigunguCd: "",
    bjdongCd: "",
    platGbCd: "0",
    bun: "",
    ji: "",

    landArea: null,
    landJimok: "",

    isAggregate: false,        // 집합건물 여부
    totalFloors: null,
    underFloors: null,
    parkingTotal: null,
    useAprDay: "",
    mainPurps: "",
    etcPurps: "",
    isViolationBldg: false,
    isUnregistered: false,

    dongList: [],
    selectedDong: "",
    selectedHo: "",
    selectedFlrNo: null,
    selectedExclusiveArea: null,

    buildingFetchStatus: "none",  // "none" | "aggregate" | "general" | "notFound"
  },

  // ── 탭2: 12가지 명시사항 ─────────────────────────────────────────
  disclosure: {
    소재지: "",
    소재지_표시방식: "",        // 지번포함|읍면동리|지번+동+층수|지번+동+저중고|읍면동리+층수

    면적: null,
    면적_근거: "건축물대장(전유)",

    거래형태: "",              // 매매|교환|전세|월세
    가격_매매가: null,
    가격_보증금: null,
    가격_차임: null,

    중개대상물종류: "",
    중개대상물종류_특수: "",    // ""|미등기건물|위반건축물

    총층수_지상: null,   // 지상층수 (명시사항 기준)
    총층수_지하: null,   // 지하층수 (병기용)

    입주가능일: "",

    방수: null,
    욕실수: null,

    사용승인일: "",

    주차대수_총: null,
    주차대수_세대당: null,
    주차대수_실제메모: "",

    관리비_정액여부: "",        // 정액|월평균|없음
    관리비_총액: null,
    관리비_비목: {
      일반관리비: null,
      전기료: null,
      수도료: null,
      가스사용료: null,
      난방비: null,
      인터넷사용료: null,
      TV사용료: null,
      기타관리비: null,
    },

    방향: "",
    방향_기준: "",
  },

  // ── 탭3: 중개사무소 / 개업공인중개사 ────────────────────────────
  office: {
    명칭: "",
    소재지: "",
    연락처: "",
    등록번호: "",
    성명: "",
  },

  // ── 내부 상태 ────────────────────────────────────────────────────
  _lawText: null,            // law_text.json 캐시
  _currentTab: "tab1",
};

// ─── 헬퍼: 탭1 자동값 → 탭2 명시사항으로 복사 ────────────────────────────
AppState.syncAutoValues = function () {
  const a = this.address;
  const d = this.disclosure;

  // 자동 채움 가능 항목
  if (a.useAprDay)             d.사용승인일     = a.useAprDay;
  if (a.mainPurps)             d.중개대상물종류  = a.mainPurps;
  if (a.totalFloors  !== null) d.총층수_지상 = a.totalFloors;
  if (a.underFloors !== null && a.underFloors > 0) d.총층수_지하 = a.underFloors;
  if (a.parkingTotal !== null) d.주차대수_총    = a.parkingTotal;

  // 건축물대장 조회 결과에 따른 면적 자동 채움
  const bldgStatus = a.buildingFetchStatus || "none";
  if (bldgStatus === "aggregate" && a.selectedExclusiveArea !== null) {
    d.면적 = a.selectedExclusiveArea;
    d.면적_근거 = "건축물대장(전유)";
  } else if (bldgStatus === "general") {
    d.면적_근거 = "건축물현황";
  } else if (bldgStatus === "notFound" && a.landArea !== null) {
    d.면적 = a.landArea;
    d.면적_근거 = "토지대장";
  }

  // 소재지 기본값 — 표시 방식은 사용자가 선택
  if (a.fullAddress) d.소재지 = a.fullAddress;

  // 위반건축물 자동 표시
  if (a.isViolationBldg) d.중개대상물종류_특수 = "위반건축물";
  if (a.isUnregistered)  d.중개대상물종류_특수 = "미등기건물";
};

// ─── 헬퍼: 페이지 로드 시 localStorage에서 사무소 정보 복원 ──────────────
AppState.loadOfficeFromStorage = function () {
  try {
    const saved = localStorage.getItem("officeInfo");
    if (saved) {
      this.office = { ...this.office, ...JSON.parse(saved) };
      return true;
    }
  } catch (e) { /* 무시 */ }
  return false;
};

// ─── 헬퍼: 사무소 정보 저장 ─────────────────────────────────────────────
AppState.saveOfficeToStorage = function () {
  try {
    localStorage.setItem("officeInfo", JSON.stringify(this.office));
  } catch (e) { /* 무시 */ }
};

// ─── 헬퍼: 전체 초기화 ──────────────────────────────────────────────────
AppState.resetAddress = function () {
  const blank = {
    jibunInput: "", fullAddress: "", sigunguCd: "", bjdongCd: "",
    platGbCd: "0", bun: "", ji: "",
    landArea: null, landJimok: "",
    isAggregate: false, totalFloors: null, underFloors: null,
    parkingTotal: null, useAprDay: "", mainPurps: "", etcPurps: "",
    isViolationBldg: false, isUnregistered: false,
    dongList: [], selectedDong: "", selectedHo: "",
    selectedFlrNo: null, selectedExclusiveArea: null,
    buildingFetchStatus: "none",
  };
  this.address = blank;
};

// ─── 법령 텍스트 로딩 ────────────────────────────────────────────────────
AppState.loadLawText = async function () {
  if (this._lawText) return this._lawText;
  try {
    const r = await fetch("/static/data/law_text.json");
    this._lawText = await r.json();
  } catch (e) {
    this._lawText = {};
  }
  return this._lawText;
};

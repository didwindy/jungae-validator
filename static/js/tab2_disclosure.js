
// ─── 가격 유틸: 천단위 쉼표 + 한글 금액 변환 ─────────────────────────────
function toKoreanPrice(num) {
  if (!num || isNaN(num) || num <= 0) return "";
  const jo   = Math.floor(num / 1_000_000_000_000);
  const eok  = Math.floor((num % 1_000_000_000_000) / 100_000_000);
  const man  = Math.floor((num % 100_000_000) / 10_000);
  const rest = num % 10_000;

  let result = "";
  if (jo)   result += jo + "조 ";
  if (eok)  result += eok + "억 ";
  if (man)  result += man.toLocaleString() + "만 ";
  if (rest && !jo && !eok && !man) result += rest.toLocaleString();
  return result.trim() + "원";
}

function onPriceInput(inputEl, krSpanId) {
  // 숫자와 쉼표만 허용
  let raw = inputEl.value.replace(/[^\d]/g, "");
  const num = parseInt(raw) || 0;

  // 천단위 쉼표 표시
  if (raw) {
    inputEl.value = num.toLocaleString();
  }

  // 한글 금액 표시
  const span = document.getElementById(krSpanId);
  if (span) span.textContent = num > 0 ? toKoreanPrice(num) : "";
}

// 가격 필드에서 순수 숫자 읽기 (쉼표 제거)
function getPriceValue(id) {
  const val = document.getElementById(id)?.value || "";
  const num = parseInt(val.replace(/,/g, "")) || null;
  return num;
}

/**
 * tab2_disclosure.js — 12가지 명시사항 입력 폼
 */

function renderTab2() {
  const d = AppState.disclosure;
  const a = AppState.address;

  // 소재지 자동 조합: 지번 + 동 + 층수
  if (a.fullAddress) {
    let addr = a.fullAddress.replace("[더미] ", "");
    const parts = [];
    parts.push(addr);
    if (a.selectedDong)  parts.push(a.selectedDong);
    if (a.selectedFlrNo) parts.push(a.selectedFlrNo + "층");
    d.소재지 = parts.join(" ");
  }

  // 자동 입력 항목 표시
  setVal("t2-address-display", d.소재지 || "");
  setVal("t2-area", d.면적 ?? "");

  // 건물 유형에 따라 면적 필드 스타일 및 면적 근거 설정
  _updateAreaFieldByType(d);

  setVal("t2-purps", d.중개대상물종류 || "");
  setVal("t2-total-floors-grnd", d.총층수_지상 ?? "");
  setVal("t2-total-floors-ugrd", d.총층수_지하 ?? "");
  setVal("t2-use-apr", d.사용승인일 || "");
  setVal("t2-parking", d.주차대수_총 ?? "");

  // 소재지 표시 방식 선택
  const method = d.소재지_표시방식 || guessDefaultMethod();
  const radios = document.querySelectorAll('input[name="address-method"]');
  radios.forEach(r => { r.checked = (r.value === method); });

  // 거래형태/가격 UI 갱신
  updatePriceUI();

  // 관리비 UI 갱신
  updateManageUI();
}

// ── 건물 유형별 면적 필드 스타일 및 면적 근거 설정 ─────────────────────────
function _updateAreaFieldByType(d) {
  const purps = d.중개대상물종류 || "";
  const areaInput = document.getElementById("t2-area");
  const areaSource = document.getElementById("t2-area-source");
  if (!areaInput || !areaSource) return;

  const isAptOft = ["아파트", "오피스텔"].some(p => purps.includes(p));
  const isLand   = purps.includes("토지") || (!purps && AppState.address.landArea && !AppState.address.mainPurps);

  if (isAptOft) {
    areaInput.classList.add("auto-filled");
    areaSource.value = "건축물대장(전유)";
  } else if (isLand) {
    areaInput.classList.remove("auto-filled");
    areaSource.value = "토지대장";
  } else {
    areaInput.classList.remove("auto-filled");
    areaSource.value = "건축물현황";
  }
}

// ── 유형별 기본 표시방식 추론 ─────────────────────────────────────────────
function guessDefaultMethod() {
  const purps = AppState.disclosure.중개대상물종류 || "";
  const detached = ["단독주택", "다중주택", "다가구주택", "공관"];
  const housing   = ["아파트", "연립주택", "다세대주택", "오피스텔"];
  if (detached.some(p => purps.includes(p))) return "지번포함";
  if (housing.some(p => purps.includes(p)))  return "지번+동+층수";
  return "읍면동리+층수";
}

// ── 거래형태 변경 시 가격 입력 UI 변경 ─────────────────────────────────
function onTradeTypeChange() {
  const v = document.querySelector('input[name="trade-type"]:checked')?.value || "";
  AppState.disclosure.거래형태 = v;
  updatePriceUI();
}

function updatePriceUI() {
  const v = AppState.disclosure.거래형태;
  document.getElementById("price-sale-row").style.display   = (v === "매매" || v === "교환") ? "" : "none";
  document.getElementById("price-lease-row").style.display  = (v === "전세") ? "" : "none";
  document.getElementById("price-month-row").style.display  = (v === "월세") ? "" : "none";

  if (v === "매매" || v === "교환") {
    document.getElementById("t2-price-sale").value = AppState.disclosure.가격_매매가 ?? "";
  }
  if (v === "전세" || v === "월세") {
    document.getElementById("t2-price-deposit").value = AppState.disclosure.가격_보증금 ?? "";
  }
  if (v === "월세") {
    document.getElementById("t2-price-rent").value = AppState.disclosure.가격_차임 ?? "";
  }
}

// ── 관리비 정액여부에 따른 UI 변경 ─────────────────────────────────────
function onManageTypeChange() {
  const v = document.querySelector('input[name="manage-type"]:checked')?.value || "";
  AppState.disclosure.관리비_정액여부 = v;
  updateManageUI();
}

function updateManageUI() {
  const v = AppState.disclosure.관리비_정액여부;
  const total = parseFloat(AppState.disclosure.관리비_총액) || 0;
  // 월 10만원 이상 정액일 때만 비목 분리
  const showBreakdown = (v === "정액" && total >= 100000);
  document.getElementById("manage-breakdown").style.display = showBreakdown ? "" : "none";
  document.getElementById("manage-total-row").style.display = (v === "정액" || v === "월평균") ? "" : "none";
}

// ── 입력값 → AppState 반영 ─────────────────────────────────────────────
function syncTab2ToState() {
  const d = AppState.disclosure;

  d.소재지_표시방식 = document.querySelector('input[name="address-method"]:checked')?.value || "";
  d.면적           = parseFloatSafe(getVal("t2-area"));
  d.면적_근거      = document.getElementById("t2-area-source")?.value || d.면적_근거;
  d.중개대상물종류  = getVal("t2-purps");
  d.중개대상물종류_특수 = getVal("t2-purps-special");
  d.총층수_지상    = parseIntSafe(getVal("t2-total-floors-grnd"));
  d.총층수_지하    = parseIntSafe(getVal("t2-total-floors-ugrd"));
  d.사용승인일     = getVal("t2-use-apr");
  d.주차대수_총    = parseIntSafe(getVal("t2-parking"));
  d.주차대수_세대당   = parseFloatSafe(getVal("t2-parking-per-unit"));
  d.주차대수_실제메모 = getVal("t2-parking-memo");

  d.거래형태       = document.querySelector('input[name="trade-type"]:checked')?.value || "";
  d.가격_매매가    = getPriceValue("t2-price-sale");
  d.가격_보증금    = getPriceValue("t2-price-deposit");
  d.가격_차임      = getPriceValue("t2-price-rent");

  d.입주가능일     = getVal("t2-movein");
  d.방수           = parseIntSafe(getVal("t2-rooms"));
  d.욕실수         = parseIntSafe(getVal("t2-baths"));

  d.관리비_정액여부 = document.querySelector('input[name="manage-type"]:checked')?.value || "";
  d.관리비_총액    = getPriceValue("t2-manage-total");
  // 관리비 비목 (월 10만원 이상 정액 시)
  d.관리비_비목 = {
    일반관리비:   parseIntSafe(getVal("manage-general")) || 0,
    전기료:       parseIntSafe(getVal("manage-elec"))    || 0,
    수도료:       parseIntSafe(getVal("manage-water"))   || 0,
    가스사용료:   parseIntSafe(getVal("manage-gas"))     || 0,
    난방비:       parseIntSafe(getVal("manage-heat"))    || 0,
    인터넷사용료: parseIntSafe(getVal("manage-net"))     || 0,
    TV사용료:     parseIntSafe(getVal("manage-tv"))      || 0,
    기타관리비:   parseIntSafe(getVal("manage-etc"))     || 0,
  };

  d.방향           = getVal("t2-direction");
  d.방향_기준      = document.querySelector('input[name="direction-basis"]:checked')?.value || "";
}

// ─── 탭4로 이동 버튼 ────────────────────────────────────────────────────
function goToTab4FromTab2() {
  syncTab2ToState();
  switchTab("tab4");
  renderTab4();
}

// ─── 유틸 ──────────────────────────────────────────────────────────────
function setVal(id, v) {
  const el = document.getElementById(id);
  if (el) el.value = (v === null || v === undefined) ? "" : v;
}
function getVal(id) {
  return document.getElementById(id)?.value?.trim() || "";
}
function parseFloatSafe(v) {
  const n = parseFloat(v); return isNaN(n) ? null : n;
}
function parseIntSafe(v) {
  const n = parseInt(v); return isNaN(n) ? null : n;
}

/**
 * tab1_address.js v5
 * 흐름: 주소선택 → 토지대장 자동조회 → 건축물대장(수동) → 동선택→층수확정 → 호선택→전용면적
 */

async function postApi(endpoint, body) {
  const r = await fetch(endpoint, {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)
  });
  return r.json();
}

function showStatus(msg, type) {
  const el = document.getElementById("t1-status");
  el.textContent = msg; el.className = "status-msg "+(type||"");
}

function setBldgProgress(pct, label) {
  const wrap = document.getElementById("bldg-progress-wrap");
  const bar  = document.getElementById("bldg-progress-bar");
  const lbl  = document.getElementById("bldg-progress-label");
  if (!wrap) return;
  if (pct <= 0) { wrap.style.display="none"; return; }
  wrap.style.display = "block";
  bar.style.width = pct+"%";
  if (lbl) lbl.textContent = label||"";
  if (pct >= 100) setTimeout(()=>{ wrap.style.display="none"; }, 1500);
}

function showAreaLoading(show) {
  const el = document.getElementById("area-loading-overlay");
  if (el) el.style.display = show ? "flex" : "none";
}

// ─── STEP 1: 후보 검색 ───────────────────────────────────────────────────
async function onSearchCandidates() {
  const query = document.getElementById("t1-address-input").value.trim();
  if (!query) { showStatus("검색어를 입력해주세요.","error"); return; }

  showStatus("주소 검색 중...","loading");
  AppState.resetAddress(); clearResults();

  const data = await postApi("/api/search-candidates", {query});
  if (data.error) { showStatus("❌ "+data.error,"error"); return; }

  const candidates = data.candidates||[];
  if (!candidates.length) { showStatus("검색 결과가 없습니다. 더 구체적인 주소를 입력해주세요.","error"); return; }

  renderCandidateList(candidates, data._dummy);
  showStatus(`${candidates.length}건 검색됨 — 아래 목록에서 정확한 주소를 선택하세요.`,"loading");
}

function renderCandidateList(candidates, isDummy) {
  const container = document.getElementById("t1-candidate-list");
  container.innerHTML = isDummy
    ? `<div class="candidate-dummy-notice">⚠ 더미 데이터 (VWorld API 키 미설정)</div>` : "";
  container.style.display = "block";
  candidates.forEach(c => {
    const btn = document.createElement("button");
    btn.className = "candidate-item";
    btn.textContent = c.text;
    btn.onclick = () => onSelectCandidate(c, btn);
    container.appendChild(btn);
  });
}

// ─── STEP 2: 후보 선택 → 토지대장 자동 조회 ─────────────────────────────
async function onSelectCandidate(candidate, btnEl) {
  document.querySelectorAll(".candidate-item").forEach(b=>b.classList.remove("selected"));
  btnEl.classList.add("selected");
  showStatus("주소 코드 확인 중...","loading");

  let result = {...candidate};
  if (candidate.needGeocode) {
    const geo = await postApi("/api/geocode-single", {address: candidate.text});
    if (geo.error) { showStatus("❌ 코드 추출 실패: "+geo.error,"error"); return; }
    result = {...result, ...geo};
  }

  AppState.address.fullAddress = result.text||result.fullAddress||candidate.text;
  AppState.address.sigunguCd   = result.sigunguCd||"";
  AppState.address.bjdongCd    = result.bjdongCd||"";
  AppState.address.platGbCd    = result.platGbCd||"0";
  AppState.address.bun         = (result.bun||"0000").padStart(4,"0");
  AppState.address.ji          = (result.ji||"0000").padStart(4,"0");

  renderSelectedAddress(AppState.address);

  // 주소 선택 후 토지대장 자동 조회
  await onFetchLand();
}

function renderSelectedAddress(a) {
  document.getElementById("t1-address-result").innerHTML = `
    <div class="result-card selected-address-card">
      <div class="result-row">
        <span class="result-label">📍 소재지</span>
        <span class="result-value"><strong>${a.fullAddress}</strong></span>
      </div>
      <div class="result-row">
        <span class="result-label">시군구코드</span><span class="result-value mono">${a.sigunguCd||"—"}</span>
        <span class="result-label ml">법정동코드</span><span class="result-value mono">${a.bjdongCd||"—"}</span>
      </div>
      <div class="result-row">
        <span class="result-label">본번/부번</span><span class="result-value mono">${a.bun} / ${a.ji}</span>
      </div>
    </div>`;
}

// ─── STEP 3: 토지대장 조회 (주소 선택 후 자동 실행) ─────────────────────
async function onFetchLand() {
  const a = AppState.address;
  if (!a.sigunguCd) { showStatus("❌ 주소를 먼저 선택해주세요.","error"); return; }
  showStatus("🗺 토지대장 조회 중...","loading");

  const data = await postApi("/api/land-info", {
    sigunguCd:a.sigunguCd, bjdongCd:a.bjdongCd,
    platGbCd:a.platGbCd, bun:a.bun, ji:a.ji
  });

  if (data.error) {
    document.getElementById("t1-land-result").innerHTML = `<div class="error-box">❌ ${data.error}</div>`;
    showStatus("토지대장 조회 실패 — 건축물대장 조회는 계속 가능합니다.","error");
    return;
  }

  AppState.address.landArea  = data.landArea;
  AppState.address.landJimok = data.jimok;

  document.getElementById("t1-land-result").innerHTML = `
    <div class="result-card">
      <div class="result-row">
        <span class="result-label">토지면적</span>
        <span class="result-value"><strong>${data.landArea.toLocaleString()} ㎡</strong></span>
        ${data._dummy?'<span class="dummy-tag">더미</span>':""}
      </div>
      <div class="result-row">
        <span class="result-label">지목</span>
        <span class="result-value">${data.jimok}</span>
      </div>
    </div>`;
  showStatus("✓ 토지대장 조회 완료 — 건축물대장 조회 버튼을 눌러주세요.","success");
}

// ─── STEP 4: 건축물대장 표제부 조회 ─────────────────────────────────────
async function onFetchBuilding() {
  const a = AppState.address;
  if (!a.sigunguCd) { showStatus("❌ 주소를 먼저 선택해주세요.","error"); return; }

  setBldgProgress(15,"표제부 조회 중...");
  showStatus("건축물대장 표제부 조회 중...","loading");

  const data = await postApi("/api/building-title", {
    sigunguCd:a.sigunguCd, bjdongCd:a.bjdongCd, bun:a.bun, ji:a.ji
  });

  if (data.error) {
    document.getElementById("t1-building-result").innerHTML=`<div class="error-box">❌ ${data.error}</div>`;
    setBldgProgress(0); return;
  }

  AppState.address.totalFloors  = data.totalFloors;
  AppState.address.underFloors  = data.underFloors;
  AppState.address.parkingTotal = data.parking;
  AppState.address.useAprDay    = data.useAprDay;
  AppState.address.mainPurps    = data.mainPurps;
  AppState.address.etcPurps     = data.etcPurps;
  AppState.address.isAggregate  = data.isAggregate;

  renderBuildingResult(data);
  setBldgProgress(30,"표제부 완료");

  if (data.isAggregate) {
    setBldgProgress(40,"동·호 목록 수집 중...");
    await onFetchDongHo();
  } else {
    setBldgProgress(100,"완료");
    showStatus("✓ 건축물대장 조회 완료 (일반/단독 건물)","success");
    document.getElementById("t1-dong-ho-section").style.display = "none";
  }
}

function renderBuildingResult(data) {
  // 집합건물은 동 선택 후 총층수 확정 예정
  const floorTxt = data.isAggregate
    ? `<span style="color:var(--amber)">동 선택 후 확정</span>`
    : (data.totalFloors > 0 ? `지상 <strong>${data.totalFloors}</strong>층 / 지하 ${data.underFloors}층` : "미확인");

  document.getElementById("t1-building-result").innerHTML = `
    <div class="result-card">
      <div class="result-row">
        <span class="result-label">대장 구분</span>
        <span class="result-value">${data.isAggregate?"🏢 집합건물":"🏠 일반건물"}</span>
        ${data._dummy?'<span class="dummy-tag">더미</span>':""}
      </div>
      <div class="result-row">
        <span class="result-label">주용도</span>
        <span class="result-value">${data.mainPurps} ${data.etcPurps?"("+data.etcPurps+")":""}</span>
      </div>
      <div class="result-row">
        <span class="result-label">총층수</span>
        <span class="result-value" id="bldg-floor-display">${floorTxt}</span>
      </div>
      <div class="result-row">
        <span class="result-label">사용승인일</span>
        <span class="result-value">${data.useAprDay||"미확인"}</span>
      </div>
      <div class="result-row">
        <span class="result-label">주차대수</span>
        <span class="result-value">${data.parking}대</span>
      </div>
    </div>`;
}

// ─── STEP 5: 동/호 목록 조회 ─────────────────────────────────────────────
async function onFetchDongHo() {
  const a = AppState.address;
  showStatus("동·호 목록 수집 중... (세대 수에 따라 수 초 소요)","loading");
  setBldgProgress(50,"동·호 목록 수집 중...");

  const data = await postApi("/api/building-dong-ho", {
    sigunguCd:a.sigunguCd, bjdongCd:a.bjdongCd, bun:a.bun, ji:a.ji
  });

  if (data.error) { showStatus("❌ "+data.error,"error"); setBldgProgress(0); return; }

  AppState.address.dongList = data.dongList;

  // maxFlrNo 저장 (동 선택 전 폴백용)
  if (data.maxFlrNo) AppState.address._maxFlrNo = data.maxFlrNo;

  renderDongSelect(data.dongList);
  document.getElementById("t1-dong-ho-section").style.display = "block";
  setBldgProgress(75,"동을 선택하세요");
  showStatus(`✓ 동·호 목록 완료 (총 ${data.totalCount}개 호) — 동을 선택해주세요.`,"success");
}

// ─── STEP 6: 동 선택 → 해당 동의 총층수 조회 ────────────────────────────
async function onDongChange() {
  const dongNm = document.getElementById("t1-dong-select").value;
  AppState.address.selectedDong  = dongNm;
  AppState.address.selectedHo    = "";
  AppState.address.selectedFlrNo = null;
  AppState.address.selectedExclusiveArea = null;

  const dongObj = AppState.address.dongList.find(d=>d.dongNm===dongNm);
  renderHoSelect(dongObj ? dongObj.hoList : []);
  document.getElementById("t1-area-result").innerHTML = "";
  showAreaLoading(false);

  if (!dongNm) return;

  // 해당 동의 총층수 조회
  setBldgProgress(80,"해당 동 층수 조회 중...");
  showStatus(`${dongNm}의 총층수 확인 중...`,"loading");

  const a = AppState.address;
  const floorData = await postApi("/api/dong-floors", {
    sigunguCd:a.sigunguCd, bjdongCd:a.bjdongCd,
    bun:a.bun, ji:a.ji, dongNm:dongNm
  });

  if (!floorData.error && floorData.grndFlrCnt > 0) {
    AppState.address.totalFloors = floorData.grndFlrCnt;
    AppState.address.underFloors = floorData.ugrndFlrCnt || AppState.address.underFloors;

    // 화면 업데이트
    const floorEl = document.getElementById("bldg-floor-display");
    if (floorEl) {
      const ugrd = floorData.ugrndFlrCnt || AppState.address.underFloors || 0;
      floorEl.innerHTML = `지상 <strong>${floorData.grndFlrCnt}</strong>층 / 지하 ${ugrd}층
        <span style="font-size:.72rem;color:var(--green);margin-left:4px">(${dongNm} 기준)</span>`;
    }
    setBldgProgress(85,"층수 확정 — 호를 선택하세요");
    showStatus(`✓ ${dongNm} 총층수: 지상 ${floorData.grndFlrCnt}층 — 호를 선택해주세요.`,"success");
  } else {
    // 폴백: maxFlrNo 또는 기존값
    const fallback = AppState.address._maxFlrNo || AppState.address.totalFloors || 0;
    if (fallback) AppState.address.totalFloors = fallback;
    setBldgProgress(85,"호를 선택하세요");
    showStatus("호를 선택해주세요.","loading");
  }
}

// ─── STEP 7: 호 선택 → 전용면적 조회 ────────────────────────────────────
async function onHoChange() {
  const hoNm = document.getElementById("t1-ho-select").value;
  AppState.address.selectedHo = hoNm;
  if (!hoNm) return;

  const a = AppState.address;
  setBldgProgress(90,"전용면적 조회 중...");
  showAreaLoading(true);
  showStatus("전용면적 조회 중... 잠시 기다려주세요. (최대 15초)","loading");

  const data = await postApi("/api/exclusive-area", {
    sigunguCd:a.sigunguCd, bjdongCd:a.bjdongCd,
    bun:a.bun, ji:a.ji, dongNm:a.selectedDong, hoNm
  });

  showAreaLoading(false);

  if (data.error) {
    document.getElementById("t1-area-result").innerHTML=`<div class="error-box">❌ ${data.error}</div>`;
    setBldgProgress(0); return;
  }

  AppState.address.selectedExclusiveArea = data.exclusiveArea;
  const dongObj = a.dongList.find(d=>d.dongNm===a.selectedDong);
  const hoObj   = dongObj?.hoList.find(h=>h.hoNm===hoNm);
  if (hoObj) AppState.address.selectedFlrNo = hoObj.flrNo;

  document.getElementById("t1-area-result").innerHTML = `
    <div class="result-card">
      <div class="result-row highlight">
        <span class="result-label">✅ 전용면적</span>
        <span class="result-value strong">${data.exclusiveArea} ㎡</span>
        ${data._dummy?'<span class="dummy-tag">더미</span>':""}
      </div>
      <div class="result-row">
        <span class="result-label">해당 층</span>
        <span class="result-value">${hoObj?.flrNo??"—"} 층 / 총 ${AppState.address.totalFloors}층 (지상)</span>
      </div>
    </div>`;

  setBldgProgress(100,"✓ 모든 조회 완료");
  showStatus("✓ 전용면적 입력 완료 — '명시사항 입력 탭으로' 버튼을 눌러주세요.","success");
}

// ─── 렌더링 헬퍼 ─────────────────────────────────────────────────────────
function renderDongSelect(dongList) {
  const sel = document.getElementById("t1-dong-select");
  sel.innerHTML = '<option value="">-- 동 선택 --</option>';
  dongList.forEach(d => {
    const o = document.createElement("option");
    o.value=d.dongNm; o.textContent=d.dongNm; sel.appendChild(o);
  });
}
function renderHoSelect(hoList) {
  const sel = document.getElementById("t1-ho-select");
  sel.innerHTML = '<option value="">-- 호 선택 --</option>';
  hoList.forEach(h => {
    const o = document.createElement("option");
    o.value=h.hoNm; o.textContent=`${h.hoNm} (${h.flrNo}층)`; sel.appendChild(o);
  });
}
function clearResults() {
  ["t1-candidate-list","t1-address-result","t1-land-result",
   "t1-building-result","t1-area-result"].forEach(id=>{
    const el = document.getElementById(id);
    if (el) { el.innerHTML=""; if(id==="t1-candidate-list") el.style.display="none"; }
  });
  document.getElementById("t1-dong-ho-section").style.display="none";
  setBldgProgress(0); showAreaLoading(false);
}
function goToTab2() {
  AppState.syncAutoValues(); switchTab("tab2"); renderTab2();
}

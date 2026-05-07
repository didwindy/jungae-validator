/**
 * tab4_validate.js — 검증 실행 및 결과 렌더링
 */

async function renderTab4() {
  document.getElementById("t4-result").innerHTML =
    '<div class="loading-msg">검증 중...</div>';

  const body = {
    disclosure: AppState.disclosure,
    address: AppState.address,
    office: AppState.office,
  };

  const r = await fetch("/api/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();

  renderValidationResult(data);
}

function renderValidationResult(data) {
  const passed = data.passed;
  const failed = data.failed;
  const total  = data.total;
  const pct    = Math.round((passed / total) * 100);

  const catOrder = ["명시의무", "거짓광고", "사무소"];
  const catLabels = { 명시의무: "명시의무", 거짓광고: "거짓·과장 광고", 사무소: "사무소 항목" };
  const catIcons  = { 명시의무: "📋", 거짓광고: "⚠️", 사무소: "🏢" };

  let catHtml = "";
  catOrder.forEach(cat => {
    const items = (data.categories || {})[cat] || [];
    if (!items.length) return;

    const failItems = items.filter(i => !i.passed);
    const passItems = items.filter(i => i.passed);

    catHtml += `
      <div class="result-category">
        <h3 class="cat-title">${catIcons[cat]} ${catLabels[cat]}
          <span class="cat-score">${passItems.length}/${items.length} 통과</span>
        </h3>`;

    failItems.forEach(item => {
      catHtml += `
        <div class="result-item fail">
          <div class="item-header">
            <span class="item-icon">❌</span>
            <span class="item-subject">${item.subject}</span>
          </div>
          <div class="item-message">${item.message}</div>
          <div class="item-law">근거: ${item.law}</div>
          <button class="law-btn" onclick="openLawModal('${getLawKey(item.subject)}')">📖 관련 법령 보기</button>
        </div>`;
    });

    if (passItems.length) {
      catHtml += `<div class="result-pass-group">`;
      passItems.forEach(item => {
        catHtml += `
          <div class="result-item pass">
            <span class="item-icon">✅</span>
            <span class="item-subject">${item.subject}</span>
          </div>`;
      });
      catHtml += `</div>`;
    }

    catHtml += `</div>`;
  });

  document.getElementById("t4-result").innerHTML = `
    <div class="validation-summary ${failed === 0 ? 'all-pass' : 'has-fail'}">
      <div class="summary-score">
        <div class="score-circle">
          <span class="score-pct">${pct}%</span>
        </div>
        <div class="score-detail">
          <div>총 <strong>${total}</strong>개 항목 검증</div>
          <div class="pass-count">✅ 통과 <strong>${passed}</strong>개</div>
          <div class="fail-count">❌ 위반 <strong>${failed}</strong>개</div>
        </div>
      </div>
      ${failed === 0
        ? '<div class="all-pass-msg">🎉 모든 항목이 법적 기준을 충족합니다.</div>'
        : `<div class="fail-msg">위반 항목을 수정 후 재검증하세요.</div>`}
    </div>
    ${catHtml}
    <div class="action-row">
      <button class="btn-secondary" onclick="switchTab('tab2'); renderTab2()">✏ 명시사항 수정</button>
      <button class="btn-primary" onclick="renderTab4()">🔄 재검증</button>
    </div>`;
}

// subject → law_text.json 키 매핑
function getLawKey(subject) {
  const map = {
    "소재지": "소재지",
    "면적": "면적",
    "면적-대장일치": "면적",
    "가격": "가격",
    "중개대상물종류": "중개대상물종류",
    "위반건축물표시": "중개대상물종류",
    "거래형태": "거래형태",
    "총층수": "총층수",
    "총층수-대장일치": "총층수",
    "입주가능일": "입주가능일",
    "방수/욕실수": "방수/욕실수",
    "사용승인일": "사용승인일",
    "주차대수": "주차대수",
    "주차대수-대장일치": "주차대수",
    "방향": "방향",
  };
  return map[subject] || subject;
}

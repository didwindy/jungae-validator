/**
 * law_modal.js — 법령 팝업 (각 항목의 📖 버튼)
 */

function openLawModal(subject) {
  AppState.loadLawText().then(law => {
    const info = law[subject];
    if (!info) return;

    const violationsHtml = (info.violations || [])
      .map(v => `<li class="law-violation-item">${v}</li>`).join("");
    const detailHtml = (info.detail || [])
      .map(d => `<li>${d}</li>`).join("");

    document.getElementById("law-modal-title").textContent = info.title;
    document.getElementById("law-modal-law").textContent = info.law;
    document.getElementById("law-modal-summary").textContent = info.summary;
    document.getElementById("law-modal-detail").innerHTML = detailHtml;
    document.getElementById("law-modal-violations").innerHTML = violationsHtml;

    document.getElementById("law-modal").classList.add("active");
  });
}

function closeLawModal() {
  document.getElementById("law-modal").classList.remove("active");
}

// ESC 키로 닫기
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeLawModal();
});

// 바깥 클릭으로 닫기
document.getElementById("law-modal")?.addEventListener("click", e => {
  if (e.target.id === "law-modal") closeLawModal();
});

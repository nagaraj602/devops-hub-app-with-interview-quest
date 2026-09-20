/* ==============================================================================
   Command Cheatsheet JavaScript: Category Tabs, Search & Copy Functions
   ============================================================================== */

let currentCsCategory = "all";
let csSearchQuery = "";

document.addEventListener("DOMContentLoaded", () => {
  initCheatsheet();
});

function initCheatsheet() {
  initCategoryTabs();
  initCheatsheetSearch();
}

function initCategoryTabs() {
  const tabs = document.querySelectorAll(".cs-tab-pill");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentCsCategory = tab.getAttribute("data-category") || "all";
      applyCsFilters();
    });
  });
}

function initCheatsheetSearch() {
  const searchInput = document.getElementById("csSearchInput");
  if (!searchInput) return;

  let timeout = null;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      csSearchQuery = e.target.value.trim().toLowerCase();
      applyCsFilters();
    }, 150);
  });
}

function applyCsFilters() {
  const items = document.querySelectorAll(".cs-item-card");
  let visibleCount = 0;

  items.forEach(card => {
    const cardCat = (card.getAttribute("data-category") || "").toLowerCase();
    const cmdText = (card.querySelector(".cmd-code-text, .code-example-pre")?.textContent || "").toLowerCase();
    const expText = (card.querySelector(".cmd-explanation-text, .code-example-title")?.textContent || "").toLowerCase();
    const secText = (card.querySelector(".cmd-section-label")?.textContent || "").toLowerCase();

    const matchCat = currentCsCategory === "all" || cardCat === currentCsCategory.toLowerCase();
    const matchSearch = !csSearchQuery ||
      cmdText.includes(csSearchQuery) ||
      expText.includes(csSearchQuery) ||
      secText.includes(csSearchQuery);

    if (matchCat && matchSearch) {
      card.style.display = "";
      visibleCount++;
    } else {
      card.style.display = "none";
    }
  });

  const emptyState = document.getElementById("csEmptyState");
  if (emptyState) {
    emptyState.style.display = visibleCount === 0 ? "block" : "none";
  }
}

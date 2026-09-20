/* ==============================================================================
   Question Bank JavaScript: Categorization, Collapse/Expand, Calendar & Favorites
   ============================================================================== */

let currentCategory = "All";
let currentSort = "recent";
let searchQuery = "";
let showFavoritesOnly = false;
let userFavorites = JSON.parse(localStorage.getItem("devops_hub_favorites") || "[]");

document.addEventListener("DOMContentLoaded", () => {
  initQuestionBank();
});

function initQuestionBank() {
  updateFavoritesCountUI();
  initCategoryPills();
  initSearchAndSort();
  initGlobalAccordions();
  initQuestionToggles();
  initCalendarModal();
}

// Favorites / Bookmarks Manager
function updateFavoritesCountUI() {
  const favCountElem = document.getElementById("statFavoritesCount");
  if (favCountElem) {
    favCountElem.textContent = userFavorites.length;
  }
}

function toggleFavorite(qId, e) {
  if (e) e.stopPropagation();
  const idx = userFavorites.indexOf(qId);
  if (idx > -1) {
    userFavorites.splice(idx, 1);
    showToast("Removed from bookmarks", "info");
  } else {
    userFavorites.push(qId);
    showToast("Question bookmarked!", "success");
  }
  localStorage.setItem("devops_hub_favorites", JSON.stringify(userFavorites));
  updateFavoritesCountUI();

  // Update UI icons
  document.querySelectorAll(`.fav-btn[data-qid="${qId}"]`).forEach(btn => {
    btn.classList.toggle("favorite-active", userFavorites.includes(qId));
    const icon = btn.querySelector("i");
    if (icon) {
      icon.className = userFavorites.includes(qId) ? "fa-solid fa-star" : "fa-regular fa-star";
    }
  });

  const questionCard = document.getElementById(qId);
  if (questionCard) {
    questionCard.classList.toggle("favorite", userFavorites.includes(qId));
  }

  if (showFavoritesOnly) {
    applyFilters();
  }
}

// Category Pills Filtering
function initCategoryPills() {
  const pills = document.querySelectorAll(".category-pill");
  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentCategory = pill.getAttribute("data-category") || "All";
      showFavoritesOnly = false;
      applyFilters();
    });
  });

  // Favorites stat card click handler
  const favCard = document.getElementById("statCardFavorites");
  if (favCard) {
    favCard.style.cursor = "pointer";
    favCard.addEventListener("click", () => {
      showFavoritesOnly = !showFavoritesOnly;
      pills.forEach(p => p.classList.remove("active"));
      if (showFavoritesOnly) {
        showToast("Filtering bookmarked questions", "info");
      }
      applyFilters();
    });
  }
}

// Search & Sort Handlers
function initSearchAndSort() {
  const searchInput = document.getElementById("qbSearchInput");
  if (searchInput) {
    let timeout = null;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        searchQuery = e.target.value.trim().toLowerCase();
        applyFilters();
      }, 200);
    });
  }

  const sortSelect = document.getElementById("qbSortSelect");
  if (sortSelect) {
    sortSelect.addEventListener("change", (e) => {
      currentSort = e.target.value;
      sortCompaniesDOM(currentSort);
    });
  }
}

// Main Filter Logic: Category, Search & Favorites
function applyFilters() {
  const companyCards = document.querySelectorAll(".company-card");
  let visibleCompaniesCount = 0;
  let visibleQuestionsCount = 0;

  const isFilteringCategory = currentCategory.toLowerCase() !== "all";

  companyCards.forEach(companyCard => {
    const cName = (companyCard.getAttribute("data-company-name") || "").toLowerCase();
    const roundBlocks = companyCard.querySelectorAll(".round-block");
    let companyHasMatches = false;

    roundBlocks.forEach(roundBlock => {
      const rName = (roundBlock.getAttribute("data-round-name") || "").toLowerCase();
      const questionItems = roundBlock.querySelectorAll(".question-item");
      let roundHasMatches = false;

      questionItems.forEach(qItem => {
        const qId = qItem.id;
        const qCat = (qItem.getAttribute("data-category") || "").toLowerCase();
        const qText = (qItem.querySelector(".question-text")?.textContent || "").toLowerCase();
        const aText = (qItem.querySelector(".answer-markdown")?.textContent || "").toLowerCase();

        // 1. Category Check
        const matchCategory = !isFilteringCategory || qCat === currentCategory.toLowerCase();

        // 2. Favorites Check
        const matchFav = !showFavoritesOnly || userFavorites.includes(qId);

        // 3. Search Query Check
        const matchSearch = !searchQuery ||
          cName.includes(searchQuery) ||
          rName.includes(searchQuery) ||
          qText.includes(searchQuery) ||
          aText.includes(searchQuery) ||
          qCat.includes(searchQuery);

        if (matchCategory && matchFav && matchSearch) {
          qItem.style.display = "";
          roundHasMatches = true;
          companyHasMatches = true;
          visibleQuestionsCount++;
        } else {
          qItem.style.display = "none";
        }
      });

      if (roundHasMatches) {
        roundBlock.style.display = "";
        // Requirement: If category is selected, matching company and rounds automatically expand, but answers remain in collapse mode!
        if (isFilteringCategory || searchQuery) {
          roundBlock.classList.add("expanded");
        }
      } else {
        roundBlock.style.display = "none";
      }
    });

    if (companyHasMatches) {
      companyCard.style.display = "";
      visibleCompaniesCount++;
      if (isFilteringCategory || searchQuery) {
        companyCard.classList.add("expanded");
      }
    } else {
      companyCard.style.display = "none";
    }
  });

  // Update empty state if needed
  const emptyState = document.getElementById("qbEmptyState");
  if (emptyState) {
    emptyState.style.display = visibleCompaniesCount === 0 ? "block" : "none";
  }
}

// Global Accordion Expand / Collapse Buttons
function initGlobalAccordions() {
  const expandAllBtn = document.getElementById("expandAllCompaniesBtn");
  const collapseAllBtn = document.getElementById("collapseAllCompaniesBtn");
  const expandAllAnswersBtn = document.getElementById("expandAllAnswersBtn");
  const collapseAllAnswersBtn = document.getElementById("collapseAllAnswersBtn");

  // Expand all companies and rounds, but keep answers collapsed
  if (expandAllBtn) {
    expandAllBtn.addEventListener("click", () => {
      document.querySelectorAll(".company-card").forEach(c => c.classList.add("expanded"));
      document.querySelectorAll(".round-block").forEach(r => r.classList.add("expanded"));
      showToast("All companies & rounds expanded", "info");
    });
  }

  // Collapse all companies and rounds
  if (collapseAllBtn) {
    collapseAllBtn.addEventListener("click", () => {
      document.querySelectorAll(".company-card").forEach(c => c.classList.remove("expanded"));
      document.querySelectorAll(".round-block").forEach(r => r.classList.remove("expanded"));
      showToast("All companies & rounds collapsed", "info");
    });
  }

  // Separate button to expand all answers at once
  if (expandAllAnswersBtn) {
    expandAllAnswersBtn.addEventListener("click", () => {
      // Also expand company and round containers so answers are immediately visible
      document.querySelectorAll(".company-card").forEach(c => c.classList.add("expanded"));
      document.querySelectorAll(".round-block").forEach(r => r.classList.add("expanded"));
      document.querySelectorAll(".question-item").forEach(q => q.classList.add("expanded"));
      showToast("All answers expanded", "success");
    });
  }

  // Separate button to collapse all answers at once
  if (collapseAllAnswersBtn) {
    collapseAllAnswersBtn.addEventListener("click", () => {
      document.querySelectorAll(".question-item").forEach(q => q.classList.remove("expanded"));
      showToast("All answers collapsed", "info");
    });
  }
}

// Individual Company, Round & Question Accordion Click Handlers
function initQuestionToggles() {
  document.addEventListener("click", (e) => {
    // If clicking on copy button or fav button, do not toggle accordions
    if (e.target.closest(".action-icon-btn") || e.target.closest(".copy-btn") || e.target.closest(".copy-name-btn")) {
      return;
    }

    // Check if user currently has text selected with mouse drag
    const selectedText = window.getSelection().toString();
    if (selectedText && selectedText.trim().length > 0) {
      return;
    }

    // Company header click
    const compHeader = e.target.closest(".company-header");
    if (compHeader) {
      const card = compHeader.closest(".company-card");
      if (card) {
        card.classList.toggle("expanded");
      }
      return;
    }

    // Round header click
    const roundHeader = e.target.closest(".round-header");
    if (roundHeader) {
      const block = roundHeader.closest(".round-block");
      if (block) {
        block.classList.toggle("expanded");
      }
      return;
    }

    // Question header click (toggles question answer)
    const qHeader = e.target.closest(".question-header");
    if (qHeader && !e.target.closest(".action-icon-btn")) {
      const qItem = qHeader.closest(".question-item");
      if (qItem) {
        qItem.classList.toggle("expanded");
      }
      return;
    }

    // Copy Question Text
    const copyQBtn = e.target.closest(".copy-q-btn");
    if (copyQBtn) {
      const qItem = copyQBtn.closest(".question-item");
      const text = qItem.querySelector(".question-text")?.textContent.trim();
      copyTextToClipboard(text, "Question copied!");
      return;
    }

    // Copy Answer Text
    const copyAnsBtn = e.target.closest(".copy-ans-btn");
    if (copyAnsBtn) {
      const qItem = copyAnsBtn.closest(".question-item");
      const text = qItem.querySelector(".answer-markdown")?.textContent.trim();
      copyTextToClipboard(text, "Answer copied!");
      return;
    }
  });
}

// Sorting Companies in DOM
function sortCompaniesDOM(sortMode) {
  const container = document.getElementById("companyListContainer");
  if (!container) return;

  const cards = Array.from(container.querySelectorAll(".company-card"));

  cards.sort((a, b) => {
    const aName = (a.getAttribute("data-company-name") || "").toLowerCase();
    const bName = (b.getAttribute("data-company-name") || "").toLowerCase();
    const aOrder = parseFloat(a.getAttribute("data-file-order") || "0");
    const bOrder = parseFloat(b.getAttribute("data-file-order") || "0");
    const aTime = parseFloat(a.getAttribute("data-timestamp") || "0");
    const bTime = parseFloat(b.getAttribute("data-timestamp") || "0");
    const aQs = parseInt(a.getAttribute("data-total-questions") || "0");
    const bQs = parseInt(b.getAttribute("data-total-questions") || "0");

    if (sortMode === "name_asc") {
      return aName.localeCompare(bName);
    } else if (sortMode === "name_desc") {
      return bName.localeCompare(aName);
    } else if (sortMode === "most_questions") {
      return bQs - aQs;
    } else if (sortMode === "date") {
      return bTime - aTime;
    } else {
      // Default: Recent (file order first, then timestamp, then name)
      if (bOrder !== aOrder) return bOrder - aOrder;
      if (bTime !== aTime) return bTime - aTime;
      return aName.localeCompare(bName);
    }
  });

  cards.forEach(card => container.appendChild(card));
}

// Calendar Pop-Up Modal Logic
let currentCalYear = 2026;
let currentCalMonth = 8; // September (0-indexed: 8 = Sep)
let calendarEventsData = {};

function initCalendarModal() {
  const calTriggerBtn = document.getElementById("calendarTriggerBtn");
  if (calTriggerBtn) {
    calTriggerBtn.addEventListener("click", () => {
      openCalendarModal();
    });
  }

  // Load calendar events
  fetch("/api/calendar")
    .then(res => res.json())
    .then(data => {
      calendarEventsData = data || {};
    })
    .catch(err => console.error("Error loading calendar events:", err));
}

function openCalendarModal() {
  openModal("calendarModal");
  renderCalendarView(currentCalYear, currentCalMonth);
}

function prevCalendarMonth() {
  currentCalMonth--;
  if (currentCalMonth < 0) {
    currentCalMonth = 11;
    currentCalYear--;
  }
  renderCalendarView(currentCalYear, currentCalMonth);
}

function nextCalendarMonth() {
  currentCalMonth++;
  if (currentCalMonth > 11) {
    currentCalMonth = 0;
    currentCalYear++;
  }
  renderCalendarView(currentCalYear, currentCalMonth);
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

function renderCalendarView(year, month) {
  const titleElem = document.getElementById("calendarMonthTitle");
  if (titleElem) {
    titleElem.textContent = `${MONTH_NAMES[month]} ${year}`;
  }

  const gridElem = document.getElementById("calendarGridDays");
  if (!gridElem) return;

  gridElem.innerHTML = "";

  const firstDay = new Date(year, month, 1).getDay();
  // Adjust Monday as start of week (0: Mon ... 6: Sun)
  const startDayOffset = (firstDay + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  // Fill leading empty cells
  for (let i = 0; i < startDayOffset; i++) {
    const emptyCell = document.createElement("div");
    emptyCell.className = "calendar-day-cell empty";
    gridElem.appendChild(emptyCell);
  }

  // Month short prefix for matching (e.g. "Sep", "Aug")
  const monthShort = MONTH_NAMES[month].substring(0, 3);

  for (let d = 1; d <= daysInMonth; d++) {
    const dayCell = document.createElement("div");
    dayCell.className = "calendar-day-cell";

    const dayNum = document.createElement("span");
    dayNum.className = "day-number";
    dayNum.textContent = d;
    dayCell.appendChild(dayNum);

    // Look for matching events in calendarEventsData
    // Format in dates could be DD-MM-YYYY or D-Sep-YYYY or 17-09-2026
    const matchingEvents = [];
    const dayStrPadded = d < 10 ? `0${d}` : `${d}`;
    const monthPadded = (month + 1) < 10 ? `0${month + 1}` : `${month + 1}`;

    for (const [dateStr, events] of Object.entries(calendarEventsData)) {
      if (
        dateStr.includes(`${dayStrPadded}-${monthPadded}-${year}`) ||
        dateStr.includes(`${d}-${monthShort}-${year}`) ||
        dateStr.includes(`${dayStrPadded}-${monthShort}-${year}`)
      ) {
        matchingEvents.push(...events);
      }
    }

    if (matchingEvents.length > 0) {
      dayCell.classList.add("has-interview");
      const badge = document.createElement("div");
      badge.className = "interview-dot-badge";
      badge.textContent = `${matchingEvents.length} Rounds`;
      dayCell.appendChild(badge);

      dayCell.addEventListener("click", () => {
        showDayInterviewDetails(d, MONTH_NAMES[month], year, matchingEvents);
      });
    }

    gridElem.appendChild(dayCell);
  }
}

function showDayInterviewDetails(day, monthName, year, events) {
  const panel = document.getElementById("selectedDayEventsPanel");
  const list = document.getElementById("selectedDayEventsList");
  if (!panel || !list) return;

  panel.style.display = "block";
  document.getElementById("selectedDayTitle").textContent = `Interviews on ${day} ${monthName} ${year}:`;

  list.innerHTML = "";
  events.forEach(ev => {
    const item = document.createElement("div");
    item.className = "metric-box";
    item.style.padding = "0.75rem 1rem";
    item.style.marginBottom = "0.5rem";
    item.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <strong style="color:var(--primary);">${ev.company}</strong>
          <span style="font-size:0.85rem; color:var(--text-secondary); margin-left:0.5rem;">• ${ev.round}</span>
        </div>
        <span class="badge badge-blue">${ev.question_count} Qs</span>
      </div>
    `;
    item.style.cursor = "pointer";
    item.addEventListener("click", () => {
      closeModal("calendarModal");
      searchQuery = ev.company.toLowerCase();
      const searchInput = document.getElementById("qbSearchInput");
      if (searchInput) searchInput.value = ev.company;
      applyFilters();
    });
    list.appendChild(item);
  });
}

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
  const favCard = document.getElementById("statCardFavorites");

  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentCategory = pill.getAttribute("data-category") || "All";
      showFavoritesOnly = false;
      favCard?.classList.remove("active-favorite-filter");
      applyFilters();
    });
  });

  // Favorites stat card click handler (toggle on and release off)
  if (favCard) {
    favCard.style.cursor = "pointer";
    favCard.addEventListener("click", () => {
      showFavoritesOnly = !showFavoritesOnly;

      if (showFavoritesOnly) {
        favCard.classList.add("active-favorite-filter");
        pills.forEach(p => p.classList.remove("active"));
        showToast("Filtering bookmarked questions", "info");
      } else {
        // Toggle off / release from favorites: return to All
        favCard.classList.remove("active-favorite-filter");
        currentCategory = "All";
        pills.forEach(p => p.classList.remove("active"));
        const allPill = document.querySelector('.category-pill[data-category="All"]');
        if (allPill) allPill.classList.add("active");
        showToast("Showing all questions", "info");
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
    const isNagarajComp = companyCard.getAttribute("data-is-nagaraj") === "true";
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
        const matchCategory = !isFilteringCategory || 
          (currentCategory.toLowerCase() === "nagaraj's interview" 
            ? (isNagarajComp || qCat === "nagaraj's interview")
            : qCat === currentCategory.toLowerCase());

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
      expandAllBtn.classList.add("active");
      collapseAllBtn?.classList.remove("active");
      showToast("All companies & rounds expanded", "info");
    });
  }

  // Collapse all companies and rounds
  if (collapseAllBtn) {
    collapseAllBtn.addEventListener("click", () => {
      document.querySelectorAll(".company-card").forEach(c => c.classList.remove("expanded"));
      document.querySelectorAll(".round-block").forEach(r => r.classList.remove("expanded"));
      collapseAllBtn.classList.add("active");
      expandAllBtn?.classList.remove("active");
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
      expandAllAnswersBtn.classList.add("active");
      collapseAllAnswersBtn?.classList.remove("active");
      showToast("All answers expanded", "success");
    });
  }

  // Separate button to collapse all answers at once
  if (collapseAllAnswersBtn) {
    collapseAllAnswersBtn.addEventListener("click", () => {
      document.querySelectorAll(".question-item").forEach(q => q.classList.remove("expanded"));
      collapseAllAnswersBtn.classList.add("active");
      expandAllAnswersBtn?.classList.remove("active");
      showToast("All answers collapsed", "info");
    });
  }
}

// Dedicated Copy Handlers for Questions & Answers
window.copyQuestionText = function(qId, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  const qCard = document.getElementById(qId);
  if (!qCard) return;
  const qText = qCard.querySelector(".question-text")?.textContent?.trim() || "";
  if (qText) {
    copyTextToClipboard(qText, "Question copied to clipboard!");
    const btn = event ? (event.currentTarget || event.target.closest("button")) : qCard.querySelector(".copy-q-btn");
    if (btn) {
      const icon = btn.querySelector("i");
      if (icon) {
        const oldClass = icon.className;
        icon.className = "fa-solid fa-check";
        setTimeout(() => { icon.className = oldClass; }, 1500);
      }
    }
  }
};

window.copyAnswerText = function(qId, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  const qCard = document.getElementById(qId);
  if (!qCard) return;
  const aElem = qCard.querySelector(".answer-markdown");
  const aText = aElem?.innerText?.trim() || aElem?.textContent?.trim() || "";
  if (aText) {
    copyTextToClipboard(aText, "Answer copied to clipboard!");
    const btn = event ? (event.currentTarget || event.target.closest("button")) : qCard.querySelector(".copy-ans-btn");
    if (btn) {
      const originalHtml = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
      setTimeout(() => { btn.innerHTML = originalHtml; }, 1500);
    }
  }
};

// Individual Company, Round & Question Accordion Click Handlers
function initQuestionToggles() {
  document.addEventListener("click", (e) => {
    // If clicking on copy button, fav button, or other action buttons, do not toggle accordions
    if (e.target.closest(".action-icon-btn") || e.target.closest(".copy-btn") || e.target.closest(".copy-name-btn") || e.target.closest(".copy-q-btn") || e.target.closest(".copy-ans-btn") || e.target.closest(".fav-btn")) {
      return;
    }

    // Check if user currently has text selected with mouse drag
    const selectedText = window.getSelection().toString();
    if (selectedText && selectedText.trim().length > 0) {
      return;
    }

    // Allow user to freely select company name or round name text without accordion toggle interference
    if (e.target.closest(".company-name") || e.target.closest(".round-name")) {
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
    if (qHeader) {
      const qItem = qHeader.closest(".question-item");
      if (qItem) {
        qItem.classList.toggle("expanded");
      }
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
const initialCalDate = new Date();
let currentCalYear = initialCalDate.getFullYear();
let currentCalMonth = initialCalDate.getMonth();
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
  const now = new Date();
  currentCalYear = now.getFullYear();
  currentCalMonth = now.getMonth();
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

  const monthShort = MONTH_NAMES[month].substring(0, 3);
  const realToday = new Date();
  const isCurrentMonthView = (year === realToday.getFullYear() && month === realToday.getMonth());
  const todayDate = realToday.getDate();

  let todayEvents = [];
  let todayCell = null;
  let fallbackFirstEventCell = null;
  let fallbackFirstEvents = [];
  let fallbackFirstDay = null;

  for (let d = 1; d <= daysInMonth; d++) {
    const dayCell = document.createElement("div");
    dayCell.className = "calendar-day-cell";

    const dayNum = document.createElement("span");
    dayNum.className = "day-number";
    dayNum.textContent = d;
    dayCell.appendChild(dayNum);

    const isThisToday = isCurrentMonthView && (d === todayDate);
    if (isThisToday) {
      dayCell.classList.add("is-today");
      todayCell = dayCell;
    }

    // Look for matching events in calendarEventsData
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

    if (isThisToday) {
      todayEvents = matchingEvents;
    }

    if (matchingEvents.length > 0) {
      dayCell.classList.add("has-interview");
      const badge = document.createElement("div");
      badge.className = "interview-dot-badge";
      badge.textContent = `${matchingEvents.length} Rounds`;
      dayCell.appendChild(badge);

      if (!fallbackFirstEventCell) {
        fallbackFirstEventCell = dayCell;
        fallbackFirstEvents = matchingEvents;
        fallbackFirstDay = d;
      }
    }

    dayCell.addEventListener("click", () => {
      document.querySelectorAll(".calendar-day-cell").forEach(c => c.classList.remove("active-day"));
      dayCell.classList.add("active-day");
      showDayInterviewDetails(d, MONTH_NAMES[month], year, matchingEvents);
    });

    gridElem.appendChild(dayCell);
  }

  // User requirement: By default stay on current date (today)
  if (isCurrentMonthView && todayCell) {
    todayCell.classList.add("active-day");
    showDayInterviewDetails(todayDate, MONTH_NAMES[month], year, todayEvents);
  } else if (fallbackFirstEventCell) {
    fallbackFirstEventCell.classList.add("active-day");
    showDayInterviewDetails(fallbackFirstDay, MONTH_NAMES[month], year, fallbackFirstEvents);
  } else {
    showDayInterviewDetails(1, MONTH_NAMES[month], year, []);
  }
}

function showDayInterviewDetails(day, monthName, year, events) {
  const panel = document.getElementById("selectedDayEventsPanel");
  const list = document.getElementById("selectedDayEventsList");
  const title = document.getElementById("selectedDayTitle");
  if (!panel || !list) return;

  const realToday = new Date();
  const isToday = (year === realToday.getFullYear() && monthName === MONTH_NAMES[realToday.getMonth()] && day === realToday.getDate());

  if (title) {
    title.textContent = `Interviews on ${day} ${monthName} ${year}${isToday ? ' (Today)' : ''}:`;
  }

  list.innerHTML = "";
  if (events && events.length > 0) {
    events.forEach(ev => {
      const card = document.createElement("div");
      card.className = "calendar-event-card";
      card.innerHTML = `
        <div>
          <div class="calendar-event-company">${escapeHtml(ev.company)}</div>
          <div class="calendar-event-round"><i class="fa-regular fa-circle-dot" style="margin-right:0.25rem;"></i>${escapeHtml(ev.round)}</div>
        </div>
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <span class="badge badge-purple" style="font-size:0.75rem;">${ev.question_count} Qs</span>
          <span class="calendar-event-btn"><i class="fa-solid fa-arrow-right"></i> View</span>
        </div>
      `;
      card.title = `Click to filter Question Bank for ${ev.company}`;
      card.addEventListener("click", () => {
        closeModal("calendarModal");
        searchQuery = ev.company.toLowerCase();
        const searchInput = document.getElementById("qbSearchInput");
        if (searchInput) searchInput.value = ev.company;
        applyFilters();
        const firstCard = document.querySelector(".company-card");
        if (firstCard) firstCard.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      list.appendChild(card);
    });
  } else {
    list.innerHTML = `
      <div class="calendar-empty-hint" style="padding: 1.5rem 1rem;">
        <i class="fa-regular fa-calendar" style="font-size:1.6rem; color:var(--text-muted); margin-bottom:0.5rem;"></i>
        <p style="margin:0; font-size:0.9rem; color:var(--text-secondary);">No interview rounds scheduled for ${isToday ? 'today' : 'this date'}.</p>
        <span style="font-size:0.78rem; color:var(--text-muted); margin-top:0.25rem;">Click on any highlighted date (e.g. 3, 9, 17 Sep) to view scheduled rounds.</span>
      </div>
    `;
  }
}


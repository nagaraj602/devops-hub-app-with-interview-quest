/* ==============================================================================
   Question Bank JavaScript: Categorization, Collapse/Expand, Calendar & Favorites
   ============================================================================== */

let currentCategory = "All";
let currentSort = "recent";
let searchQuery = "";
let showFavoritesOnly = false;
let userFavorites = JSON.parse(localStorage.getItem("devops_hub_favorites") || "[]");

// Toggle states and progressive chunking
let isCompaniesExpanded = false;
let userManualCompaniesExpanded = false;
let isAnswersExpanded = false;
const PAGE_CHUNK = 10;
let isChunkLoading = false;
let filterAbortController = null;

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
  initQuestionBank();
});

function initQuestionBank() {
  updateFavoritesCountUI();
  updateFavoriteIconsInDOM();
  initCategoryPills();
  initSearchAndSort();
  initCustomSortDropdown();
  initGlobalAccordions();
  initLoadMore();
  initQuestionToggles();
  initCalendarModal();
  updateCompaniesToggleBtnUI();
  updateAnswersToggleBtnUI();
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
    applyFilters(true);
  }
}

// Category Pills Filtering
function initCategoryPills() {
  const pills = document.querySelectorAll(".category-pill");
  const favCard = document.getElementById("statCardFavorites");

  const urlParams = new URLSearchParams(window.location.search);
  const urlCat = urlParams.get("category");
  if (urlCat) {
    currentCategory = urlCat;
    pills.forEach(p => {
      p.classList.toggle("active", (p.getAttribute("data-category") || "").toLowerCase() === urlCat.toLowerCase());
    });
    if (urlCat.toLowerCase() !== "all") {
      isCompaniesExpanded = true;
    }
  }

  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentCategory = pill.getAttribute("data-category") || "All";
      showFavoritesOnly = false;
      favCard?.classList.remove("active-favorite-filter");

      const isCategoryAll = currentCategory.toLowerCase() === "all";
      if (isCategoryAll) {
        // Returning to Category 'All': restore clean collapsed state by default
        isCompaniesExpanded = false;
        userManualCompaniesExpanded = false;
      } else {
        // Specific category selected: auto-expand all companies and rounds to reveal questions
        isCompaniesExpanded = true;
        userManualCompaniesExpanded = false;
      }
      updateCompaniesToggleBtnUI();

      applyFilters(true);
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
        isCompaniesExpanded = true;
        userManualCompaniesExpanded = false;
      } else {
        // Toggle off / release from favorites: return to All
        favCard.classList.remove("active-favorite-filter");
        currentCategory = "All";
        pills.forEach(p => p.classList.remove("active"));
        const allPill = document.querySelector('.category-pill[data-category="All"]');
        if (allPill) allPill.classList.add("active");
        showToast("Showing all questions", "info");
        isCompaniesExpanded = false;
        userManualCompaniesExpanded = false;
      }
      updateCompaniesToggleBtnUI();
      applyFilters(true);
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
        if (searchQuery) {
          isCompaniesExpanded = true;
          userManualCompaniesExpanded = false;
        } else if (currentCategory.toLowerCase() === "all") {
          isCompaniesExpanded = false;
          userManualCompaniesExpanded = false;
        }
        updateCompaniesToggleBtnUI();
        applyFilters(false);
      }, 250);
    });
  }

  const sortSelect = document.getElementById("qbSortSelect");
  if (sortSelect) {
    sortSelect.addEventListener("change", (e) => {
      currentSort = e.target.value;
      applyFilters(true);
    });
  }
}

// Custom Sort Dropdown Handler (Zero-lag, 100% white theme, no OS black box)
function initCustomSortDropdown() {
  const wrapper = document.getElementById("qbCustomSortWrapper");
  const btn = document.getElementById("qbSortDropdownBtn");
  const menu = document.getElementById("qbSortMenu");
  const label = document.getElementById("qbSortLabel");
  const arrow = document.getElementById("qbSortArrow");
  const hiddenSelect = document.getElementById("qbSortSelect");

  if (!wrapper || !btn || !menu) return;

  const toggleDropdown = (show) => {
    const isOpen = show !== undefined ? show : !wrapper.classList.contains("open");
    wrapper.classList.toggle("open", isOpen);
    menu.style.display = isOpen ? "block" : "none";
    btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
  };

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleDropdown();
  });

  document.addEventListener("click", (e) => {
    if (!wrapper.contains(e.target)) {
      toggleDropdown(false);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && wrapper.classList.contains("open")) {
      toggleDropdown(false);
      btn.focus();
    }
  });

  const options = menu.querySelectorAll(".custom-sort-option");
  options.forEach(opt => {
    opt.addEventListener("click", (e) => {
      e.stopPropagation();
      const val = opt.getAttribute("data-value");
      const optText = opt.querySelector("span")?.textContent || opt.textContent.trim();

      options.forEach(o => o.classList.remove("active"));
      opt.classList.add("active");

      if (label) label.textContent = optText;
      if (hiddenSelect) hiddenSelect.value = val;
      currentSort = val;

      toggleDropdown(false);

      if (arrow) arrow.className = "fa-solid fa-spinner fa-spin custom-sort-arrow";
      applyFilters(true);
    });
  });

  if (hiddenSelect) {
    hiddenSelect.addEventListener("change", (e) => {
      const val = e.target.value;
      currentSort = val;
      const matchingOpt = menu.querySelector(`.custom-sort-option[data-value="${val}"]`);
      if (matchingOpt) {
        options.forEach(o => o.classList.remove("active"));
        matchingOpt.classList.add("active");
        if (label) label.textContent = matchingOpt.querySelector("span")?.textContent || matchingOpt.textContent.trim();
      }
      if (arrow) arrow.className = "fa-solid fa-spinner fa-spin custom-sort-arrow";
      applyFilters(true);
    });
  }
}

function updateFavoriteIconsInDOM() {
  document.querySelectorAll(".fav-btn").forEach(btn => {
    const qId = btn.getAttribute("data-qid");
    const isFav = userFavorites.includes(qId);
    btn.classList.toggle("favorite-active", isFav);
    const icon = btn.querySelector("i");
    if (icon) {
      icon.className = isFav ? "fa-solid fa-star" : "fa-regular fa-star";
    }
    const questionCard = document.getElementById(qId);
    if (questionCard) {
      questionCard.classList.toggle("favorite", isFav);
    }
  });
}

// Main Filter Logic: Category, Search & Favorites via Server Chunking
function applyFilters(showLoading = false) {
  const container = document.getElementById("companyListContainer");
  const emptyState = document.getElementById("qbEmptyState");
  const loadMoreWrap = document.getElementById("qbLoadMoreWrap");
  const arrow = document.getElementById("qbSortArrow");
  if (!container) return;

  if (filterAbortController) {
    filterAbortController.abort();
  }
  filterAbortController = new AbortController();

  if (showLoading) {
    if (emptyState) emptyState.style.display = "none";
    if (loadMoreWrap) loadMoreWrap.style.display = "none";
    container.innerHTML = `
      <div class="qb-loading-card">
        <div class="qb-loading-spinner"></div>
        <div class="qb-loading-title">Loading & Sorting Question Bank...</div>
        <div class="qb-loading-desc">Organizing companies and interview questions</div>
      </div>
    `;
  }

  const isFilteringCategory = currentCategory.toLowerCase() !== "all";
  const hasSearch = Boolean(searchQuery && searchQuery.trim());

  const params = new URLSearchParams({
    offset: "0",
    limit: String(PAGE_CHUNK),
    category: currentCategory,
    search: searchQuery,
    sort_by: currentSort,
    favorites: showFavoritesOnly ? userFavorites.join(",") : "",
    is_companies_expanded: isCompaniesExpanded ? "true" : "false",
    is_answers_expanded: isAnswersExpanded ? "true" : "false"
  });

  fetch(`/api/question-bank/chunk?${params.toString()}`, { signal: filterAbortController.signal })
    .then(res => res.json())
    .then(data => {
      if (arrow) arrow.className = "fa-solid fa-chevron-down custom-sort-arrow";
      if (!data) return;

      if (data.total_matched === 0) {
        container.innerHTML = "";
        if (emptyState) emptyState.style.display = "block";
        if (loadMoreWrap) loadMoreWrap.style.display = "none";
      } else {
        if (emptyState) emptyState.style.display = "none";
        container.innerHTML = data.html;

        if (loadMoreWrap) {
          loadMoreWrap.style.display = data.has_more ? "flex" : "none";
        }

        updateCompaniesToggleBtnUI();
        updateFavoriteIconsInDOM();
      }
    })
    .catch(err => {
      if (err.name !== "AbortError") {
        if (arrow) arrow.className = "fa-solid fa-chevron-down custom-sort-arrow";
        console.error("Filter request error:", err);
      }
    });
}

// Progressive Chunked Reveal: Displays 10 listings at a time via Server Endpoint
function initLoadMore() {
  const loadMoreBtn = document.getElementById("qbLoadMoreBtn");
  if (loadMoreBtn) {
    const handleLoadMore = () => {
      if (isChunkLoading) return;
      isChunkLoading = true;

      const loadMoreSpan = loadMoreBtn.querySelector("span");
      const loadMoreIcon = loadMoreBtn.querySelector("i");
      if (loadMoreSpan) loadMoreSpan.textContent = "Loading...";
      if (loadMoreIcon) loadMoreIcon.className = "fa-solid fa-spinner fa-spin";

      const container = document.getElementById("companyListContainer");
      const currentCards = container ? container.querySelectorAll(".company-card") : [];
      const offset = currentCards.length;

      const params = new URLSearchParams({
        offset: String(offset),
        limit: String(PAGE_CHUNK),
        category: currentCategory,
        search: searchQuery,
        sort_by: currentSort,
        favorites: showFavoritesOnly ? userFavorites.join(",") : "",
        is_companies_expanded: isCompaniesExpanded ? "true" : "false",
        is_answers_expanded: isAnswersExpanded ? "true" : "false"
      });

      fetch(`/api/question-bank/chunk?${params.toString()}`)
        .then(res => res.json())
        .then(data => {
          if (data && data.html && container) {
            container.insertAdjacentHTML("beforeend", data.html);

            const newTotalCards = container.querySelectorAll(".company-card").length;
            const totalMatched = data.total_matched || newTotalCards;

            // Apply active expand states to new elements
            if (isCompaniesExpanded) {
              container.querySelectorAll(".company-card").forEach(c => c.classList.add("expanded"));
              container.querySelectorAll(".round-block").forEach(r => r.classList.add("expanded"));
            }
            if (isAnswersExpanded) {
              container.querySelectorAll(".question-item").forEach(q => q.classList.add("expanded"));
            }

            updateFavoriteIconsInDOM();

            // 4-second notification toast
            showToast(`Loaded ${newTotalCards} of ${totalMatched} companies`, "info", 4000);

            const loadMoreWrap = document.getElementById("qbLoadMoreWrap");
            if (loadMoreWrap) {
              loadMoreWrap.style.display = data.has_more ? "flex" : "none";
            }
          }
        })
        .catch(err => {
          console.error("Error loading company chunk:", err);
          showToast("Failed to load more companies", "error");
        })
        .finally(() => {
          isChunkLoading = false;
          if (loadMoreSpan) loadMoreSpan.textContent = "Load more...";
          if (loadMoreIcon) loadMoreIcon.className = "fa-solid fa-chevron-down";
        });
    };

    loadMoreBtn.addEventListener("click", handleLoadMore);
    loadMoreBtn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleLoadMore();
      }
    });
  }
}

// UI State Updater for Companies Toggle Button
function updateCompaniesToggleBtnUI() {
  const btn = document.getElementById("toggleAllCompaniesBtn");
  const text = document.getElementById("toggleAllCompaniesText");
  const icon = document.getElementById("toggleAllCompaniesIcon");
  if (!btn) return;

  if (isCompaniesExpanded) {
    btn.classList.add("active");
    btn.title = "Collapse all companies & rounds";
    if (text) text.textContent = "Collapse All";
    if (icon) icon.className = "fa-solid fa-down-left-and-up-right-to-center";
  } else {
    btn.classList.remove("active");
    btn.title = "Expand all company & round containers";
    if (text) text.textContent = "Expand All";
    if (icon) icon.className = "fa-solid fa-up-right-and-down-left-from-center";
  }
}

// UI State Updater for Answers Toggle Button
function updateAnswersToggleBtnUI() {
  const btn = document.getElementById("toggleAllAnswersBtn");
  const text = document.getElementById("toggleAllAnswersText");
  const icon = document.getElementById("toggleAllAnswersIcon");
  if (!btn) return;

  if (isAnswersExpanded) {
    btn.classList.add("active");
    btn.title = "Collapse all answers";
    if (text) text.textContent = "Collapse Answers";
    if (icon) icon.className = "fa-solid fa-eye-slash";
  } else {
    btn.classList.remove("active");
    btn.title = "Expand answers for all questions";
    if (text) text.textContent = "Expand Answers";
    if (icon) icon.className = "fa-solid fa-eye";
  }
}

// Global Accordion Expand / Collapse Buttons (2 buttons with 4 functionalities)
function initGlobalAccordions() {
  const toggleCompaniesBtn = document.getElementById("toggleAllCompaniesBtn");
  const toggleAnswersBtn = document.getElementById("toggleAllAnswersBtn");

  // Button 1: Toggle Expand All / Collapse All Companies & Rounds
  if (toggleCompaniesBtn) {
    toggleCompaniesBtn.addEventListener("click", () => {
      isCompaniesExpanded = !isCompaniesExpanded;
      userManualCompaniesExpanded = isCompaniesExpanded;
      if (isCompaniesExpanded) {
        // Expand visible companies and rounds
        document.querySelectorAll(".company-card").forEach(c => {
          if (c.style.display !== "none") c.classList.add("expanded");
        });
        document.querySelectorAll(".round-block").forEach(r => {
          if (r.style.display !== "none") r.classList.add("expanded");
        });
        showToast("All companies & rounds expanded", "info");
      } else {
        // Collapse all companies and rounds
        document.querySelectorAll(".company-card").forEach(c => c.classList.remove("expanded"));
        document.querySelectorAll(".round-block").forEach(r => r.classList.remove("expanded"));
        // If answers were also expanded, collapse them and reset answers toggle
        if (isAnswersExpanded) {
          document.querySelectorAll(".question-item").forEach(q => q.classList.remove("expanded"));
          isAnswersExpanded = false;
          updateAnswersToggleBtnUI();
        }
        showToast("All companies & rounds collapsed", "info");
      }
      updateCompaniesToggleBtnUI();
    });
  }

  // Button 2: Toggle Expand Answers / Collapse Answers
  if (toggleAnswersBtn) {
    toggleAnswersBtn.addEventListener("click", () => {
      isAnswersExpanded = !isAnswersExpanded;
      if (isAnswersExpanded) {
        // Expand answers for all visible questions, and also expand company & round containers so answers are immediately visible
        document.querySelectorAll(".company-card").forEach(c => {
          if (c.style.display !== "none") c.classList.add("expanded");
        });
        document.querySelectorAll(".round-block").forEach(r => {
          if (r.style.display !== "none") r.classList.add("expanded");
        });
        document.querySelectorAll(".question-item").forEach(q => {
          if (q.style.display !== "none") q.classList.add("expanded");
        });
        // Reflect that companies are now expanded
        isCompaniesExpanded = true;
        updateCompaniesToggleBtnUI();
        showToast("All answers expanded", "success");
      } else {
        // Collapse all answers
        document.querySelectorAll(".question-item").forEach(q => q.classList.remove("expanded"));
        showToast("All answers collapsed", "info");
      }
      updateAnswersToggleBtnUI();
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

const MONTH_MAP = {
  jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
  jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11
};

// Robust date key parser: matches 23-Aug-2026, 17-08-2026 03:49 PM, 9-Sep-2026, 03-09-2026, etc.
function parseCalendarDateKey(key) {
  if (!key || key === "N/A") return null;
  const match = String(key).trim().match(/^(\d{1,2})[-/]([A-Za-z]+|\d{1,2})[-/](\d{4})/);
  if (!match) return null;
  const d = parseInt(match[1], 10);
  const mVal = match[2].toLowerCase();
  const y = parseInt(match[3], 10);
  let mIdx = -1;
  if (/^\d+$/.test(mVal)) {
    mIdx = parseInt(mVal, 10) - 1;
  } else {
    const prefix = mVal.substring(0, 3);
    mIdx = MONTH_MAP[prefix] !== undefined ? MONTH_MAP[prefix] : -1;
  }
  if (mIdx < 0 || mIdx > 11) return null;
  return { day: d, month: mIdx, year: y };
}

function dateKeyMatches(key, d, month, year) {
  const parsed = parseCalendarDateKey(key);
  if (!parsed) return false;
  return parsed.day === d && parsed.month === month && parsed.year === year;
}

// Opens the specific company and round directly in the Question Bank list
function openRoundInQuestionBank(companyName, roundName, eventDate) {
  closeModal("calendarModal");

  // 1. Reset category filter to "All" so all companies and rounds are searchable
  currentCategory = "All";
  document.querySelectorAll(".category-pill").forEach(p => {
    p.classList.toggle("active", p.dataset.category === "All");
  });

  // 2. Clear search input and search query
  const searchInput = document.getElementById("qbSearchInput");
  if (searchInput) searchInput.value = "";
  searchQuery = "";

  // 3. Remove favorites filter if active
  showFavoritesOnly = false;
  const favDock = document.getElementById("statCardFavorites");
  if (favDock) favDock.classList.remove("active-favorite-filter");

  // 4. Locate company helper
  const findCompanyInDOM = () => {
    const compCards = Array.from(document.querySelectorAll(".company-card"));
    const query = (companyName || "").trim().toLowerCase();
    const cleanEventDate = (eventDate || "").trim().split(" ")[0].toLowerCase();

    let foundCard = null;
    if (cleanEventDate) {
      foundCard = compCards.find(c => {
        const cName = (c.dataset.companyName || "").trim().toLowerCase();
        const cDate = (c.dataset.companyDate || "").trim().toLowerCase();
        const nameMatch = cName === query || cName.includes(query) || query.includes(cName);
        const dateMatch = cDate.includes(cleanEventDate) || cleanEventDate.includes(cDate);
        return nameMatch && dateMatch;
      });
    }
    if (!foundCard) {
      foundCard = compCards.find(c => {
        const cName = (c.dataset.companyName || "").trim().toLowerCase();
        return cName === query || cName.includes(query) || query.includes(cName);
      });
    }
    return foundCard;
  };

  const expandAndScroll = (targetCard) => {
    targetCard.style.display = "";
    targetCard.classList.add("expanded");

    const cleanEventDate = (eventDate || "").trim().split(" ")[0].toLowerCase();
    const roundBlocks = Array.from(targetCard.querySelectorAll(".round-block"));
    const qRound = (roundName || "").trim().toLowerCase();
    const normQ = qRound.replace(/^level\s*/, "l");

    let targetRound = roundBlocks.find(r => {
      const rName = (r.dataset.roundName || "").trim().toLowerCase();
      const rDate = (r.dataset.roundDate || "").trim().toLowerCase();
      const nameMatch = rName === qRound;
      const dateMatch = !cleanEventDate || rDate.includes(cleanEventDate) || cleanEventDate.includes(rDate);
      return nameMatch && dateMatch;
    });
    if (!targetRound) {
      targetRound = roundBlocks.find(r => (r.dataset.roundName || "").trim().toLowerCase() === qRound);
    }
    if (!targetRound) {
      targetRound = roundBlocks.find(r => {
        const normR = (r.dataset.roundName || "").trim().toLowerCase().replace(/^level\s*/, "l");
        return normR === normQ || normR.includes(normQ) || normQ.includes(normR);
      });
    }
    if (!targetRound && roundBlocks.length > 0) {
      targetRound = roundBlocks[0];
    }

    if (targetRound) {
      targetRound.classList.add("expanded");
      setTimeout(() => {
        targetRound.scrollIntoView({ behavior: "smooth", block: "center" });
        targetRound.classList.add("highlight-pulse");
        setTimeout(() => {
          targetRound.classList.remove("highlight-pulse");
        }, 2200);
      }, 150);
      showToast(`Opened ${companyName} • ${roundName}`, "success");
    } else {
      setTimeout(() => {
        targetCard.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 150);
      showToast(`Opened ${companyName}`, "info");
    }
  };

  let targetCard = findCompanyInDOM();
  if (targetCard) {
    expandAndScroll(targetCard);
    return;
  }

  // If target company card is not in current DOM chunk, fetch it directly from server
  fetch(`/api/question-bank/chunk?target_company=${encodeURIComponent(companyName)}&offset=0&limit=10`)
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById("companyListContainer");
      if (data && data.html && container) {
        const bannerHtml = `
          <div class="calendar-target-notice" style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:var(--radius-md); padding:0.65rem 1.1rem; margin-bottom:1rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
            <span style="font-size:0.86rem; color:#1e40af; font-weight:600;">
              <i class="fa-regular fa-calendar-check" style="margin-right:0.35rem; color:var(--primary);"></i>
              Showing interview for <strong>${escapeHtml(companyName)}</strong> from Calendar
            </span>
            <button type="button" class="btn btn-secondary btn-sm" onclick="resetToAllCompanies()" style="font-size:0.78rem; padding:0.25rem 0.65rem;">
              <i class="fa-solid fa-list"></i> View All Companies
            </button>
          </div>
        `;
        container.innerHTML = bannerHtml + data.html;
        const loadMoreWrap = document.getElementById("qbLoadMoreWrap");
        if (loadMoreWrap) {
          loadMoreWrap.style.display = data.has_more ? "flex" : "none";
        }
        updateFavoriteIconsInDOM();
        let loadedTarget = findCompanyInDOM();
        if (!loadedTarget) {
          const compCards = Array.from(container.querySelectorAll(".company-card"));
          if (compCards.length > 0) loadedTarget = compCards[0];
        }
        if (loadedTarget) {
          expandAndScroll(loadedTarget);
        } else {
          showToast(`Company "${companyName}" not found in list`, "warning");
        }
      } else {
        showToast(`Company "${companyName}" not found in list`, "warning");
      }
    })
    .catch(err => {
      console.error("Error opening round:", err);
      showToast(`Company "${companyName}" not found in list`, "warning");
    });
}

window.resetToAllCompanies = function() {
  currentCategory = "All";
  searchQuery = "";
  isCompaniesExpanded = false;
  userManualCompaniesExpanded = false;
  updateCompaniesToggleBtnUI();
  const sInput = document.getElementById("qbSearchInput");
  if (sInput) sInput.value = "";
  document.querySelectorAll(".category-pill").forEach(p => {
    p.classList.toggle("active", p.dataset.category === "All");
  });
  applyFilters(true);
};

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

    // Look for matching events in calendarEventsData with exact parsed matching
    const matchingEvents = [];
    for (const [dateStr, events] of Object.entries(calendarEventsData)) {
      if (dateKeyMatches(dateStr, d, month, year)) {
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
      badge.textContent = `${matchingEvents.length} Round${matchingEvents.length > 1 ? 's' : ''}`;
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
  const subtitle = document.getElementById("selectedDaySubtitle");
  if (!panel || !list) return;

  const realToday = new Date();
  const isToday = (year === realToday.getFullYear() && monthName === MONTH_NAMES[realToday.getMonth()] && day === realToday.getDate());

  if (title) {
    title.textContent = `Interviews on ${day} ${monthName} ${year}${isToday ? ' (Today)' : ''}`;
  }
  if (subtitle) {
    if (events && events.length > 0) {
      subtitle.textContent = `${events.length} Round${events.length > 1 ? 's' : ''} • Click to open in Question Bank list`;
    } else {
      subtitle.textContent = `No scheduled interviews on this date`;
    }
  }

  list.innerHTML = "";
  if (events && events.length > 0) {
    events.forEach(ev => {
      const card = document.createElement("div");
      card.className = "calendar-event-card";
      card.innerHTML = `
        <div style="flex: 1; min-width: 0;">
          <div class="calendar-event-company">${escapeHtml(ev.company)}</div>
          <div class="calendar-event-round"><i class="fa-regular fa-circle-dot" style="margin-right:0.25rem;"></i>${escapeHtml(ev.round)}</div>
          <div style="font-size:0.72rem; color:var(--text-muted); margin-top:0.2rem;"><i class="fa-regular fa-clock" style="margin-right:0.25rem;"></i>${escapeHtml(ev.date || `${day}-${monthName}-${year}`)}</div>
        </div>
        <div style="display:flex; align-items:center; gap:0.5rem; flex-shrink:0;">
          <span class="badge badge-purple" style="font-size:0.75rem;">${ev.question_count} Qs</span>
          <span class="calendar-event-btn"><i class="fa-solid fa-arrow-right"></i> Open Round</span>
        </div>
      `;
      card.title = `Click to open ${ev.company} (${ev.round}) directly in Question Bank list`;
      card.addEventListener("click", () => {
        openRoundInQuestionBank(ev.company, ev.round, ev.date);
      });
      list.appendChild(card);
    });
  } else {
    list.innerHTML = `
      <div class="calendar-empty-hint" style="padding: 1.5rem 1rem;">
        <i class="fa-regular fa-calendar" style="font-size:1.6rem; color:var(--text-muted); margin-bottom:0.5rem;"></i>
        <p style="margin:0; font-size:0.9rem; color:var(--text-secondary);">No interview rounds scheduled for ${isToday ? 'today' : 'this date'}.</p>
        <span style="font-size:0.78rem; color:var(--text-muted); margin-top:0.25rem;">Click on any highlighted date (e.g. 3, 5, 9, 17 Sep) to view scheduled rounds.</span>
      </div>
    `;
  }
}


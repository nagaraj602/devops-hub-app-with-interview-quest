/* ==============================================================================
   QA Questions JavaScript: Filtering, Search, Progressive Chunking & Bookmarks
   ============================================================================== */

let currentInstructor = "All";
let currentQASort = "default";
let qaSearchQuery = "";
let showQAFavoritesOnly = false;
let userQAFavorites = JSON.parse(localStorage.getItem("devops_hub_qa_favorites") || "[]");

let isQASessionsExpanded = false;
let isQAAnswersExpanded = false;
const QA_PAGE_CHUNK = 2; // 2 instructors per chunk for fast, low-memory rendering
let currentQAOffset = 0;
let isQAChunkLoading = false;
let qaFilterAbortController = null;

function escapeQAHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
  initQAQuestions();
});

function initQAQuestions() {
  const container = document.getElementById("qaListContainer");
  if (container) {
    const initialAttr = parseInt(container.getAttribute("data-initial-count"), 10);
    const existingCards = container.querySelectorAll(".qa-instructor-card").length;
    currentQAOffset = !isNaN(initialAttr) ? initialAttr : existingCards;
  }
  updateQAFavoritesCountUI();
  updateQAFavoriteIconsInDOM();
  initQAPills();
  initQASearchAndSort();
  initQACustomSortDropdown();
  initQAGlobalAccordions();
  initQALoadMore();
  updateQASessionsToggleBtnUI();
  updateQAAnswersToggleBtnUI();
}

// Bookmarks / Favorites Manager
function updateQAFavoritesCountUI() {
  const favCountElem = document.getElementById("qaStatFavoritesCount");
  if (favCountElem) {
    favCountElem.textContent = userQAFavorites.length;
  }
}

function toggleQAFavorite(qId, e) {
  if (e) e.stopPropagation();
  const idx = userQAFavorites.indexOf(qId);
  if (idx > -1) {
    userQAFavorites.splice(idx, 1);
    showToast("Removed from bookmarks", "info");
  } else {
    userQAFavorites.push(qId);
    showToast("Question bookmarked!", "success");
  }
  localStorage.setItem("devops_hub_qa_favorites", JSON.stringify(userQAFavorites));
  updateQAFavoritesCountUI();

  // Update icons
  document.querySelectorAll(`.qa-fav-btn[data-qid="${qId}"]`).forEach(btn => {
    btn.classList.toggle("favorite-active", userQAFavorites.includes(qId));
    const icon = btn.querySelector("i");
    if (icon) {
      icon.className = userQAFavorites.includes(qId) ? "fa-solid fa-star" : "fa-regular fa-star";
    }
  });

  const questionCard = document.getElementById(qId);
  if (questionCard) {
    questionCard.classList.toggle("favorite", userQAFavorites.includes(qId));
  }

  if (showQAFavoritesOnly) {
    applyQAFilters(true);
  }
}

function updateQAFavoriteIconsInDOM() {
  document.querySelectorAll(".qa-fav-btn").forEach(btn => {
    const qId = btn.getAttribute("data-qid");
    const isFav = userQAFavorites.includes(qId);
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

// Instructor Pills Filtering
function initQAPills() {
  const pills = document.querySelectorAll(".qa-pill");
  const favCard = document.getElementById("qaStatCardFavorites");

  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      const instructor = pill.getAttribute("data-instructor");
      if (currentInstructor === instructor && !showQAFavoritesOnly) return;

      currentInstructor = instructor;
      showQAFavoritesOnly = false;

      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      if (favCard) favCard.classList.remove("active");

      applyQAFilters(true);
    });
  });

  if (favCard) {
    favCard.addEventListener("click", () => {
      showQAFavoritesOnly = !showQAFavoritesOnly;
      favCard.classList.toggle("active", showQAFavoritesOnly);

      if (showQAFavoritesOnly) {
        pills.forEach(p => p.classList.remove("active"));
        if (userQAFavorites.length === 0) {
          showToast("No bookmarked questions yet. Click the star icon to save questions.", "info");
        }
      } else {
        const defaultPill = document.querySelector(`.qa-pill[data-instructor="${currentInstructor}"]`) || document.querySelector('.qa-pill[data-instructor="All"]');
        if (defaultPill) defaultPill.classList.add("active");
      }

      applyQAFilters(true);
    });
  }
}

// Search and Sort Initialization
function initQASearchAndSort() {
  const searchInput = document.getElementById("qaSearchInput");
  if (!searchInput) return;

  let debounceTimer;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      qaSearchQuery = e.target.value.trim();
      applyQAFilters(true);
    }, 250);
  });
}

function initQACustomSortDropdown() {
  const wrapper = document.getElementById("qaCustomSortWrapper");
  const btn = document.getElementById("qaSortDropdownBtn");
  const menu = document.getElementById("qaSortMenu");
  const label = document.getElementById("qaSortLabel");
  const arrow = document.getElementById("qaSortArrow");
  const hiddenSelect = document.getElementById("qaSortSelect");
  if (!wrapper || !btn || !menu) return;

  const toggleDropdown = (open) => {
    const isOpen = open !== undefined ? open : menu.style.display === "none";
    menu.style.display = isOpen ? "flex" : "none";
    btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    wrapper.classList.toggle("open", isOpen);
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
      currentQASort = val;

      toggleDropdown(false);
      applyQAFilters(true);
    });
  });
}

// Global Accordions (Expand/Collapse All)
function initQAGlobalAccordions() {
  const toggleSessionsBtn = document.getElementById("toggleAllQASessionsBtn");
  const toggleAnswersBtn = document.getElementById("toggleAllQAAnswersBtn");

  if (toggleSessionsBtn) {
    toggleSessionsBtn.addEventListener("click", () => {
      isQASessionsExpanded = !isQASessionsExpanded;
      updateQASessionsToggleBtnUI();

      document.querySelectorAll(".qa-instructor-card").forEach(c => {
        c.classList.toggle("expanded", isQASessionsExpanded);
      });
      document.querySelectorAll(".qa-session-block").forEach(b => {
        b.classList.toggle("expanded", isQASessionsExpanded);
      });
    });
  }

  if (toggleAnswersBtn) {
    toggleAnswersBtn.addEventListener("click", () => {
      isQAAnswersExpanded = !isQAAnswersExpanded;
      updateQAAnswersToggleBtnUI();

      document.querySelectorAll('.qa-question-item[data-has-answer="true"]').forEach(q => {
        q.classList.toggle("expanded", isQAAnswersExpanded);
      });
    });
  }

  // Delegated click for instructor headers & session headers
  const container = document.getElementById("qaListContainer");
  if (container) {
    container.addEventListener("click", (e) => {
      // 1. Instructor Header Click
      const instHeader = e.target.closest(".qa-instructor-header");
      if (instHeader && !e.target.closest("button") && !e.target.closest("a")) {
        const card = instHeader.closest(".qa-instructor-card");
        if (card) {
          card.classList.toggle("expanded");
        }
        return;
      }

      // 2. Session Header Click
      const sessHeader = e.target.closest(".qa-session-header");
      if (sessHeader && !e.target.closest("button") && !e.target.closest("a")) {
        const sessBlock = sessHeader.closest(".qa-session-block");
        if (sessBlock) {
          sessBlock.classList.toggle("expanded");
        }
        return;
      }

      // 3. Question Item Click (Toggle Answer Drawer if has answer)
      const qHeader = e.target.closest(".qa-question-header");
      if (qHeader && !e.target.closest("button") && !e.target.closest("a")) {
        const qItem = qHeader.closest('.qa-question-item[data-has-answer="true"]');
        if (qItem) {
          qItem.classList.toggle("expanded");
        }
      }
    });
  }
}

function updateQASessionsToggleBtnUI() {
  const btn = document.getElementById("toggleAllQASessionsBtn");
  const icon = document.getElementById("toggleAllQASessionsIcon");
  const text = document.getElementById("toggleAllQASessionsText");
  if (!btn) return;

  btn.classList.toggle("active", isQASessionsExpanded);
  if (icon) {
    icon.className = isQASessionsExpanded
      ? "fa-solid fa-down-left-and-up-right-to-center"
      : "fa-solid fa-up-right-and-down-left-from-center";
  }
  if (text) {
    text.textContent = isQASessionsExpanded ? "Collapse Sessions" : "Expand Sessions";
  }
}

function updateQAAnswersToggleBtnUI() {
  const btn = document.getElementById("toggleAllQAAnswersBtn");
  const icon = document.getElementById("toggleAllQAAnswersIcon");
  const text = document.getElementById("toggleAllQAAnswersText");
  if (!btn) return;

  btn.classList.toggle("active", isQAAnswersExpanded);
  if (icon) {
    icon.className = isQAAnswersExpanded ? "fa-solid fa-eye-slash" : "fa-solid fa-eye";
  }
  if (text) {
    text.textContent = isQAAnswersExpanded ? "Collapse Answers" : "Expand Answers";
  }
}

// Server-side Chunking & Filtering
function applyQAFilters(showLoading = false) {
  const container = document.getElementById("qaListContainer");
  const emptyState = document.getElementById("qaEmptyState");
  const loadMoreWrap = document.getElementById("qaLoadMoreWrap");
  if (!container) return;

  if (qaFilterAbortController) {
    qaFilterAbortController.abort();
  }
  qaFilterAbortController = new AbortController();

  if (showLoading) {
    if (emptyState) emptyState.style.display = "none";
    if (loadMoreWrap) loadMoreWrap.style.display = "none";
    container.style.opacity = "0.55";
  }

  const isFilteringInstructor = currentInstructor.toLowerCase() !== "all";
  const hasSearch = Boolean(qaSearchQuery && qaSearchQuery.trim());
  const effectiveLimit = isFilteringInstructor ? "10" : String(QA_PAGE_CHUNK);

  const params = new URLSearchParams({
    offset: "0",
    limit: effectiveLimit,
    instructor: currentInstructor,
    search: qaSearchQuery,
    sort_by: currentQASort,
    favorites: showQAFavoritesOnly ? userQAFavorites.join(",") : "",
    is_answers_expanded: isQAAnswersExpanded ? "true" : "false"
  });

  if (isQASessionsExpanded || isFilteringInstructor || hasSearch) {
    params.set("is_sessions_expanded", "true");
  }

  fetch(`/api/qa-questions/chunk?${params.toString()}`, {
    signal: qaFilterAbortController.signal
  })
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      container.style.opacity = "1";
      container.innerHTML = data.html;
      currentQAOffset = data.count;

      if (data.total_matched === 0) {
        if (emptyState) {
          emptyState.style.display = "block";
          const title = document.getElementById("qaEmptyTitle");
          const desc = document.getElementById("qaEmptyDesc");
          if (showQAFavoritesOnly) {
            if (title) title.textContent = "No Bookmarked Questions";
            if (desc) desc.textContent = "You have not bookmarked any QA questions yet. Click the star icon on any question to bookmark it.";
          } else {
            if (title) title.textContent = "No QA Questions Found";
            if (desc) desc.textContent = `No questions found matching "${escapeQAHtml(qaSearchQuery)}". Try broadening your search or resetting filters.`;
          }
        }
        if (loadMoreWrap) loadMoreWrap.style.display = "none";
      } else {
        if (emptyState) emptyState.style.display = "none";
        if (loadMoreWrap) {
          loadMoreWrap.style.display = data.has_more ? "block" : "none";
        }
      }

      updateQAFavoriteIconsInDOM();
    })
    .catch(err => {
      if (err.name !== "AbortError") {
        container.style.opacity = "1";
        console.error("Error loading QA chunk:", err);
      }
    });
}

function loadNextQAChunk() {
  if (isQAChunkLoading) return;
  const loadMoreBtn = document.getElementById("qaLoadMoreBtn");
  const loadingIndicator = document.getElementById("qaLoadingIndicator");
  const container = document.getElementById("qaListContainer");
  const loadMoreWrap = document.getElementById("qaLoadMoreWrap");
  if (!container) return;

  isQAChunkLoading = true;
  if (loadMoreBtn) loadMoreBtn.style.display = "none";
  if (loadingIndicator) loadingIndicator.style.display = "flex";

  const isFilteringInstructor = currentInstructor.toLowerCase() !== "all";
  const hasSearch = Boolean(qaSearchQuery && qaSearchQuery.trim());

  const params = new URLSearchParams({
    offset: String(currentQAOffset),
    limit: String(QA_PAGE_CHUNK),
    instructor: currentInstructor,
    search: qaSearchQuery,
    sort_by: currentQASort,
    favorites: showQAFavoritesOnly ? userQAFavorites.join(",") : "",
    is_answers_expanded: isQAAnswersExpanded ? "true" : "false"
  });

  if (isQASessionsExpanded || isFilteringInstructor || hasSearch) {
    params.set("is_sessions_expanded", "true");
  }

  fetch(`/api/qa-questions/chunk?${params.toString()}`)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      // Parse HTML to avoid appending duplicates if cards already exist
      const temp = document.createElement("div");
      temp.innerHTML = data.html;
      const newCards = temp.querySelectorAll(".qa-instructor-card");
      newCards.forEach(card => {
        if (!card.id || !document.getElementById(card.id)) {
          container.appendChild(card);
        }
      });
      currentQAOffset += data.count;
      isQAChunkLoading = false;

      if (loadingIndicator) loadingIndicator.style.display = "none";
      if (loadMoreBtn) loadMoreBtn.style.display = "inline-flex";

      if (loadMoreWrap) {
        loadMoreWrap.style.display = data.has_more ? "block" : "none";
      }

      updateQAFavoriteIconsInDOM();
    })
    .catch(err => {
      isQAChunkLoading = false;
      if (loadingIndicator) loadingIndicator.style.display = "none";
      if (loadMoreBtn) loadMoreBtn.style.display = "inline-flex";
      console.error("Error loading next QA chunk:", err);
    });
}

function initQALoadMore() {
  const loadMoreWrap = document.getElementById("qaLoadMoreWrap");
  if (!loadMoreWrap) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !isQAChunkLoading && loadMoreWrap.style.display !== "none") {
        loadNextQAChunk();
      }
    });
  }, { rootMargin: "300px" });

  observer.observe(loadMoreWrap);
}

function resetQAFilters() {
  currentInstructor = "All";
  qaSearchQuery = "";
  showQAFavoritesOnly = false;
  currentQASort = "default";

  const searchInput = document.getElementById("qaSearchInput");
  if (searchInput) searchInput.value = "";

  const pills = document.querySelectorAll(".qa-pill");
  pills.forEach(p => {
    p.classList.toggle("active", p.getAttribute("data-instructor") === "All");
  });

  const favCard = document.getElementById("qaStatCardFavorites");
  if (favCard) favCard.classList.remove("active");

  const sortLabel = document.getElementById("qaSortLabel");
  if (sortLabel) sortLabel.textContent = "Sort: Instructor Order";

  applyQAFilters(true);
}

// Copy Actions & Toast Feedback
function copyQAQuestionText(qId, e) {
  if (e) e.stopPropagation();
  const qItem = document.getElementById(qId);
  if (!qItem) return;

  const textElem = qItem.querySelector(".qa-question-text");
  if (!textElem) return;

  const text = textElem.textContent.trim();
  navigator.clipboard.writeText(text).then(() => {
    showToast("Question copied to clipboard!", "success");
  }).catch(() => {
    showToast("Could not copy question", "error");
  });
}

function copyQAAnswerText(qId, e) {
  if (e) e.stopPropagation();
  const qItem = document.getElementById(qId);
  if (!qItem) return;

  const ansElem = qItem.querySelector(".qa-answer-markdown");
  if (!ansElem) return;

  const text = ansElem.innerText.trim();
  navigator.clipboard.writeText(text).then(() => {
    showToast("Answer copied to clipboard!", "success");
  }).catch(() => {
    showToast("Could not copy answer", "error");
  });
}

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.style.cssText = `
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: #1e293b;
    color: #ffffff;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    font-size: 0.88rem;
    margin-bottom: 0.5rem;
    animation: fadeIn 0.2s ease-out;
  `;

  let iconClass = "fa-solid fa-circle-info";
  if (type === "success") iconClass = "fa-solid fa-circle-check";
  if (type === "error") iconClass = "fa-solid fa-triangle-exclamation";

  toast.innerHTML = `<i class="${iconClass}" style="color:${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#38bdf8'};"></i><span>${escapeQAHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.2s ease";
    setTimeout(() => toast.remove(), 200);
  }, 2600);
}

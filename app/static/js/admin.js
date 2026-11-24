/* ==============================================================================
   Admin Portal JavaScript: Page Visibility, Nagaraj's Interview Activity & Schedules
   Version: 2.3.0 (Compact Modern UI, Indian Standard Date DD-Mon-YYYY)
   ============================================================================== */

/* Helper: Format date string to Indian Standard DD-Mon-YYYY (e.g. 24-Nov-2026) */
function formatIndianDate(dateStr) {
  if (!dateStr) return "";
  const str = String(dateStr).trim();
  if (/^\d{1,2}-[A-Za-z]{3}-\d{4}$/.test(str)) return str;
  const parts = str.split("-");
  if (parts.length === 3 && parts[0].length === 4) {
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10);
    const d = parseInt(parts[2], 10);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    if (m >= 1 && m <= 12) {
      const dd = d < 10 ? `0${d}` : `${d}`;
      return `${dd}-${months[m - 1]}-${y}`;
    }
  }
  const dt = new Date(str);
  if (!isNaN(dt.getTime())) {
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const dd = dt.getDate() < 10 ? `0${dt.getDate()}` : `${dt.getDate()}`;
    return `${dd}-${months[dt.getMonth()]}-${dt.getFullYear()}`;
  }
  return str;
}

/* Global State */
let hubState = {
  schedules: [],
  companies: [],
  rounds: [],
  weeklyData: null,
  monthlyData: null,
  activeEmails: [],
  activeScreenshots: [],
  currentWeekDate: null,
  currentMonthStr: null,
  activeView: "week", // 'week' or 'month'
  activeFilterDate: null
};
window.hubState = hubState;

function bootstrapAdminPortal() {
  initAdminTabs();
  initAdminToggles();
  initAdminAuthForm();
  initAdminLogout();
  initInterviewActivityHub();
}

/* ==============================================================================
   1. Tab Navigation
   ============================================================================== */
function initAdminTabs() {
  const tabBtns = document.querySelectorAll(".admin-tab-btn");
  const tabPanes = document.querySelectorAll(".admin-tab-pane");

  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");

      tabBtns.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
      }

      // Update URL query param without full page refresh
      const url = new URL(window.location);
      url.searchParams.set("tab", targetId === "tab-page-publisher" ? "visibility" : "interviews");
      window.history.replaceState({}, "", url);
    });
  });
}

/* ==============================================================================
   2. Interview Activity Hub & Dashboard
   ============================================================================== */

function initInterviewActivityHub() {
  // Read embedded JSON data if present for zero-latency instant startup
  readInitialEmbeddedData();

  initReportDropdown();
  initGraphViewSwitcher();
  initWeeklyGraphControls();
  initMonthlyGraphControls();
  initClearFilterBtn();
  initCompanyRowsAccordion();
  initReorderRoundsModal();
  initCompanySearch();
  initScheduleModal();
  initQuickStatusModal();
  initScreenshotViewerModal();
  initEmailsViewerModal();
  initTranscriptViewerModal();
  initQuickYoutubeModal();

  // If monthly view was pre-loaded, render its initial calendar matrix
  if (hubState.monthlyData) {
    renderMonthMatrix(hubState.monthlyData);
  }
}

function readInitialEmbeddedData() {
  const initEl = document.getElementById("hub-init-data");
  if (!initEl) return;
  try {
    const raw = initEl.textContent.trim();
    if (raw) {
      const data = JSON.parse(raw);
      hubState.schedules = data.schedules || [];
      hubState.companies = data.companies || [];
      hubState.rounds = data.rounds || [];
      hubState.weeklyData = data.weekly || null;
      hubState.monthlyData = data.monthly || null;
      if (data.weekly) hubState.currentWeekDate = data.weekly.week_start;
      if (data.monthly) hubState.currentMonthStr = data.monthly.month_str;
      updateDatalists(hubState.companies, hubState.rounds);
    }
  } catch (err) {
    console.warn("Could not parse embedded hub data:", err);
  }
}

/* Dropdown Menu */
function initReportDropdown() {
  const btn = document.getElementById("btnReportDropdown");
  const menu = document.getElementById("reportDropdownMenu");
  if (!btn || !menu) return;

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.classList.toggle("show");
  });

  document.addEventListener("click", () => {
    menu.classList.remove("show");
  });
}

function updateDatalists(companies, rounds) {
  const compList = document.getElementById("companyDatalist");
  if (compList && companies) {
    compList.innerHTML = companies.map(c => `<option value="${escapeHtml(c.name)}"></option>`).join("");
  }
  const roundList = document.getElementById("roundDatalist");
  if (roundList && rounds) {
    roundList.innerHTML = rounds.map(r => `<option value="${escapeHtml(r)}"></option>`).join("");
  }
}

/* ==============================================================================
   3. View Switcher (Week vs Month)
   ============================================================================== */
function initGraphViewSwitcher() {
  const btnWeek = document.getElementById("btnViewWeek");
  const btnMonth = document.getElementById("btnViewMonth");

  if (btnWeek) {
    btnWeek.addEventListener("click", () => window.switchGraphView("week"));
  }

  if (btnMonth) {
    btnMonth.addEventListener("click", () => window.switchGraphView("month"));
  }
}

function switchGraphView(view) {
  const btnWeek = document.getElementById("btnViewWeek");
  const btnMonth = document.getElementById("btnViewMonth");
  const weekView = document.getElementById("weekActivityView");
  const monthView = document.getElementById("monthActivityView");
  const weekNav = document.getElementById("weekNavControls");
  const monthNav = document.getElementById("monthNavControls");
  const mainTitle = document.getElementById("activityGraphMainTitle");

  if (view === "month") {
    hubState.activeView = "month";
    if (btnMonth) btnMonth.classList.add("active");
    if (btnWeek) btnWeek.classList.remove("active");

    if (weekView) {
      weekView.style.display = "none";
      weekView.classList.remove("active");
    }
    if (monthView) {
      monthView.style.display = "block";
      monthView.classList.add("active");
    }

    if (weekNav) weekNav.style.display = "none";
    if (monthNav) monthNav.style.display = "flex";

    if (mainTitle) mainTitle.textContent = "Monthly Interview Calendar";

    if (hubState.monthlyData) {
      renderMonthMatrix(hubState.monthlyData);
    } else {
      fetchMonthlyData(hubState.currentMonthStr);
    }
  } else {
    hubState.activeView = "week";
    if (btnWeek) btnWeek.classList.add("active");
    if (btnMonth) btnMonth.classList.remove("active");

    if (weekView) {
      weekView.style.display = "block";
      weekView.classList.add("active");
    }
    if (monthView) {
      monthView.style.display = "none";
      monthView.classList.remove("active");
    }

    if (weekNav) weekNav.style.display = "flex";
    if (monthNav) monthNav.style.display = "none";

    if (mainTitle) mainTitle.textContent = "Weekly Interview Dynamics";

    const label = document.getElementById("activityRangeLabel");
    if (label && hubState.weeklyData) {
      label.textContent = hubState.weeklyData.formatted_week_label || `${hubState.weeklyData.week_start} - ${hubState.weeklyData.week_end}`;
    }
    updateFooterMetrics(hubState.weeklyData);
  }
}
window.switchGraphView = switchGraphView;

function updateFooterMetrics(data) {
  if (!data) return;
  const cEl = document.getElementById("activityCompletedVal");
  const sEl = document.getElementById("activityScheduledVal");
  const xEl = document.getElementById("activityCancelledVal");
  const tEl = document.getElementById("activityTotalVal");

  if (cEl) cEl.textContent = data.completed_count || 0;
  if (sEl) sEl.textContent = data.scheduled_count || 0;
  if (xEl) xEl.textContent = data.cancelled_count || 0;
  if (tEl) tEl.textContent = data.total_count || 0;
}

/* ==============================================================================
   4. Weekly Activity Controls & Matrix Strip
   ============================================================================== */
function initWeeklyGraphControls() {
  const btnPrev = document.getElementById("btnPrevWeek");
  const btnNext = document.getElementById("btnNextWeek");
  const btnCurrent = document.getElementById("btnCurrentWeek");

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      const date = btnPrev.getAttribute("data-date");
      if (date) fetchWeeklyData(date);
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      const date = btnNext.getAttribute("data-date");
      if (date) fetchWeeklyData(date);
    });
  }

  if (btnCurrent) {
    btnCurrent.addEventListener("click", () => {
      fetchWeeklyData();
    });
  }

  // Attach click listener on week pill cards
  attachWeekPillListeners();
}

function attachWeekPillListeners() {
  const pills = document.querySelectorAll("#weekDaysModernGrid .week-day-pill-card");
  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      const d = pill.getAttribute("data-date");
      toggleDateFilter(d);
    });
  });
}

async function fetchWeeklyData(targetDate = "") {
  try {
    let url = "/api/admin/interview-schedules/weekly";
    if (targetDate) url += `?date=${encodeURIComponent(targetDate)}`;
    const resp = await fetch(url);
    const data = await resp.json();
    if (resp.ok && data.status === "success") {
      hubState.weeklyData = data.weekly;
      renderWeeklyGrid(data.weekly);
    }
  } catch (err) {
    console.error("Failed to fetch weekly data:", err);
  }
}
window.fetchWeeklyData = fetchWeeklyData;

function renderWeeklyGrid(weekly) {
  if (!weekly || !weekly.days) return;

  hubState.currentWeekDate = weekly.week_start;

  // Update Range Label
  const label = document.getElementById("activityRangeLabel");
  if (label && hubState.activeView === "week") {
    label.textContent = weekly.formatted_week_label || `${weekly.week_start} - ${weekly.week_end}`;
  }

  // Update Nav Buttons
  const btnPrev = document.getElementById("btnPrevWeek");
  if (btnPrev && weekly.prev_week) btnPrev.setAttribute("data-date", weekly.prev_week);

  const btnNext = document.getElementById("btnNextWeek");
  if (btnNext && weekly.next_week) btnNext.setAttribute("data-date", weekly.next_week);

  // Update footer metrics
  updateFooterMetrics(weekly);

  const gridContainer = document.getElementById("weekDaysModernGrid");
  if (!gridContainer) return;

  let gridHtml = "";
  weekly.days.forEach(day => {
    const isSelected = hubState.activeFilterDate === day.date;
    const hasActivity = day.count > 0;

    let companiesHtml = "";
    if (hasActivity && day.schedules) {
      companiesHtml = '<div class="day-companies-list">';
      day.schedules.forEach(s => {
        const st = (s.status || "scheduled").toLowerCase();
        companiesHtml += `
          <span class="day-company-tag" title="${escapeHtml(s.company_name)} - ${escapeHtml(s.round_name)}">
            <span class="mini-status-dot ${st}"></span>
            <strong>${escapeHtml(s.company_name)}</strong> &bull; ${escapeHtml(s.round_name)}
          </span>
        `;
      });
      companiesHtml += '</div>';
    }

    const indianDate = formatIndianDate(day.date) || day.formatted_date;
    gridHtml += `
      <div class="week-day-pill-card ${hasActivity ? 'active-day' : ''} ${isSelected ? 'selected' : ''}" data-date="${day.date}" title="${day.count} interview(s) on ${day.day_name}, ${indianDate}">
        <div class="day-pill-header">
          <span class="day-pill-name">${day.day_name}</span>
          <span class="day-pill-date">${indianDate}</span>
        </div>
        <div class="day-pill-body">
          ${hasActivity ? `
            <div class="activity-chip has-count">
              <i class="fa-solid fa-bolt"></i>
              <span>${day.count} Round${day.count > 1 ? 's' : ''}</span>
            </div>
            ${companiesHtml}
          ` : `
            <div class="activity-chip is-empty">
              <span class="empty-dash">No Interviews</span>
            </div>
          `}
        </div>
      </div>
    `;
  });

  gridContainer.innerHTML = gridHtml;
  attachWeekPillListeners();
}

/* ==============================================================================
   5. Monthly Activity Controls & Matrix Calendar
   ============================================================================== */
function initMonthlyGraphControls() {
  const btnPrev = document.getElementById("btnPrevMonth");
  const btnNext = document.getElementById("btnNextMonth");
  const btnCurrent = document.getElementById("btnCurrentMonth");

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      const m = btnPrev.getAttribute("data-month");
      if (m) fetchMonthlyData(m);
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      const m = btnNext.getAttribute("data-month");
      if (m) fetchMonthlyData(m);
    });
  }

  if (btnCurrent) {
    btnCurrent.addEventListener("click", () => {
      fetchMonthlyData();
    });
  }
}

async function fetchMonthlyData(targetMonth = "") {
  try {
    let url = "/api/admin/interview-schedules/monthly";
    if (targetMonth) url += `?month=${encodeURIComponent(targetMonth)}`;
    const resp = await fetch(url);
    const data = await resp.json();
    if (resp.ok && data.status === "success") {
      hubState.monthlyData = data.monthly;
      renderMonthMatrix(data.monthly);
    }
  } catch (err) {
    console.error("Failed to fetch monthly data:", err);
  }
}
window.fetchMonthlyData = fetchMonthlyData;

function renderMonthMatrix(monthly) {
  if (!monthly || !monthly.days) return;

  hubState.currentMonthStr = monthly.month_str;

  // Update Range Label
  const label = document.getElementById("activityRangeLabel");
  if (label && hubState.activeView === "month") {
    label.textContent = monthly.formatted_month_label;
  }

  // Update Nav Buttons
  const btnPrev = document.getElementById("btnPrevMonth");
  if (btnPrev && monthly.prev_month) btnPrev.setAttribute("data-month", monthly.prev_month);

  const btnNext = document.getElementById("btnNextMonth");
  if (btnNext && monthly.next_month) btnNext.setAttribute("data-month", monthly.next_month);

  // Update footer metrics
  updateFooterMetrics(monthly);

  const container = document.getElementById("monthMatrixContainer");
  if (!container) return;

  const dayHeaders = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  let html = '<div class="month-calendar-matrix">';

  // Weekday Header Row
  dayHeaders.forEach(dh => {
    html += `<div class="month-matrix-header-cell">${dh}</div>`;
  });

  // Empty padding cells before first weekday (first_weekday: 0=Mon, 6=Sun)
  for (let p = 0; p < monthly.first_weekday; p++) {
    html += `<div class="month-day-cell other-month"></div>`;
  }

  // Month days
  monthly.days.forEach(day => {
    const isSelected = hubState.activeFilterDate === day.date;
    const hasCount = day.count > 0;

    let chipsHtml = "";
    if (hasCount && day.schedules) {
      chipsHtml = '<div class="month-day-chips">';
      day.schedules.forEach(s => {
        const st = (s.status || "scheduled").toLowerCase();
        chipsHtml += `
          <span class="month-mini-chip" title="${escapeHtml(s.company_name)} - ${escapeHtml(s.round_name)}">
            <span class="mini-status-dot ${st}"></span>
            <strong>${escapeHtml(s.company_name)}</strong>
          </span>
        `;
      });
      chipsHtml += '</div>';
    }

    const indianDate = formatIndianDate(day.date) || day.formatted_date;
    html += `
      <div class="month-day-cell ${hasCount ? 'has-interviews' : ''} ${isSelected ? 'selected' : ''}" data-date="${day.date}" title="${day.count} interview(s) on ${indianDate}">
        <div class="month-day-cell-top">
          <span class="month-day-num">${day.day_number}</span>
          ${hasCount ? `<span class="month-day-badge">${day.count}</span>` : ''}
        </div>
        ${chipsHtml}
      </div>
    `;
  });

  html += '</div>';
  container.innerHTML = html;

  // Add click to filter day
  container.querySelectorAll(".month-day-cell:not(.other-month)").forEach(cell => {
    cell.addEventListener("click", () => {
      const d = cell.getAttribute("data-date");
      toggleDateFilter(d);
    });
  });
}

/* ==============================================================================
   6. Date Filter & Clear Controls
   ============================================================================== */
function toggleDateFilter(dateStr) {
  if (hubState.activeFilterDate === dateStr) {
    clearDateFilter();
  } else {
    hubState.activeFilterDate = dateStr;
    applyDateFilter(dateStr);
  }
}

function applyDateFilter(dateStr) {
  const filterBadge = document.getElementById("activeFilterIndicator");
  const filterDateDisplay = document.getElementById("filterDateDisplay");
  if (filterBadge && filterDateDisplay) {
    filterDateDisplay.textContent = formatIndianDate(dateStr) || dateStr;
    filterBadge.style.display = "inline-flex";
  }

  // Update selected classes in Week pills and Month cells
  document.querySelectorAll(".week-day-pill-card").forEach(c => {
    c.classList.toggle("selected", c.getAttribute("data-date") === dateStr);
  });
  document.querySelectorAll(".month-day-cell").forEach(c => {
    c.classList.toggle("selected", c.getAttribute("data-date") === dateStr);
  });

  filterCompanyRowsByDate(dateStr);
}

function clearDateFilter() {
  hubState.activeFilterDate = null;
  const filterBadge = document.getElementById("activeFilterIndicator");
  if (filterBadge) filterBadge.style.display = "none";

  document.querySelectorAll(".week-day-pill-card").forEach(c => c.classList.remove("selected"));
  document.querySelectorAll(".month-day-cell").forEach(c => c.classList.remove("selected"));

  // Reset company rows visibility (all collapsed by default)
  const rows = document.querySelectorAll(".company-row-card");
  rows.forEach(row => {
    row.style.display = "";
    const body = row.querySelector(".company-row-body");
    row.classList.remove("is-expanded");
    if (body) body.style.display = "none";

    const stages = row.querySelectorAll(".pipeline-stage-card");
    stages.forEach(s => s.style.display = "flex");

    const separators = row.querySelectorAll(".pipeline-arrow-separator");
    separators.forEach(sep => sep.style.display = "flex");
  });
}

function initClearFilterBtn() {
  const btn = document.getElementById("btnClearDateFilter");
  if (btn) {
    btn.addEventListener("click", clearDateFilter);
  }
}

function filterCompanyRowsByDate(dateStr) {
  const indianDate = formatIndianDate(dateStr);
  const rows = document.querySelectorAll(".company-row-card");
  rows.forEach(row => {
    const stages = row.querySelectorAll(".pipeline-stage-card");
    let matchCount = 0;
    stages.forEach(stage => {
      const stageDate = stage.getAttribute("data-date") || "";
      const stageText = stage.textContent || "";
      if (stageDate === dateStr || stageText.includes(dateStr) || (indianDate && stageText.includes(indianDate))) {
        stage.style.display = "flex";
        matchCount++;
      } else {
        stage.style.display = "none";
      }
    });

    // Hide or show arrow separators
    const separators = row.querySelectorAll(".pipeline-arrow-separator");
    separators.forEach(sep => {
      sep.style.display = (matchCount > 1) ? "flex" : "none";
    });

    if (matchCount > 0) {
      row.style.display = "";
      row.classList.add("is-expanded");
      const body = row.querySelector(".company-row-body");
      if (body) body.style.display = "block";
    } else {
      row.style.display = "none";
    }
  });
}

/* ==============================================================================
   7. Company Rows Accordion (All info hidden by default)
   ============================================================================== */
function initCompanyRowsAccordion() {
  document.addEventListener("click", (e) => {
    const header = e.target.closest(".company-row-header");
    if (!header) return;

    // Do not toggle if clicked on buttons inside header
    if (e.target.closest("button") || e.target.closest("a")) return;

    const rowCard = header.closest(".company-row-card");
    if (!rowCard) return;

    const targetId = header.getAttribute("data-target");
    const body = targetId ? document.getElementById(targetId) : rowCard.querySelector(".company-row-body");
    if (!body) return;

    const isExpanded = rowCard.classList.contains("is-expanded");
    if (isExpanded) {
      rowCard.classList.remove("is-expanded");
      body.style.display = "none";
    } else {
      rowCard.classList.add("is-expanded");
      body.style.display = "block";
    }
  });
}

/* ==============================================================================
   8. Manual Link & Reorder Rounds Modal
   ============================================================================== */
let reorderState = {
  company: "",
  rounds: []
};

function initReorderRoundsModal() {
  const modal = document.getElementById("reorderRoundsModal");
  const btnClose = document.getElementById("btnCloseReorderModal");
  const btnCancel = document.getElementById("btnCancelReorderModal");
  const btnSave = document.getElementById("btnSaveReorderRounds");

  if (btnClose) btnClose.addEventListener("click", () => modal.style.display = "none");
  if (btnCancel) btnCancel.addEventListener("click", () => modal.style.display = "none");

  // Open modal handler on .btn-open-link-rounds
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-open-link-rounds");
    if (!btn) return;
    e.stopPropagation();

    const compName = btn.getAttribute("data-company");
    if (!compName) return;

    openReorderModal(compName);
  });

  if (btnSave) {
    btnSave.addEventListener("click", async () => {
      if (!reorderState.company || reorderState.rounds.length === 0) return;

      const orderedIds = reorderState.rounds.map(r => r.id);
      showToast(`Saving round links for ${reorderState.company}...`, "info");

      try {
        const resp = await fetch("/api/admin/interview-schedules/reorder", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            company_name: reorderState.company,
            ordered_ids: orderedIds
          })
        });

        const res = await resp.json();
        if (resp.ok && res.status === "success") {
          showToast(`Progression pipeline saved with connected arrow markers!`, "success");
          modal.style.display = "none";
          setTimeout(() => window.location.reload(), 300);
        } else {
          showToast(res.message || "Failed to save reordered rounds", "danger");
        }
      } catch (err) {
        showToast("Error communicating with server", "danger");
      }
    });
  }
}

function openReorderModal(companyName) {
  const modal = document.getElementById("reorderRoundsModal");
  const title = document.getElementById("reorderModalTitle");
  const listContainer = document.getElementById("reorderRoundsList");
  if (!modal || !listContainer) return;

  reorderState.company = companyName;
  if (title) title.textContent = `Link & Connect Rounds — ${companyName}`;

  // Find all schedules for this company from hubState.schedules or scrape from DOM
  let compSchedules = (hubState.schedules || []).filter(
    s => (s.company_name || "").trim().toLowerCase() === companyName.trim().toLowerCase()
  );

  // If not found in memory, read directly from DOM cards
  if (compSchedules.length === 0) {
    const compRow = document.querySelector(`.company-row-card[data-company-name="${companyName.toLowerCase()}"]`);
    if (compRow) {
      compRow.querySelectorAll(".pipeline-stage-card").forEach((card, idx) => {
        const sid = card.getAttribute("data-schedule-id");
        const rName = card.querySelector(".stage-title-text")?.textContent?.trim() || `Round ${idx + 1}`;
        const rDate = card.querySelector(".stage-date-text")?.textContent?.trim() || "";
        compSchedules.push({
          id: sid,
          company_name: companyName,
          round_name: rName,
          date: rDate,
          round_order: idx + 1,
          status: "Scheduled"
        });
      });
    }
  }

  // Sort by existing round_order or date
  compSchedules.sort((a, b) => (a.round_order || 99) - (b.round_order || 99));

  reorderState.rounds = JSON.parse(JSON.stringify(compSchedules));

  renderReorderList();
  modal.style.display = "flex";
}

function renderReorderList() {
  const listContainer = document.getElementById("reorderRoundsList");
  if (!listContainer) return;

  if (reorderState.rounds.length === 0) {
    listContainer.innerHTML = `<div class="no-items-notice">No rounds found for this company to link.</div>`;
    return;
  }

  let html = "";
  reorderState.rounds.forEach((r, idx) => {
    const isFirst = idx === 0;
    const isLast = idx === reorderState.rounds.length - 1;

    const displayDate = formatIndianDate(r.date) || r.date || 'No Date';
    html += `
      <div class="reorder-round-item" data-id="${r.id}">
        <div class="reorder-item-left">
          <span class="reorder-order-badge">${idx + 1}</span>
          <div class="reorder-round-meta">
            <strong>${escapeHtml(r.round_name)}</strong>
            <span><i class="fa-regular fa-calendar"></i> ${escapeHtml(displayDate)} &bull; ${escapeHtml(r.status || 'Scheduled')}</span>
          </div>
        </div>
        <div class="reorder-btns">
          <button type="button" class="reorder-btn btn-move-up" data-idx="${idx}" ${isFirst ? 'disabled' : ''} title="Move Earlier (Round ${idx})">
            <i class="fa-solid fa-arrow-up"></i>
          </button>
          <button type="button" class="reorder-btn btn-move-down" data-idx="${idx}" ${isLast ? 'disabled' : ''} title="Move Later (Round ${idx + 2})">
            <i class="fa-solid fa-arrow-down"></i>
          </button>
        </div>
      </div>
    `;

    if (!isLast) {
      html += `
        <div class="reorder-arrow-between">
          <i class="fa-solid fa-arrow-down"></i> Leads to Round ${idx + 2}
        </div>
      `;
    }
  });

  listContainer.innerHTML = html;

  listContainer.querySelectorAll(".btn-move-up").forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.getAttribute("data-idx"), 10);
      if (idx > 0) {
        const temp = reorderState.rounds[idx];
        reorderState.rounds[idx] = reorderState.rounds[idx - 1];
        reorderState.rounds[idx - 1] = temp;
        renderReorderList();
      }
    });
  });

  listContainer.querySelectorAll(".btn-move-down").forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.getAttribute("data-idx"), 10);
      if (idx < reorderState.rounds.length - 1) {
        const temp = reorderState.rounds[idx];
        reorderState.rounds[idx] = reorderState.rounds[idx + 1];
        reorderState.rounds[idx + 1] = temp;
        renderReorderList();
      }
    });
  });
}

/* ==============================================================================
   9. Search & Filter
   ============================================================================== */
function initCompanySearch() {
  const input = document.getElementById("companySearchInput");
  if (!input) return;

  input.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase().trim();
    filterCompanyRows(term);
  });
}

function filterCompanyRows(term) {
  const rows = document.querySelectorAll(".company-row-card");
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    const stages = row.querySelectorAll(".pipeline-stage-card");
    stages.forEach(item => item.style.display = "flex");

    if (!term || text.includes(term)) {
      row.style.display = "";
      if (term) {
        row.classList.add("is-expanded");
        const body = row.querySelector(".company-row-body");
        if (body) body.style.display = "block";
      }
    } else {
      row.style.display = "none";
    }
  });
}

/* ==============================================================================
   10. Schedule Modal (Add / Edit) & Logic
   ============================================================================== */
function initScheduleModal() {
  const modal = document.getElementById("scheduleModal");
  const form = document.getElementById("scheduleForm");
  const btnOpen = document.getElementById("btnOpenAddSchedule");
  const btnClose = document.getElementById("btnCloseScheduleModal");
  const btnCancel = document.getElementById("btnCancelScheduleModal");
  const btnDelete = document.getElementById("btnDeleteSchedule");
  const btnAddEmail = document.getElementById("btnAddEmailBlock");
  const fileInput = document.getElementById("screenshotFileInput");
  const companyInput = document.getElementById("formCompanyName");

  // Status Radios & Dynamic Fields
  const statusRadios = document.querySelectorAll('input[name="status"]');
  const cancellationGroup = document.getElementById("cancellationReasonGroup");
  const transcriptBox = document.getElementById("transcriptSectionBox");
  const toggleNoTranscript = document.getElementById("toggleNoTranscript");
  const transcriptWrap = document.getElementById("transcriptInputWrap");
  const noTranscriptNotice = document.getElementById("noTranscriptNotice");
  const transcriptTextarea = document.getElementById("formTranscript");

  function updateStatusFieldVisibility() {
    const sel = document.querySelector('input[name="status"]:checked');
    const val = sel ? sel.value : "Scheduled";

    if (cancellationGroup) {
      cancellationGroup.style.display = (val === "Cancelled") ? "block" : "none";
    }

    if (transcriptBox) {
      transcriptBox.style.display = (val === "Completed" || val === "Scheduled") ? "block" : "block";
    }
  }

  statusRadios.forEach(radio => {
    radio.addEventListener("change", updateStatusFieldVisibility);
  });

  if (toggleNoTranscript) {
    toggleNoTranscript.addEventListener("change", (e) => {
      const isNoTranscript = e.target.checked;
      if (transcriptWrap) transcriptWrap.style.display = isNoTranscript ? "none" : "block";
      if (noTranscriptNotice) noTranscriptNotice.style.display = isNoTranscript ? "block" : "none";
      if (transcriptTextarea && isNoTranscript) {
        transcriptTextarea.value = "";
      }
    });
  }

  // Update Next Round dropdown when company changes
  if (companyInput) {
    companyInput.addEventListener("input", (e) => {
      updateNextRoundDropdown(e.target.value.trim());
    });
    companyInput.addEventListener("change", (e) => {
      updateNextRoundDropdown(e.target.value.trim());
    });
  }

  // Open Add Schedule Modal
  if (btnOpen) {
    btnOpen.addEventListener("click", () => {
      openScheduleModal();
    });
  }

  // Close Modal
  if (btnClose) btnClose.addEventListener("click", closeScheduleModal);
  if (btnCancel) btnCancel.addEventListener("click", closeScheduleModal);
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        closeScheduleModal();
      }
    });
  }

  // Add Email Block
  if (btnAddEmail) {
    btnAddEmail.addEventListener("click", () => {
      addEmailBlock("", "");
    });
  }

  // Screenshot Upload Handler
  if (fileInput) {
    fileInput.addEventListener("change", async (e) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;
      for (let i = 0; i < files.length; i++) {
        await uploadScreenshot(files[i]);
      }
      fileInput.value = "";
    });
  }

  // Form Submit
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      await submitScheduleForm();
    });
  }

  // Delete Schedule
  if (btnDelete) {
    btnDelete.addEventListener("click", async () => {
      const id = document.getElementById("formScheduleId").value;
      if (!id) return;
      if (!confirm("Are you sure you want to delete this interview schedule record?")) return;

      try {
        const resp = await fetch(`/api/admin/interview-schedules/${encodeURIComponent(id)}`, {
          method: "DELETE"
        });
        const res = await resp.json();
        if (resp.ok && res.status === "success") {
          showToast("Schedule deleted successfully.", "success");
          closeScheduleModal();
          setTimeout(() => window.location.reload(), 400);
        } else {
          showToast(res.message || "Failed to delete schedule.", "danger");
        }
      } catch (err) {
        showToast("Error communicating with server.", "danger");
      }
    });
  }

  // Delegate edit buttons on company boxes
  document.addEventListener("click", (e) => {
    const editBtn = e.target.closest(".btn-edit-schedule");
    if (editBtn) {
      const schedId = editBtn.getAttribute("data-id");
      openEditScheduleModal(schedId);
      return;
    }

    const addRoundBtn = e.target.closest(".btn-add-round-for-comp");
    if (addRoundBtn) {
      e.stopPropagation();
      const compName = addRoundBtn.getAttribute("data-company");
      openScheduleModal({ company_name: compName });
      return;
    }

    const rescheduleBtn = e.target.closest(".btn-reschedule-action");
    if (rescheduleBtn) {
      const compName = rescheduleBtn.getAttribute("data-company");
      const roundName = rescheduleBtn.getAttribute("data-round");
      openScheduleModal({ company_name: compName, round_name: roundName, status: "Scheduled" });
      return;
    }
  });
}

function updateNextRoundDropdown(companyName, currentSchedId = "", selectedNextId = "") {
  const nextSelect = document.getElementById("formNextRoundId");
  if (!nextSelect) return;

  nextSelect.innerHTML = '<option value="">-- No Next Round (Final Round) --</option>';
  if (!companyName) return;

  const otherRounds = (hubState.schedules || []).filter(
    s => (s.company_name || "").trim().toLowerCase() === companyName.toLowerCase() && s.id !== currentSchedId
  );

  otherRounds.forEach(r => {
    const opt = document.createElement("option");
    opt.value = r.id;
    const displayDate = formatIndianDate(r.date) || r.date || 'No Date';
    opt.textContent = `${r.round_name} (${displayDate})`;
    if (r.id === selectedNextId) {
      opt.selected = true;
    }
    nextSelect.appendChild(opt);
  });
}

function openScheduleModal(initialData = {}) {
  const modal = document.getElementById("scheduleModal");
  const form = document.getElementById("scheduleForm");
  if (!modal || !form) return;

  form.reset();
  const schedId = initialData.id || "";
  document.getElementById("formScheduleId").value = schedId;
  document.getElementById("formRoundId").value = initialData.round_id || "";
  document.getElementById("formQuestionCount").value = initialData.question_count || "0";
  document.getElementById("formQbLink").value = initialData.qb_link || "";

  document.getElementById("formCompanyName").value = initialData.company_name || "";
  document.getElementById("formRoundName").value = initialData.round_name || "";
  document.getElementById("formRoundOrder").value = initialData.round_order || 1;
  document.getElementById("formDate").value = initialData.date || new Date().toISOString().split("T")[0];
  document.getElementById("formStartTime").value = initialData.start_time || "10:00 AM";
  document.getElementById("formEndTime").value = initialData.end_time || "11:00 AM";
  document.getElementById("formHrEmail").value = initialData.hr_email || "";
  document.getElementById("formHrPhone").value = initialData.hr_phone || "";
  document.getElementById("formExperience").value = initialData.experience || "";
  document.getElementById("formTranscript").value = initialData.transcript || "";
  document.getElementById("formCancellationReason").value = initialData.cancellation_reason || "";

  const ytInput = document.getElementById("formYoutubeUrl");
  if (ytInput) {
    ytInput.value = initialData.youtube_url || "";
  }

  // Update Next Round Select
  updateNextRoundDropdown(initialData.company_name || "", schedId, initialData.next_round_id || "");

  // Status Radio
  const statusVal = initialData.status || "Scheduled";
  const r = document.querySelector(`input[name="status"][value="${statusVal}"]`);
  if (r) r.checked = true;

  // Toggle No Transcript
  const toggleNoTranscript = document.getElementById("toggleNoTranscript");
  const transcriptWrap = document.getElementById("transcriptInputWrap");
  const noTranscriptNotice = document.getElementById("noTranscriptNotice");
  const hasNoTranscript = initialData.has_transcript === false && !initialData.transcript;
  if (toggleNoTranscript) toggleNoTranscript.checked = hasNoTranscript;
  if (transcriptWrap) transcriptWrap.style.display = hasNoTranscript ? "none" : "block";
  if (noTranscriptNotice) noTranscriptNotice.style.display = hasNoTranscript ? "block" : "none";

  // Emails & Screenshots
  hubState.activeEmails = initialData.emails ? JSON.parse(JSON.stringify(initialData.emails)) : [];
  hubState.activeScreenshots = initialData.screenshots ? JSON.parse(JSON.stringify(initialData.screenshots)) : [];

  renderEmailBlocks();
  renderScreenshotThumbnails();

  // Cancellation visibility
  const cancellationGroup = document.getElementById("cancellationReasonGroup");
  if (cancellationGroup) {
    cancellationGroup.style.display = (statusVal === "Cancelled") ? "block" : "none";
  }

  // Delete button
  const btnDelete = document.getElementById("btnDeleteSchedule");
  if (btnDelete) {
    btnDelete.style.display = initialData.id ? "inline-block" : "none";
  }

  const titleEl = document.getElementById("scheduleModalTitle");
  if (titleEl) {
    titleEl.textContent = initialData.id ? `Edit Schedule — ${initialData.company_name} (${initialData.round_name})` : "Add Interview Schedule";
  }

  modal.style.display = "flex";
}

function openEditScheduleModal(scheduleId) {
  const sched = (hubState.schedules || []).find(s => s.id === scheduleId);
  if (!sched) {
    fetch(`/api/admin/interview-schedules`)
      .then(r => r.json())
      .then(data => {
        hubState.schedules = data.schedules || [];
        const s = hubState.schedules.find(x => x.id === scheduleId);
        if (s) openScheduleModal(s);
      });
    return;
  }
  openScheduleModal(sched);
}

function closeScheduleModal() {
  const modal = document.getElementById("scheduleModal");
  if (modal) modal.style.display = "none";
}

/* Emails Repeater */
function addEmailBlock(subject = "", body = "") {
  hubState.activeEmails.push({
    id: `em_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
    subject: subject,
    body: body
  });
  renderEmailBlocks();
}

function removeEmailBlock(index) {
  hubState.activeEmails.splice(index, 1);
  renderEmailBlocks();
}

function renderEmailBlocks() {
  const container = document.getElementById("emailsListContainer");
  if (!container) return;

  if (hubState.activeEmails.length === 0) {
    container.innerHTML = `<div class="no-items-notice"><i class="fa-regular fa-envelope"></i> No emails added. Click "+ Add Email" to record invitation emails.</div>`;
    return;
  }

  let html = "";
  hubState.activeEmails.forEach((em, idx) => {
    html += `
      <div class="email-block-item" data-idx="${idx}">
        <div class="email-block-header">
          <strong style="font-size:0.84rem; color:var(--text-primary);"><i class="fa-solid fa-envelope"></i> Email #${idx + 1}</strong>
          <button type="button" class="btn-remove-email" onclick="removeEmailBlock(${idx})" title="Remove this email">
            <i class="fa-solid fa-trash"></i> Remove
          </button>
        </div>
        <div style="margin-bottom:0.4rem;">
          <input type="text" class="form-control email-subject-input" placeholder="Email Subject line..." value="${escapeHtml(em.subject || '')}" oninput="updateEmailField(${idx}, 'subject', this.value)">
        </div>
        <div>
          <textarea class="form-control email-body-input" rows="3" placeholder="Paste full email body or interview invite details here..." oninput="updateEmailField(${idx}, 'body', this.value)">${escapeHtml(em.body || '')}</textarea>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

window.updateEmailField = function(index, field, value) {
  if (hubState.activeEmails[index]) {
    hubState.activeEmails[index][field] = value;
  }
};

window.removeEmailBlock = removeEmailBlock;

/* Lossless Screenshot Upload */
async function uploadScreenshot(file) {
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  showToast(`Uploading ${file.name} losslessly...`, "info");

  try {
    const resp = await fetch("/api/admin/interview-schedules/upload", {
      method: "POST",
      body: formData
    });
    const res = await resp.json();
    if (resp.ok && res.status === "success") {
      hubState.activeScreenshots.push(res.attachment);
      renderScreenshotThumbnails();
      showToast("Screenshot uploaded in original lossless quality!", "success");
    } else {
      showToast(res.message || "Screenshot upload failed.", "danger");
    }
  } catch (err) {
    showToast("Error uploading screenshot.", "danger");
  }
}

function removeScreenshot(index) {
  hubState.activeScreenshots.splice(index, 1);
  renderScreenshotThumbnails();
}
window.removeScreenshot = removeScreenshot;

function renderScreenshotThumbnails() {
  const container = document.getElementById("screenshotsGalleryContainer");
  const notice = document.getElementById("noScreenshotsNotice");
  if (!container) return;

  if (hubState.activeScreenshots.length === 0) {
    container.innerHTML = "";
    if (notice) notice.style.display = "block";
    return;
  }

  if (notice) notice.style.display = "none";

  let html = "";
  hubState.activeScreenshots.forEach((sc, idx) => {
    html += `
      <div class="screenshot-thumb-card" title="Click to view full resolution: ${escapeHtml(sc.original_name || '')}">
        <img src="${sc.url}" class="screenshot-thumb-img" alt="${escapeHtml(sc.original_name || '')}" onclick="openScreenshotViewer('${sc.url}', '${escapeHtml(sc.original_name || '')}')">
        <button type="button" class="screenshot-thumb-delete" onclick="removeScreenshot(${idx}); event.stopPropagation();" title="Delete screenshot">
          <i class="fa-solid fa-xmark"></i>
        </button>
        <span class="screenshot-thumb-zoom" onclick="openScreenshotViewer('${sc.url}', '${escapeHtml(sc.original_name || '')}')">
          <i class="fa-solid fa-magnifying-glass-plus"></i> View Full
        </span>
      </div>
    `;
  });

  container.innerHTML = html;
}

/* Submit Schedule Form */
async function submitScheduleForm() {
  const form = document.getElementById("scheduleForm");
  if (!form) return;

  const id = document.getElementById("formScheduleId").value;
  const company_name = document.getElementById("formCompanyName").value.trim();
  const round_name = document.getElementById("formRoundName").value.trim();
  const round_order = parseInt(document.getElementById("formRoundOrder").value || "1", 10);
  const next_round_id = document.getElementById("formNextRoundId").value.trim();
  const date = document.getElementById("formDate").value;
  const start_time = document.getElementById("formStartTime").value.trim();
  const end_time = document.getElementById("formEndTime").value.trim();
  const hr_email = document.getElementById("formHrEmail").value.trim();
  const hr_phone = document.getElementById("formHrPhone").value.trim();
  const youtube_url = (document.getElementById("formYoutubeUrl")?.value || "").trim();
  const experience = document.getElementById("formExperience").value.trim();
  const transcript = document.getElementById("formTranscript").value.trim();
  const cancellation_reason = document.getElementById("formCancellationReason").value.trim();
  const round_id = document.getElementById("formRoundId").value;
  const question_count = parseInt(document.getElementById("formQuestionCount").value || "0", 10);
  const qb_link = document.getElementById("formQbLink").value;

  const statusRadio = document.querySelector('input[name="status"]:checked');
  const status = statusRadio ? statusRadio.value : "Scheduled";

  const toggleNoTranscript = document.getElementById("toggleNoTranscript");
  const has_transcript = toggleNoTranscript ? !toggleNoTranscript.checked : Boolean(transcript);

  if (!company_name || !round_name || !date || !start_time) {
    showToast("Please fill in company name, round name, date, and start time.", "warning");
    return;
  }

  const payload = {
    id: id || undefined,
    company_name,
    round_name,
    round_order,
    next_round_id,
    date,
    start_time,
    end_time,
    hr_email,
    hr_phone,
    youtube_url,
    status,
    cancellation_reason,
    emails: hubState.activeEmails,
    screenshots: hubState.activeScreenshots,
    experience,
    transcript: has_transcript ? transcript : "",
    has_transcript,
    round_id,
    question_count,
    qb_link: qb_link || `/question-bank?search=${encodeURIComponent(company_name)}`
  };

  try {
    const resp = await fetch("/api/admin/interview-schedules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const res = await resp.json();
    if (resp.ok && res.status === "success") {
      showToast("Interview schedule saved successfully!", "success");
      closeScheduleModal();
      setTimeout(() => window.location.reload(), 300);
    } else {
      showToast(res.message || "Failed to save schedule.", "danger");
    }
  } catch (err) {
    showToast("Network error communicating with server.", "danger");
  }
}

/* ==============================================================================
   11. Modal Viewers (Emails, Transcript, YouTube & Lossless Screenshots)
   ============================================================================== */
let currentViewerTranscript = "";

async function getScheduleById(scheduleId) {
  if (!scheduleId) return null;
  let sched = (hubState.schedules || []).find(s => s.id === scheduleId);
  if (sched) return sched;

  // Try reading from hub-init-data script element
  try {
    const raw = document.getElementById("hub-init-data")?.textContent?.trim();
    if (raw) {
      const data = JSON.parse(raw);
      if (Array.isArray(data.schedules)) {
        hubState.schedules = data.schedules;
        sched = hubState.schedules.find(s => s.id === scheduleId);
        if (sched) return sched;
      }
    }
  } catch (e) {
    console.warn("Could not parse embedded init data:", e);
  }

  // Fetch from server if still missing
  try {
    const resp = await fetch("/api/admin/interview-schedules");
    if (resp.ok) {
      const data = await resp.json();
      hubState.schedules = data.schedules || [];
      sched = (hubState.schedules || []).find(s => s.id === scheduleId);
      if (sched) return sched;
    }
  } catch (err) {
    console.warn("Could not fetch interview schedules:", err);
  }

  return null;
}

function initEmailsViewerModal() {
  const modal = document.getElementById("emailsViewerModal");
  const btnClose = document.getElementById("btnCloseEmailsViewerModal");
  const btnCancel = document.getElementById("btnCancelEmailsViewerModal");

  if (btnClose) btnClose.addEventListener("click", closeEmailsViewerModal);
  if (btnCancel) btnCancel.addEventListener("click", closeEmailsViewerModal);
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeEmailsViewerModal();
    });
  }

  // Event delegation for opening emails modal from round cards
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-view-emails");
    if (!btn) return;
    e.stopPropagation();
    const schedId = btn.getAttribute("data-id");
    openEmailsViewerModal(schedId);
  });
}

function closeEmailsViewerModal() {
  const modal = document.getElementById("emailsViewerModal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
}
window.closeEmailsViewerModal = closeEmailsViewerModal;

async function openEmailsViewerModal(scheduleId) {
  const modal = document.getElementById("emailsViewerModal");
  const titleEl = document.getElementById("emailsViewerTitle");
  const contentEl = document.getElementById("emailsViewerContent");
  if (!modal || !contentEl) return;

  const sched = await getScheduleById(scheduleId);
  if (!sched) {
    showToast("Schedule details not found.", "warning");
    return;
  }

  if (titleEl) {
    titleEl.innerHTML = `Received Interview Emails &mdash; <strong style="color:var(--text-primary);">${escapeHtml(sched.company_name)}</strong> (${escapeHtml(sched.round_name)})`;
  }

  const emails = sched.emails || [];
  if (emails.length === 0) {
    contentEl.innerHTML = `
      <div class="no-items-notice" style="text-align:center; padding:2rem 1rem;">
        <i class="fa-regular fa-envelope-open" style="font-size:2rem; opacity:0.4; margin-bottom:0.5rem; display:block;"></i>
        No email correspondence recorded for this round.
      </div>
    `;
  } else {
    let html = `<div style="display:flex; flex-direction:column; gap:0.85rem;">`;
    emails.forEach((em, idx) => {
      const subject = em.subject ? escapeHtml(em.subject) : `Email #${idx + 1}`;
      const bodyText = em.body || "(Empty email body)";
      html += `
        <div class="email-viewer-card">
          <div class="email-viewer-header">
            <div class="email-viewer-subj">
              <i class="fa-solid fa-envelope" style="color:var(--primary); font-size:0.85rem;"></i>
              <span>${subject}</span>
            </div>
            <button type="button" class="btn btn-outline btn-xs btn-copy-email-body" data-idx="${idx}" title="Copy email text">
              <i class="fa-regular fa-copy"></i> Copy Email
            </button>
          </div>
          <div class="email-viewer-body">${escapeHtml(bodyText)}</div>
        </div>
      `;
    });
    html += `</div>`;
    contentEl.innerHTML = html;

    // Attach copy button handlers
    contentEl.querySelectorAll(".btn-copy-email-body").forEach(copyBtn => {
      copyBtn.addEventListener("click", () => {
        const idx = parseInt(copyBtn.getAttribute("data-idx"), 10);
        const targetEmail = emails[idx];
        if (targetEmail) {
          const copyContent = `Subject: ${targetEmail.subject || ''}\n\n${targetEmail.body || ''}`;
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(copyContent).then(() => {
              showToast("Email copied to clipboard!", "success");
            }).catch(() => {
              showToast("Could not copy email to clipboard.", "danger");
            });
          } else {
            showToast("Clipboard copy not supported in this browser.", "warning");
          }
        }
      });
    });
  }

  modal.style.display = "flex";
  modal.classList.add("active");
  modal.removeAttribute("aria-hidden");
  document.body.style.overflow = "hidden";
}
window.openEmailsViewerModal = openEmailsViewerModal;

function initTranscriptViewerModal() {
  const modal = document.getElementById("transcriptViewerModal");
  const btnClose = document.getElementById("btnCloseTranscriptViewerModal");
  const btnCancel = document.getElementById("btnCancelTranscriptViewerModal");
  const btnCopy = document.getElementById("btnCopyTranscriptModal");

  if (btnClose) btnClose.addEventListener("click", closeTranscriptViewerModal);
  if (btnCancel) btnCancel.addEventListener("click", closeTranscriptViewerModal);
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeTranscriptViewerModal();
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener("click", () => {
      if (!currentViewerTranscript || !currentViewerTranscript.trim()) {
        showToast("No transcript text to copy.", "warning");
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(currentViewerTranscript).then(() => {
          showToast("Interview transcript copied to clipboard!", "success");
        }).catch(() => {
          showToast("Could not copy transcript to clipboard.", "danger");
        });
      } else {
        showToast("Clipboard copy not supported in this browser.", "warning");
      }
    });
  }

  // Event delegation for opening transcript modal from round cards
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-view-transcript");
    if (!btn) return;
    e.stopPropagation();
    const schedId = btn.getAttribute("data-id");
    openTranscriptViewerModal(schedId);
  });
}

function closeTranscriptViewerModal() {
  const modal = document.getElementById("transcriptViewerModal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    // Stop any playing iframe
    const iframe = modal.querySelector("iframe");
    if (iframe) iframe.src = "";
  }
}
window.closeTranscriptViewerModal = closeTranscriptViewerModal;

function extractYouTubeId(url) {
  if (!url) return null;
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
  return match ? match[1] : null;
}

async function openTranscriptViewerModal(scheduleId) {
  const modal = document.getElementById("transcriptViewerModal");
  const titleEl = document.getElementById("transcriptViewerTitle");
  const contentEl = document.getElementById("transcriptViewerContent");
  if (!modal || !contentEl) return;

  const sched = await getScheduleById(scheduleId);
  if (!sched) {
    showToast("Schedule details not found.", "warning");
    return;
  }

  currentViewerTranscript = sched.transcript || "";

  if (titleEl) {
    titleEl.innerHTML = `Interview Transcript &mdash; <strong style="color:var(--text-primary);">${escapeHtml(sched.company_name)}</strong> (${escapeHtml(sched.round_name)})`;
  }

  const displayDate = formatIndianDate(sched.date) || sched.date || "";
  const displayStatus = sched.status || "Completed";
  const hasExperience = Boolean(sched.experience && sched.experience.trim());
  const ytVideoId = extractYouTubeId(sched.youtube_url);

  let html = `
    <div class="transcript-viewer-container">
      <div class="transcript-meta-strip">
        <span><i class="fa-regular fa-building"></i> <strong>${escapeHtml(sched.company_name)}</strong></span>
        <span>&bull;</span>
        <span><i class="fa-solid fa-layer-group"></i> ${escapeHtml(sched.round_name)}</span>
        <span>&bull;</span>
        <span><i class="fa-regular fa-calendar"></i> ${escapeHtml(displayDate)}</span>
        <span>&bull;</span>
        <span><i class="fa-regular fa-clock"></i> ${escapeHtml(sched.start_time || '')}${sched.end_time ? ' - ' + escapeHtml(sched.end_time) : ''}</span>
        <span>&bull;</span>
        <span class="status-badge ${displayStatus.toLowerCase()}">${escapeHtml(displayStatus)}</span>
      </div>
  `;

  if (sched.youtube_url) {
    html += `
      <div class="transcript-youtube-section" style="background:#fff1f2; border:1px solid #fecdd3; border-radius:8px; padding:0.85rem; margin-bottom:0.25rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; flex-wrap:wrap; gap:0.5rem;">
          <div style="display:flex; align-items:center; gap:0.45rem; font-weight:700; color:#9f1239; font-size:0.88rem;">
            <i class="fa-brands fa-youtube" style="font-size:1.1rem; color:#e11d48;"></i>
            <span>Interview Recording Available</span>
          </div>
          <div style="display:flex; gap:0.4rem;">
            <a href="${escapeHtml(sched.youtube_url)}" target="_blank" rel="noopener noreferrer" class="btn btn-xs btn-outline" style="color:#e11d48; border-color:#fda4af;">
              <i class="fa-solid fa-arrow-up-right-from-square"></i> Open in YouTube
            </a>
            <button type="button" class="btn btn-xs btn-outline" onclick="openQuickYoutubeModal('${escapeHtml(sched.id)}')" style="color:#475569;">
              <i class="fa-solid fa-pen"></i> Edit Link
            </button>
          </div>
        </div>
        ${ytVideoId ? `
          <div style="position:relative; padding-bottom:56.25%; height:0; overflow:hidden; border-radius:6px; box-shadow:0 2px 6px rgba(0,0,0,0.1);">
            <iframe src="https://www.youtube.com/embed/${escapeHtml(ytVideoId)}" style="position:absolute; top:0; left:0; width:100%; height:100%; border:0;" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
          </div>
        ` : `
          <div style="font-size:0.8rem; word-break:break-all; color:#9f1239;">
            <a href="${escapeHtml(sched.youtube_url)}" target="_blank" rel="noopener noreferrer" style="color:#e11d48; text-decoration:underline;">${escapeHtml(sched.youtube_url)}</a>
          </div>
        `}
      </div>
    `;
  } else {
    html += `
      <div style="display:flex; justify-content:flex-end; margin-bottom:0.1rem;">
        <button type="button" class="btn btn-xs btn-outline" onclick="openQuickYoutubeModal('${escapeHtml(sched.id)}')" style="font-size:0.75rem; color:#dc2626;">
          <i class="fa-brands fa-youtube"></i> + Add YouTube Recording Link
        </button>
      </div>
    `;
  }

  if (hasExperience) {
    html += `
      <div style="background:#fefce8; border:1px solid #fef08a; border-radius:6px; padding:0.75rem 0.95rem; font-size:0.85rem; color:#854d0e;">
        <strong style="display:flex; align-items:center; gap:0.35rem; margin-bottom:0.25rem;"><i class="fa-solid fa-lightbulb"></i> Candidate Experience & Reflection:</strong>
        <div>${escapeHtml(sched.experience)}</div>
      </div>
    `;
  }

  if (!currentViewerTranscript.trim()) {
    html += `
      <div class="no-items-notice" style="text-align:center; padding:2rem 1rem;">
        <i class="fa-regular fa-file-lines" style="font-size:2rem; opacity:0.4; margin-bottom:0.5rem; display:block;"></i>
        <div>No detailed transcript text recorded yet for this round.</div>
        <button type="button" class="btn btn-sm btn-primary" onclick="closeTranscriptViewerModal(); openEditScheduleModal('${escapeHtml(sched.id)}');" style="margin-top:0.75rem;">
          <i class="fa-solid fa-pen-to-square"></i> Add Transcript in Edit Mode
        </button>
      </div>
    `;
  } else {
    html += `
      <div class="transcript-reader-box">${escapeHtml(currentViewerTranscript)}</div>
    `;
  }

  html += `</div>`;
  contentEl.innerHTML = html;
  modal.style.display = "flex";
  modal.classList.add("active");
  modal.removeAttribute("aria-hidden");
  document.body.style.overflow = "hidden";
}
window.openTranscriptViewerModal = openTranscriptViewerModal;

/* Quick YouTube Link Modal */
async function openQuickYoutubeModal(scheduleId) {
  const modal = document.getElementById("quickYoutubeModal");
  const idInput = document.getElementById("quickYoutubeScheduleId");
  const urlInput = document.getElementById("quickYoutubeInput");
  const titleEl = document.getElementById("quickYoutubeModalTitle");
  if (!modal || !idInput || !urlInput) return;

  const sched = await getScheduleById(scheduleId);
  if (!sched) {
    showToast("Schedule details not found.", "warning");
    return;
  }

  idInput.value = sched.id;
  urlInput.value = sched.youtube_url || "";
  if (titleEl) {
    titleEl.innerHTML = `YouTube Recording &mdash; <strong>${escapeHtml(sched.company_name)}</strong> (${escapeHtml(sched.round_name)})`;
  }

  modal.style.display = "flex";
  modal.classList.add("active");
  modal.removeAttribute("aria-hidden");
  document.body.style.overflow = "hidden";
  setTimeout(() => urlInput.focus(), 100);
}
window.openQuickYoutubeModal = openQuickYoutubeModal;

function closeQuickYoutubeModal() {
  const modal = document.getElementById("quickYoutubeModal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
}
window.closeQuickYoutubeModal = closeQuickYoutubeModal;

async function submitQuickYoutubeForm(e) {
  e.preventDefault();
  const id = document.getElementById("quickYoutubeScheduleId")?.value;
  const ytUrl = (document.getElementById("quickYoutubeInput")?.value || "").trim();
  const saveBtn = document.getElementById("btnSaveQuickYoutube");
  if (!id) return;

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
  }

  try {
    const resp = await fetch("/api/admin/interview-schedules/youtube", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ schedule_id: id, youtube_url: ytUrl })
    });
    const res = await resp.json();
    if (resp.ok && res.status === "success") {
      showToast("YouTube recording link saved!", "success");
      closeQuickYoutubeModal();
      // Update in-memory schedule
      const s = (hubState.schedules || []).find(x => x.id === id);
      if (s) s.youtube_url = ytUrl;
      setTimeout(() => window.location.reload(), 300);
    } else {
      showToast(res.message || "Failed to save YouTube link.", "danger");
    }
  } catch (err) {
    showToast("Network error saving YouTube link.", "danger");
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = "Save Recording Link";
    }
  }
}
window.submitQuickYoutubeForm = submitQuickYoutubeForm;

function initQuickYoutubeModal() {
  const modal = document.getElementById("quickYoutubeModal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeQuickYoutubeModal();
    });
  }
}

function initScreenshotViewerModal() {
  const modal = document.getElementById("screenshotViewerModal");
  const btnClose = document.getElementById("btnCloseViewerModal");
  if (btnClose) btnClose.addEventListener("click", () => {
    if (modal) {
      modal.style.display = "none";
      modal.classList.remove("active");
      document.body.style.overflow = "";
    }
  });
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.style.display = "none";
        modal.classList.remove("active");
        document.body.style.overflow = "";
      }
    });
  }
}

window.openScreenshotViewer = function(url, title = "Screenshot Preview") {
  const modal = document.getElementById("screenshotViewerModal");
  const img = document.getElementById("viewerImage");
  const titleEl = document.getElementById("viewerTitle");
  if (!modal || !img) return;

  img.src = url;
  if (titleEl) titleEl.textContent = title || "Screenshot Preview (100% Original Lossless)";
  modal.style.display = "flex";
  modal.classList.add("active");
  document.body.style.overflow = "hidden";
};

/* ==============================================================================
   12. Quick Status Modal
   ============================================================================== */
function initQuickStatusModal() {
  const modal = document.getElementById("quickStatusModal");
  const form = document.getElementById("quickStatusForm");
  const btnClose = document.getElementById("btnCloseQuickStatusModal");
  const btnCancel = document.getElementById("btnCancelQuickStatus");
  const statusSelect = document.getElementById("quickStatusSelect");
  const cancellationGroup = document.getElementById("quickCancellationGroup");
  const transcriptGroup = document.getElementById("quickTranscriptGroup");
  const noTranscriptToggle = document.getElementById("quickNoTranscriptToggle");
  const transcriptInput = document.getElementById("quickTranscriptInput");
  const youtubeGroup = document.getElementById("quickYoutubeGroup");
  const youtubeInput = document.getElementById("quickYoutubeUrl");

  function updateQuickFields() {
    const val = statusSelect ? statusSelect.value : "";
    if (cancellationGroup) cancellationGroup.style.display = (val === "Cancelled") ? "block" : "none";
    if (transcriptGroup) transcriptGroup.style.display = (val === "Completed") ? "block" : "none";
    if (youtubeGroup) youtubeGroup.style.display = (val === "Completed") ? "block" : "none";
  }

  if (statusSelect) {
    statusSelect.addEventListener("change", updateQuickFields);
  }

  if (noTranscriptToggle) {
    noTranscriptToggle.addEventListener("change", (e) => {
      if (transcriptInput) {
        transcriptInput.disabled = e.target.checked;
        if (e.target.checked) transcriptInput.value = "";
      }
    });
  }

  if (btnClose) btnClose.addEventListener("click", () => modal.style.display = "none");
  if (btnCancel) btnCancel.addEventListener("click", () => modal.style.display = "none");

  // Delegate quick status buttons
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-quick-status");
    if (!btn) return;
    const schedId = btn.getAttribute("data-id");
    const targetStatus = btn.getAttribute("data-status");

    document.getElementById("quickStatusScheduleId").value = schedId;
    if (statusSelect) statusSelect.value = targetStatus;
    const sched = (hubState.schedules || []).find(s => s.id === schedId);
    if (youtubeInput) youtubeInput.value = sched ? (sched.youtube_url || "") : "";
    updateQuickFields();
    modal.style.display = "flex";
    modal.classList.add("active");
  });

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const schedId = document.getElementById("quickStatusScheduleId").value;
      const status = statusSelect.value;
      const reason = document.getElementById("quickCancellationReason").value;
      const isNoT = noTranscriptToggle ? noTranscriptToggle.checked : false;
      const tText = transcriptInput ? transcriptInput.value : "";
      const ytText = youtubeInput ? youtubeInput.value.trim() : "";

      try {
        const resp = await fetch("/api/admin/interview-schedules/status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            schedule_id: schedId,
            status: status,
            cancellation_reason: reason,
            has_transcript: !isNoT,
            transcript: isNoT ? "" : tText,
            youtube_url: ytText
          })
        });
        const res = await resp.json();
        if (resp.ok && res.status === "success") {
          showToast(`Status updated to ${status}!`, "success");
          modal.style.display = "none";
          modal.classList.remove("active");
          setTimeout(() => window.location.reload(), 300);
        } else {
          showToast(res.message || "Failed to update status", "danger");
        }
      } catch (err) {
        showToast("Error communicating with server", "danger");
      }
    });
  }
}

/* ==============================================================================
   13. Page Visibility Toggles (Preserved intact)
   ============================================================================== */
function initAdminToggles() {
  const cards = document.querySelectorAll(".admin-page-card");

  cards.forEach(card => {
    const pageKey = card.getAttribute("data-page-key");
    const publishBtn = card.querySelector(".btn-publish-action");
    const hideBtn = card.querySelector(".btn-hide-action");

    if (publishBtn) {
      publishBtn.addEventListener("click", () => {
        setPageVisibility(pageKey, true, card);
      });
    }

    if (hideBtn) {
      hideBtn.addEventListener("click", () => {
        setPageVisibility(pageKey, false, card);
      });
    }
  });
}

async function setPageVisibility(pageKey, isPublished, cardEl) {
  try {
    const response = await fetch("/api/admin/toggle-visibility", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_key: pageKey, is_published: isPublished })
    });

    const data = await response.json();

    if (response.ok && data.status === "success") {
      updateCardUI(cardEl, isPublished);
      updateCountersUI(data.published_count, data.hidden_count);
      showToast(data.message || "Page visibility updated!", "success");
    } else if (response.status === 403) {
      showToast(data.message || "Please unlock with admin passphrase first.", "warning");
    } else {
      showToast(data.message || "Failed to update visibility.", "danger");
    }
  } catch (err) {
    console.error("Error setting visibility:", err);
    showToast("Network error communicating with admin server.", "danger");
  }
}

function updateCardUI(cardEl, isPublished) {
  if (!cardEl) return;
  const statusPill = cardEl.querySelector(".admin-status-pill");
  const publishBtn = cardEl.querySelector(".btn-publish-action");
  const hideBtn = cardEl.querySelector(".btn-hide-action");

  if (isPublished) {
    cardEl.classList.remove("is-hidden-mode");
    cardEl.classList.add("is-published-mode");
    if (statusPill) {
      statusPill.className = "admin-status-pill published";
      statusPill.innerHTML = '<i class="fa-solid fa-circle-check"></i> Published & Live';
    }
    if (publishBtn) {
      publishBtn.disabled = true;
      publishBtn.style.opacity = "0.6";
      publishBtn.style.cursor = "default";
    }
    if (hideBtn) {
      hideBtn.disabled = false;
      hideBtn.style.opacity = "1";
      hideBtn.style.cursor = "pointer";
    }
  } else {
    cardEl.classList.remove("is-published-mode");
    cardEl.classList.add("is-hidden-mode");
    if (statusPill) {
      statusPill.className = "admin-status-pill hidden";
      statusPill.innerHTML = '<i class="fa-solid fa-eye-slash"></i> Hidden (Unpublished)';
    }
    if (publishBtn) {
      publishBtn.disabled = false;
      publishBtn.style.opacity = "1";
      publishBtn.style.cursor = "pointer";
    }
    if (hideBtn) {
      hideBtn.disabled = true;
      hideBtn.style.opacity = "0.6";
      hideBtn.style.cursor = "default";
    }
  }
}

function updateCountersUI(pubCount, hidCount) {
  const pubEl = document.getElementById("adminStatPublished");
  const hidEl = document.getElementById("adminStatHidden");
  if (pubEl && pubCount !== undefined) pubEl.textContent = pubCount;
  if (hidEl && hidCount !== undefined) hidEl.textContent = hidCount;
}

/* ==============================================================================
   14. Authentication & Logout
   ============================================================================== */
function initAdminAuthForm() {
  const form = document.getElementById("adminLoginForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("adminPassInput");
    const password = input ? input.value : "";

    try {
      const resp = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password })
      });

      const res = await resp.json();
      if (resp.ok && res.status === "success") {
        showToast("Access granted. Controls unlocked!", "success");
        setTimeout(() => window.location.reload(), 300);
      } else {
        showToast(res.message || "Invalid passphrase", "danger");
      }
    } catch (err) {
      showToast("Authentication request failed", "danger");
    }
  });
}

function initAdminLogout() {
  const logoutBtn = document.getElementById("adminLogoutBtn");
  if (!logoutBtn) return;

  logoutBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      await fetch("/api/admin/logout", { method: "POST" });
    } catch (err) {
      console.warn("Logout error:", err);
    }
    document.cookie = "devops_hub_admin_auth=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    document.cookie = "devops_hub_admin_auth=; expires=Thu, 01 Jan 1970 00:00:00 UTC;";
    window.location.href = "/admin/logout";
  });
}

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer") || document.body;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.style.cssText = `
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: #1e293b;
    color: #ffffff;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    font-size: 0.88rem;
    z-index: 99999;
  `;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.2s ease";
    setTimeout(() => toast.remove(), 200);
  }, 2500);
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* Bootstrap execution after all definitions are loaded */
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrapAdminPortal);
} else {
  bootstrapAdminPortal();
}

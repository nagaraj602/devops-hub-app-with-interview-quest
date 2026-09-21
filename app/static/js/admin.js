/* ==============================================================================
   Admin Portal JavaScript: Page Visibility Toggles & Authentication
   ============================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  initAdminToggles();
  initAdminAuthForm();
});

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
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        page_key: pageKey,
        is_published: isPublished
      })
    });

    const data = await response.json();

    if (response.ok && data.status === "success") {
      updateCardUI(cardEl, isPublished);
      updateCountersUI(data.published_count, data.hidden_count);
      showToast(data.message || "Page visibility updated!", "success");
    } else if (response.status === 403) {
      showToast(data.message || "Please unlock with admin passphrase first.", "warning");
      const authModal = document.getElementById("adminAuthModal");
      if (authModal) openModal("adminAuthModal");
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
        setTimeout(() => {
          window.location.reload();
        }, 500);
      } else {
        showToast(res.message || "Invalid passphrase", "danger");
      }
    } catch (err) {
      showToast("Authentication request failed", "danger");
    }
  });

  const logoutBtn = document.getElementById("adminLogoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await fetch("/api/admin/logout", { method: "POST" });
        showToast("Logged out of admin console", "info");
        setTimeout(() => { window.location.reload(); }, 500);
      } catch (err) {
        window.location.reload();
      }
    });
  }
}

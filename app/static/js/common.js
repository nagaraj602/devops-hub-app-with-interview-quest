/* ==============================================================================
   Common Application JavaScript: Fonts, Toasts, Copy Utility, Mobile Drawer & Session
   ============================================================================== */

// Save last accessed page to localStorage (User requirement: session stored in browser)
(function saveLastAccessedPage() {
  const currentPath = window.location.pathname;
  if (currentPath && currentPath !== "/api/health") {
    localStorage.setItem("devops_hub_last_page", currentPath);
  }
})();

// Initialize Font Settings on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initFontSettings();
  initMobileDrawer();
  initGlobalCopyButtons();
});

// Font Settings Manager
function initFontSettings() {
  const savedFamily = localStorage.getItem("devops_hub_font_family") || "sans";
  const savedSize = localStorage.getItem("devops_hub_font_size") || "md";

  applyFontFamily(savedFamily);
  applyFontSize(savedSize);

  // Set active radio/buttons in font modal if it exists
  const familyInputs = document.querySelectorAll('input[name="font-family"]');
  familyInputs.forEach(input => {
    if (input.value === savedFamily) input.checked = true;
    input.addEventListener("change", (e) => {
      applyFontFamily(e.target.value);
    });
  });

  const sizeInputs = document.querySelectorAll('input[name="font-size"]');
  sizeInputs.forEach(input => {
    if (input.value === savedSize) input.checked = true;
    input.addEventListener("change", (e) => {
      applyFontSize(e.target.value);
    });
  });
}

function applyFontFamily(family) {
  document.body.classList.remove("font-sans", "font-mono", "font-serif");
  document.body.classList.add(`font-${family}`);
  localStorage.setItem("devops_hub_font_family", family);
}

function applyFontSize(size) {
  document.body.classList.remove("size-sm", "size-md", "size-lg", "size-xl");
  document.body.classList.add(`size-${size}`);
  localStorage.setItem("devops_hub_font_size", size);
}

// Modal open/close helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

// Close modals when clicking outside modal-content
window.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("active");
    document.body.style.overflow = "";
  }
});

// Mobile Navigation Drawer Toggle
function initMobileDrawer() {
  const toggleBtn = document.getElementById("mobileToggleBtn");
  const drawer = document.getElementById("mobileNavDrawer");
  if (toggleBtn && drawer) {
    toggleBtn.addEventListener("click", () => {
      drawer.classList.toggle("open");
    });
  }
}

// Global Copy Text Helper
function copyTextToClipboard(text, successMsg = "Copied to clipboard!") {
  if (!text) return;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMsg, "success");
    }).catch(() => {
      fallbackCopyText(text, successMsg);
    });
  } else {
    fallbackCopyText(text, successMsg);
  }
}

function fallbackCopyText(text, successMsg) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.top = "-9999px";
  textArea.style.left = "-9999px";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    document.execCommand("copy");
    showToast(successMsg, "success");
  } catch (err) {
    showToast("Failed to copy", "danger");
  }
  document.body.removeChild(textArea);
}

// Toast Notifications System
function showToast(message, type = "info") {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  let icon = "fa-info-circle";
  if (type === "success") icon = "fa-check-circle";
  if (type === "danger") icon = "fa-exclamation-circle";
  if (type === "warning") icon = "fa-exclamation-triangle";

  toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.25s ease";
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 250);
  }, 2800);
}

// Global Copy Buttons Initialization
function initGlobalCopyButtons() {
  document.addEventListener("click", (e) => {
    const copyBtn = e.target.closest(".copy-btn");
    if (copyBtn) {
      const textToCopy = copyBtn.getAttribute("data-copy-text");
      if (textToCopy) {
        copyTextToClipboard(textToCopy);
      }
    }
  });
}

/* ==============================================================================
   Sync All & Continuous Logs JavaScript
   ============================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  initSyncButtons();
});

function initSyncButtons() {
  const syncAllBtn = document.getElementById("triggerSyncAllBtn");
  if (syncAllBtn) {
    syncAllBtn.addEventListener("click", () => {
      triggerGlobalSync(syncAllBtn);
    });
  }

  document.querySelectorAll(".repo-sync-trigger-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const repoId = btn.getAttribute("data-repo-id");
      if (repoId) {
        triggerRepoSync(repoId, btn);
      }
    });
  });
}

function triggerRepoSync(repoId, btn) {
  const origHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Syncing...`;

  fetch(`/api/sync/${encodeURIComponent(repoId)}`, { method: "POST" })
    .then(res => res.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = origHtml;
      if (data.status === "success" || data.status === "info") {
        showToast(data.message || `Synced ${repoId}!`, "success");
        refreshAuditLogsTable();
      } else {
        showToast(data.message || `Sync notice for ${repoId}`, "warning");
      }
    })
    .catch(err => {
      btn.disabled = false;
      btn.innerHTML = origHtml;
      showToast(`Sync failed: ${err.message}`, "danger");
    });
}

function triggerGlobalSync(btn) {
  const origHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Syncing All Repositories...`;

  fetch("/api/sync-all", { method: "POST" })
    .then(res => res.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = origHtml;
      showToast("All repositories synchronized successfully!", "success");
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    })
    .catch(err => {
      btn.disabled = false;
      btn.innerHTML = origHtml;
      showToast(`Global sync failed: ${err.message}`, "danger");
    });
}

function refreshAuditLogsTable() {
  const tbody = document.getElementById("auditLogsTableBody");
  if (!tbody) return;

  fetch("/api/logs?limit=30")
    .then(res => res.json())
    .then(data => {
      if (data.logs && data.logs.length > 0) {
        tbody.innerHTML = "";
        data.logs.forEach(log => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><code>${log.timestamp}</code></td>
            <td><span class="badge badge-blue">${log.event}</span></td>
            <td><strong>${log.target}</strong></td>
            <td>${log.details}</td>
            <td><span class="badge badge-gray">${log.triggered_by}</span></td>
          `;
          tbody.appendChild(tr);
        });
      }
    })
    .catch(err => console.error("Failed to refresh audit logs:", err));
}

/* ==============================================================================
   Training Materials & Notes Explorer JavaScript: File Tree, Lightbox & Custom Repos
   ============================================================================== */

let currentRepoId = "training";
let currentFilePath = "README.md";

// Image Lightbox State
let lightboxZoom = 1;
let isPanning = false;
let startX = 0, startY = 0;
let translateX = 0, translateY = 0;

document.addEventListener("DOMContentLoaded", () => {
  initTrainingExplorer();
  initImageLightbox();
  initCustomReposManager();
});

function initTrainingExplorer() {
  initTreeNodeClicks();
  initSidebarSearch();
  initRepoSelector();
  renderMermaidDiagrams();
  bindContentImagesForLightbox();
}

// Tree Node Expand / Collapse and File Loading
function initTreeNodeClicks() {
  document.addEventListener("click", (e) => {
    // Folder Click
    const folderRow = e.target.closest(".tree-node.folder > .tree-node-row");
    if (folderRow) {
      const node = folderRow.closest(".tree-node");
      node.classList.toggle("expanded");
      return;
    }

    // File Click
    const fileRow = e.target.closest(".tree-node.file > .tree-node-row");
    if (fileRow) {
      document.querySelectorAll(".tree-node-row").forEach(r => r.classList.remove("active"));
      fileRow.classList.add("active");

      const filePath = fileRow.getAttribute("data-file-path");
      if (filePath) {
        loadFileContent(currentRepoId, filePath);
      }
      return;
    }
  });
}

// Load File Content via API
function loadFileContent(repoId, filePath) {
  const contentBody = document.getElementById("trainingContentBody");
  const fileNameElem = document.getElementById("contentFileName");
  const filePathElem = document.getElementById("contentFilePath");

  if (!contentBody) return;

  contentBody.innerHTML = `
    <div style="text-align:center; padding:3rem; color:var(--text-muted);">
      <i class="fa-solid fa-spinner fa-spin fa-2x" style="color:var(--primary); margin-bottom:1rem;"></i>
      <p>Loading document content...</p>
    </div>
  `;

  fetch(`/api/training/file?repo_id=${encodeURIComponent(repoId)}&path=${encodeURIComponent(filePath)}`)
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        contentBody.innerHTML = `<div class="toast toast-danger" style="display:inline-flex;">${data.error}</div>`;
        return;
      }

      currentFilePath = filePath;
      if (fileNameElem) fileNameElem.textContent = data.filename;
      if (filePathElem) filePathElem.textContent = `${repoId} / ${data.path}`;

      if (data.is_image) {
        contentBody.innerHTML = `
          <div style="text-align:center; padding:1.5rem;">
            <img src="${data.raw_url}" alt="${data.filename}" class="lightbox-trigger-img" style="max-width:100%; border-radius:var(--radius-md); box-shadow:var(--shadow-md); cursor:zoom-in;">
            <p style="margin-top:0.75rem; font-size:0.85rem; color:var(--text-muted);"><i class="fa-solid fa-magnifying-glass-plus"></i> Click image to open in interactive zoom lightbox</p>
          </div>
        `;
      } else {
        // Render Markdown
        // Using simple markdown parser or HTML from backend
        let html = marked.parse(data.formatted_content || data.raw_content);
        contentBody.innerHTML = `<div class="markdown-pane">${html}</div>`;
      }

      // Render mermaid flowcharts
      renderMermaidDiagrams();
      // Bind click handlers to images
      bindContentImagesForLightbox();
    })
    .catch(err => {
      contentBody.innerHTML = `<p style="color:var(--danger);">Failed to load file: ${err.message}</p>`;
    });
}

// Mermaid.js Flowchart Renderer
function renderMermaidDiagrams() {
  if (window.mermaid) {
    try {
      mermaid.initialize({
        startOnLoad: true,
        theme: "default",
        securityLevel: "loose"
      });
      mermaid.run({
        nodes: document.querySelectorAll(".mermaid")
      });
    } catch (e) {
      console.warn("Mermaid render error:", e);
    }
  }
}

// Sidebar File Search Filter
function initSidebarSearch() {
  const searchInput = document.getElementById("treeSearchInput");
  if (!searchInput) return;

  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    const allNodes = document.querySelectorAll(".tree-node.file");

    allNodes.forEach(node => {
      const name = (node.querySelector(".tree-label")?.textContent || "").toLowerCase();
      if (!q || name.includes(q)) {
        node.style.display = "";
        // Expand parent folders if matching
        let parent = node.parentElement.closest(".tree-node.folder");
        while (parent) {
          parent.classList.add("expanded");
          parent = parent.parentElement.closest(".tree-node.folder");
        }
      } else {
        node.style.display = "none";
      }
    });
  });
}

// Repo Selector Switcher
function initRepoSelector() {
  const selectElem = document.getElementById("activeRepoSelect");
  if (!selectElem) return;

  selectElem.addEventListener("change", (e) => {
    currentRepoId = e.target.value;
    switchRepository(currentRepoId);
  });
}

function switchRepository(repoId) {
  currentRepoId = repoId;
  const container = document.getElementById("treeNodesContainer");
  if (!container) return;

  container.innerHTML = `
    <div style="text-align:center; padding:1.5rem; color:var(--text-muted); font-size:0.85rem;">
      <i class="fa-solid fa-spinner fa-spin" style="margin-right:0.4rem;"></i> Loading folder tree...
    </div>
  `;

  fetch(`/api/training/tree/${encodeURIComponent(repoId)}`)
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";
      if (data.children && data.children.length > 0) {
        data.children.forEach(child => {
          container.appendChild(createTreeNodeElement(child));
        });
      } else {
        container.innerHTML = `<p style="padding:1rem; color:var(--text-muted); font-size:0.85rem;">No files found in repository.</p>`;
      }
    })
    .catch(err => {
      container.innerHTML = `<p style="padding:1rem; color:var(--danger); font-size:0.85rem;">Error: ${err.message}</p>`;
    });
}

function createTreeNodeElement(node) {
  const item = document.createElement("div");

  if (node.type === "directory") {
    item.className = "tree-node folder";
    item.innerHTML = `
      <div class="tree-node-row">
        <span class="tree-arrow"><i class="fa-solid fa-chevron-right"></i></span>
        <i class="fa-solid fa-folder tree-icon"></i>
        <span class="tree-label">${node.name}</span>
      </div>
      <div class="tree-children"></div>
    `;

    const childrenContainer = item.querySelector(".tree-children");
    if (node.children) {
      node.children.forEach(child => {
        childrenContainer.appendChild(createTreeNodeElement(child));
      });
    }
  } else {
    item.className = "tree-node file";
    let icon = "fa-file-lines";
    if (["png", "jpg", "jpeg", "svg"].includes(node.extension)) icon = "fa-file-image";
    if (["yaml", "yml"].includes(node.extension)) icon = "fa-file-code";
    if (["sh", "bash"].includes(node.extension)) icon = "fa-terminal";

    item.innerHTML = `
      <div class="tree-node-row" data-file-path="${node.path}">
        <span class="tree-arrow"></span>
        <i class="fa-regular ${icon} tree-icon"></i>
        <span class="tree-label">${node.name}</span>
      </div>
    `;
  }

  return item;
}

// ------------------------------------------------------------------------------
// Interactive Image Lightbox Modal with Zoom, Scroll, Pan & Double Click
// ------------------------------------------------------------------------------
function initImageLightbox() {
  const modal = document.getElementById("imageLightboxModal");
  const closeBtn = document.getElementById("lightboxCloseBtn");
  const imgElem = document.getElementById("lightboxImage");
  const titleElem = document.getElementById("lightboxTitle");
  const viewport = document.getElementById("lightboxViewport");

  if (!modal || !imgElem) return;

  // 1. Close when clicking 'X' button
  if (closeBtn) {
    closeBtn.addEventListener("click", () => closeLightbox());
  }

  // 2. Close when clicking outside of the image area (on modal overlay or viewport)
  viewport.addEventListener("click", (e) => {
    if (e.target === viewport) {
      closeLightbox();
    }
  });

  // 3. Zoom In & Zoom Out with Mouse Scroll
  viewport.addEventListener("wheel", (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    applyLightboxZoom(lightboxZoom * zoomFactor);
  }, { passive: false });

  // 4. Double Click to Zoom In / Zoom Out
  imgElem.addEventListener("dblclick", (e) => {
    e.preventDefault();
    if (lightboxZoom > 1.2) {
      resetLightboxTransform();
    } else {
      applyLightboxZoom(2.2);
    }
  });

  // 5. Drag / Pan Image when zoomed
  viewport.addEventListener("mousedown", (e) => {
    if (e.target === imgElem && lightboxZoom > 1) {
      isPanning = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      viewport.style.cursor = "grabbing";
    }
  });

  window.addEventListener("mousemove", (e) => {
    if (isPanning) {
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      updateLightboxImageTransform();
    }
  });

  window.addEventListener("mouseup", () => {
    if (isPanning) {
      isPanning = false;
      viewport.style.cursor = "grab";
    }
  });

  // Magnifier Toolbar Buttons
  document.getElementById("btnZoomIn")?.addEventListener("click", () => applyLightboxZoom(lightboxZoom * 1.25));
  document.getElementById("btnZoomOut")?.addEventListener("click", () => applyLightboxZoom(lightboxZoom * 0.8));
  document.getElementById("btnZoomReset")?.addEventListener("click", () => resetLightboxTransform());
}

function bindContentImagesForLightbox() {
  document.querySelectorAll(".markdown-pane img, .lightbox-trigger-img").forEach(img => {
    img.style.cursor = "zoom-in";
    img.addEventListener("click", (e) => {
      e.stopPropagation();
      openLightbox(img.src, img.alt || "Image Preview");
    });
  });
}

function openLightbox(src, title) {
  const modal = document.getElementById("imageLightboxModal");
  const imgElem = document.getElementById("lightboxImage");
  const titleElem = document.getElementById("lightboxTitle");

  if (!modal || !imgElem) return;

  imgElem.src = src;
  if (titleElem) titleElem.textContent = title;
  resetLightboxTransform();

  modal.classList.add("active");
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  const modal = document.getElementById("imageLightboxModal");
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
    resetLightboxTransform();
  }
}

function applyLightboxZoom(newZoom) {
  lightboxZoom = Math.min(Math.max(newZoom, 0.4), 5.0);
  updateLightboxImageTransform();
}

function resetLightboxTransform() {
  lightboxZoom = 1;
  translateX = 0;
  translateY = 0;
  updateLightboxImageTransform();
}

function updateLightboxImageTransform() {
  const imgElem = document.getElementById("lightboxImage");
  if (imgElem) {
    imgElem.style.transform = `translate(${translateX}px, ${translateY}px) scale(${lightboxZoom})`;
  }
}

// ------------------------------------------------------------------------------
// Custom Public Repositories Manager (Saved in Browser Session / localStorage)
// ------------------------------------------------------------------------------
function initCustomReposManager() {
  const addRepoBtn = document.getElementById("openAddRepoModalBtn");
  const saveRepoBtn = document.getElementById("saveCustomRepoBtn");

  if (addRepoBtn) {
    addRepoBtn.addEventListener("click", () => {
      openModal("addRepoModal");
    });
  }

  if (saveRepoBtn) {
    saveRepoBtn.addEventListener("click", () => {
      saveCustomRepo();
    });
  }

  loadCustomReposIntoDropdown();
}

function getStoredCustomRepos() {
  try {
    return JSON.parse(localStorage.getItem("devops_hub_custom_repos") || "[]");
  } catch (e) {
    return [];
  }
}

function loadCustomReposIntoDropdown() {
  const selectElem = document.getElementById("activeRepoSelect");
  if (!selectElem) return;

  const customRepos = getStoredCustomRepos();
  // Remove previously appended custom options
  const defaultOptionsCount = 2; // training & notes
  while (selectElem.options.length > defaultOptionsCount) {
    selectElem.remove(defaultOptionsCount);
  }

  customRepos.forEach(repo => {
    const opt = document.createElement("option");
    opt.value = `custom_${repo.id}`;
    opt.textContent = `⭐ ${repo.name}`;
    selectElem.appendChild(opt);
  });
}

function saveCustomRepo() {
  const urlInput = document.getElementById("customRepoUrlInput");
  const nameInput = document.getElementById("customRepoNameInput");
  const branchInput = document.getElementById("customRepoBranchInput");

  if (!urlInput || !urlInput.value.trim()) {
    showToast("Please enter a valid GitHub repository URL", "warning");
    return;
  }

  const url = urlInput.value.trim();
  const name = nameInput?.value.trim() || url.split("/").pop().replace(".git", "");
  const branch = branchInput?.value.trim() || "main";

  const customRepos = getStoredCustomRepos();
  const repoId = `repo_${Date.now()}`;
  customRepos.push({
    id: repoId,
    name: name,
    url: url,
    branch: branch
  });

  localStorage.setItem("devops_hub_custom_repos", JSON.stringify(customRepos));
  showToast(`Added '${name}' to session!`, "success");

  closeModal("addRepoModal");
  urlInput.value = "";
  if (nameInput) nameInput.value = "";

  loadCustomReposIntoDropdown();

  // Switch to newly added repo
  const selectElem = document.getElementById("activeRepoSelect");
  if (selectElem) {
    selectElem.value = `custom_${repoId}`;
    loadLiveCustomRepo(url, branch, name);
  }
}

function loadLiveCustomRepo(url, branch, name) {
  const contentBody = document.getElementById("trainingContentBody");
  const treeContainer = document.getElementById("treeNodesContainer");

  if (contentBody) {
    contentBody.innerHTML = `
      <div style="text-align:center; padding:3rem;">
        <i class="fa-solid fa-spinner fa-spin fa-2x" style="color:var(--primary); margin-bottom:1rem;"></i>
        <p>Fetching live files from GitHub: <strong>${url}</strong>...</p>
      </div>
    `;
  }

  fetch(`/api/training/custom-repo?repo_url=${encodeURIComponent(url)}&branch=${encodeURIComponent(branch)}`)
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        if (contentBody) contentBody.innerHTML = `<div class="toast toast-danger">${data.error}</div>`;
        return;
      }

      if (treeContainer) {
        treeContainer.innerHTML = `
          <div class="tree-node file">
            <div class="tree-node-row active">
              <i class="fa-regular fa-file-lines tree-icon"></i>
              <span class="tree-label">README.md (Live)</span>
            </div>
          </div>
        `;
      }

      if (contentBody) {
        let html = marked.parse(data.formatted_content || data.raw_content);
        contentBody.innerHTML = `<div class="markdown-pane">${html}</div>`;
        renderMermaidDiagrams();
        bindContentImagesForLightbox();
      }
    })
    .catch(err => {
      if (contentBody) contentBody.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    });
}

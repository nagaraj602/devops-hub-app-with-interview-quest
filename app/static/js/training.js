/* ==============================================================================
   Training Materials & Notes Explorer JavaScript: Multi-Repo Tree, Full-Text Search,
   Match Navigation & Image Lightbox
   ============================================================================== */

let currentRepoId = "training";
let currentFilePath = "README.md";

// Full-Text Search & Match Navigator State
let currentMatchIndex = 0;
let totalMatches = 0;
let activeSearchQuery = "";
let searchDebounceTimer = null;

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
  initSidebarSearchAndFilter();
  initMatchNavigator();
  renderMermaidDiagrams();
  bindContentImagesForLightbox();
}

// ------------------------------------------------------------------------------
// Tree Node Expand / Collapse and Multi-Repo File Loading
// ------------------------------------------------------------------------------
function initTreeNodeClicks() {
  document.addEventListener("click", (e) => {
    // 1. Folder Click (Toggle Expand / Collapse)
    const folderRow = e.target.closest(".tree-node.folder > .tree-node-row");
    if (folderRow) {
      const node = folderRow.closest(".tree-node");
      node.classList.toggle("expanded");
      return;
    }

    // 2. File Click (Load Document)
    const fileRow = e.target.closest(".tree-node.file > .tree-node-row");
    if (fileRow) {
      document.querySelectorAll(".tree-node-row").forEach(r => r.classList.remove("active"));
      fileRow.classList.add("active");

      if (fileRow.getAttribute("data-is-custom") === "true") {
        const url = fileRow.getAttribute("data-custom-url");
        const branch = fileRow.getAttribute("data-custom-branch") || "main";
        const name = fileRow.getAttribute("data-custom-name");
        const filePath = fileRow.getAttribute("data-file-path") || "README.md";
        loadLiveCustomRepo(url, branch, name, filePath);
        return;
      }

      // Detect repo_id from node attribute, or walk up to parent repo root
      let repoId = fileRow.getAttribute("data-repo-id");
      if (!repoId) {
        const repoRoot = fileRow.closest(".repo-root-folder");
        repoId = repoRoot ? repoRoot.getAttribute("data-repo-id") : currentRepoId;
      }
      const filePath = fileRow.getAttribute("data-file-path");

      if (filePath) {
        loadFileContent(repoId || "training", filePath);
      }
      return;
    }
  });
}

// ------------------------------------------------------------------------------
function resetTrainingScroll() {
  window.scrollTo({ top: 0, behavior: "instant" });
  const contentBody = document.getElementById("trainingContentBody");
  if (contentBody) contentBody.scrollTop = 0;
  const contentViewer = document.querySelector(".content-viewer-card");
  if (contentViewer) contentViewer.scrollTop = 0;
  const mainContent = document.querySelector(".main-content");
  if (mainContent) mainContent.scrollTop = 0;
}

// Load File Content via API & Render Markdown
// ------------------------------------------------------------------------------
function loadFileContent(repoId, filePath, searchQuery = null) {
  const contentBody = document.getElementById("trainingContentBody");
  const fileNameElem = document.getElementById("contentFileName");
  const filePathElem = document.getElementById("contentFilePath");

  if (!contentBody) return;

  currentRepoId = repoId;
  currentFilePath = filePath;

  // Reset scroll position to top of viewer immediately
  resetTrainingScroll();

  // Highlight active tree file node
  document.querySelectorAll(".tree-node.file > .tree-node-row").forEach(row => {
    const rId = row.getAttribute("data-repo-id") || row.closest(".repo-root-folder")?.getAttribute("data-repo-id");
    const fPath = row.getAttribute("data-file-path");
    if (rId === repoId && fPath === filePath) {
      row.classList.add("active");
      // Expand parents
      let parent = row.parentElement.closest(".tree-node.folder");
      while (parent) {
        parent.classList.add("expanded");
        parent = parent.parentElement.closest(".tree-node.folder");
      }
    } else {
      row.classList.remove("active");
    }
  });

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

      if (fileNameElem) fileNameElem.textContent = data.filename;
      if (filePathElem) filePathElem.textContent = `${repoId} / ${data.path}`;

      if (data.is_image) {
        contentBody.innerHTML = `
          <div style="text-align:center; padding:1.5rem;">
            <img src="${data.raw_url}" alt="${data.filename}" class="lightbox-trigger-img" style="max-width:100%; border-radius:var(--radius-md); box-shadow:var(--shadow-md); cursor:zoom-in;">
            <p style="margin-top:0.75rem; font-size:0.85rem; color:var(--text-muted);"><i class="fa-solid fa-magnifying-glass-plus"></i> Click image to open in interactive zoom lightbox</p>
          </div>
        `;
        hideSearchNavigator();
        resetTrainingScroll();
      } else {
        // Render Markdown via marked
        let html = marked.parse(data.formatted_content || data.raw_content);
        contentBody.innerHTML = `<div class="markdown-pane">${html}</div>`;

        // If search query is active, apply in-page highlighting and navigation
        if (searchQuery && searchQuery.trim().length >= 2) {
          highlightSearchMatches(searchQuery);
        } else {
          hideSearchNavigator();
          resetTrainingScroll();
        }

        postProcessMarkdownContent(contentBody, repoId, filePath);
      }
    })
    .catch(err => {
      contentBody.innerHTML = `<p style="color:var(--danger); padding:2rem;">Failed to load file: ${err.message}</p>`;
      hideSearchNavigator();
    });
}

function postProcessMarkdownContent(contentBody, repoId, filePath) {
  if (!contentBody) return;

  // 1. Highlight code blocks and attach copy buttons
  contentBody.querySelectorAll("pre code").forEach(block => {
    if (window.hljs) {
      hljs.highlightElement(block);
    }
    const pre = block.parentElement;
    if (pre && !pre.querySelector(".code-copy-btn")) {
      pre.style.position = "relative";
      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "code-copy-btn";
      copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
      copyBtn.title = "Copy Code";
      copyBtn.onclick = (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(block.innerText).then(() => {
          copyBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
          setTimeout(() => { copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>'; }, 2000);
        });
      };
      pre.appendChild(copyBtn);
    }
  });

  // 2. Intercept relative .md links
  contentBody.querySelectorAll(".markdown-pane a").forEach(link => {
    const href = link.getAttribute("href");
    if (!href) return;
    if (!href.startsWith("http://") && !href.startsWith("https://") && !href.startsWith("#") && (href.endsWith(".md") || href.includes(".md#"))) {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        let targetPath = href.split("#")[0].replace(/^\.\//, "");
        let baseFolder = filePath.includes("/") ? filePath.substring(0, filePath.lastIndexOf("/")) : "";
        let resolvedPath = baseFolder ? `${baseFolder}/${targetPath}` : targetPath;
        
        const parts = resolvedPath.split("/");
        const cleanParts = [];
        for (const p of parts) {
          if (p === "..") cleanParts.pop();
          else if (p && p !== ".") cleanParts.push(p);
        }
        resolvedPath = cleanParts.join("/");

        if (repoId.startsWith("custom_")) {
          const customRepos = getStoredCustomRepos();
          const cr = customRepos.find(r => `custom_${r.id}` === repoId || `custom_${r.name}` === repoId);
          if (cr) {
            loadLiveCustomRepo(cr.url, cr.branch, cr.name, resolvedPath);
            return;
          }
        }
        loadFileContent(repoId, resolvedPath);
      });
    }
  });

  // 3. Render mermaid flowcharts
  renderMermaidDiagrams();

  // 4. Bind click handlers to images
  bindContentImagesForLightbox();
}

// ------------------------------------------------------------------------------
// Mermaid.js Flowchart Renderer
// ------------------------------------------------------------------------------
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

// ------------------------------------------------------------------------------
// Sidebar File Filter & Full-Text Search Engine
// ------------------------------------------------------------------------------
function initSidebarSearchAndFilter() {
  const searchInput = document.getElementById("treeSearchInput");
  const clearBtn = document.getElementById("searchClearBtn");
  const resultsPanel = document.getElementById("searchResultsPanel");
  const closeResultsBtn = document.getElementById("closeSearchResultsBtn");
  const resultsList = document.getElementById("searchResultsList");
  const resultsCount = document.getElementById("searchResultsCount");

  if (!searchInput) return;

  // Real-time input handling
  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.trim();

    if (clearBtn) {
      clearBtn.style.display = q ? "block" : "none";
    }

    // 1. Instant Tree Filename Filtering
    filterTreeNodes(q);

    // 2. Debounced Full-Text Search across files
    clearTimeout(searchDebounceTimer);
    if (q.length >= 2) {
      searchDebounceTimer = setTimeout(() => {
        performFullTextSearch(q);
      }, 350);
    } else {
      if (resultsPanel) resultsPanel.style.display = "none";
    }
  });

  // Clear button click
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      searchInput.value = "";
      clearBtn.style.display = "none";
      filterTreeNodes("");
      if (resultsPanel) resultsPanel.style.display = "none";
      hideSearchNavigator();
      removeSearchHighlights();
    });
  }

  // Close search results panel
  if (closeResultsBtn) {
    closeResultsBtn.addEventListener("click", () => {
      if (resultsPanel) resultsPanel.style.display = "none";
    });
  }

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    if (resultsPanel && !resultsPanel.contains(e.target) && e.target !== searchInput) {
      resultsPanel.style.display = "none";
    }
  });
}

function filterTreeNodes(query) {
  const q = query.toLowerCase().trim();
  const allFileNodes = document.querySelectorAll(".tree-node.file");

  allFileNodes.forEach(node => {
    const name = (node.querySelector(".tree-label")?.textContent || "").toLowerCase();
    if (!q || name.includes(q)) {
      node.style.display = "";
      // Expand parent folders
      if (q) {
        let parent = node.parentElement.closest(".tree-node.folder");
        while (parent) {
          parent.classList.add("expanded");
          parent = parent.parentElement.closest(".tree-node.folder");
        }
      }
    } else {
      node.style.display = "none";
    }
  });
}

function performFullTextSearch(query) {
  const resultsPanel = document.getElementById("searchResultsPanel");
  const resultsList = document.getElementById("searchResultsList");
  const resultsCount = document.getElementById("searchResultsCount");

  if (!resultsPanel || !resultsList) return;

  resultsPanel.style.display = "block";
  resultsList.innerHTML = `
    <div style="padding:1rem; text-align:center; color:var(--text-muted); font-size:0.82rem;">
      <i class="fa-solid fa-spinner fa-spin" style="color:var(--primary); margin-right:0.4rem;"></i> Searching across curriculum and notes...
    </div>
  `;

  fetch(`/api/training/search?q=${encodeURIComponent(query)}`)
    .then(res => res.json())
    .then(results => {
      if (!results || results.length === 0) {
        resultsCount.textContent = "0 results found";
        resultsList.innerHTML = `
          <div style="padding:1rem; text-align:center; color:var(--text-muted); font-size:0.82rem;">
            No occurrences found for "<strong>${escapeHtml(query)}</strong>"
          </div>
        `;
        return;
      }

      resultsCount.textContent = `${results.length} file${results.length === 1 ? '' : 's'} matched`;
      resultsList.innerHTML = "";

      results.forEach(res => {
        const item = document.createElement("div");
        item.className = "search-result-item";

        let snippetText = "";
        if (res.snippets && res.snippets.length > 0) {
          snippetText = res.snippets[0].text;
        }

        item.innerHTML = `
          <div class="search-result-title">
            <span><i class="fa-regular fa-file-lines" style="color:var(--primary); margin-right:0.35rem;"></i>${escapeHtml(res.filename)}</span>
            <span class="badge badge-outline" style="font-size:0.68rem;">${res.match_count} match${res.match_count === 1 ? '' : 'es'}</span>
          </div>
          <div class="search-result-path">${escapeHtml(res.repo_name)} &bull; ${escapeHtml(res.file_path)}</div>
          ${snippetText ? `<div class="search-result-snippet">${highlightSubstr(escapeHtml(snippetText), query)}</div>` : ''}
        `;

        item.addEventListener("click", () => {
          resultsPanel.style.display = "none";
          loadFileContent(res.repo_id, res.file_path, query);
        });

        resultsList.appendChild(item);
      });
    })
    .catch(err => {
      resultsList.innerHTML = `<div style="padding:1rem; color:var(--danger); font-size:0.82rem;">Search error: ${err.message}</div>`;
    });
}

// ------------------------------------------------------------------------------
// In-Document Text Highlighting & Floating Match Navigator
// ------------------------------------------------------------------------------
function initMatchNavigator() {
  const prevBtn = document.getElementById("prevMatchBtn");
  const nextBtn = document.getElementById("nextMatchBtn");
  const closeBtn = document.getElementById("closeSearchNavBtn");

  if (prevBtn) {
    prevBtn.addEventListener("click", () => goToMatch(currentMatchIndex - 1));
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", () => goToMatch(currentMatchIndex + 1));
  }
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      hideSearchNavigator();
      removeSearchHighlights();
    });
  }

  // Keyboard navigation: Enter -> Next, Shift+Enter -> Prev, Esc -> Close
  document.addEventListener("keydown", (e) => {
    const nav = document.getElementById("searchMatchNavigator");
    if (nav && nav.style.display !== "none") {
      if (e.key === "Enter") {
        e.preventDefault();
        if (e.shiftKey) {
          goToMatch(currentMatchIndex - 1);
        } else {
          goToMatch(currentMatchIndex + 1);
        }
      } else if (e.key === "Escape") {
        hideSearchNavigator();
        removeSearchHighlights();
      }
    }
  });
}

function highlightSearchMatches(query) {
  removeSearchHighlights();
  activeSearchQuery = query;

  const pane = document.querySelector("#trainingContentBody .markdown-pane");
  if (!pane || !query || query.trim().length < 2) {
    hideSearchNavigator();
    return;
  }

  const regex = new RegExp(`(${escapeRegExp(query)})`, "gi");
  let matchCount = 0;

  function walk(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      if (node.parentNode) {
        const parentTag = node.parentNode.tagName;
        if (["SCRIPT", "STYLE"].includes(parentTag) || node.parentNode.closest(".mermaid")) {
          return;
        }
      }
      const val = node.nodeValue;
      if (regex.test(val)) {
        const span = document.createElement("span");
        span.innerHTML = val.replace(regex, (m) => {
          matchCount++;
          return `<mark class="search-highlight" data-match-idx="${matchCount}">${m}</mark>`;
        });
        node.parentNode.replaceChild(span, node);
      }
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      if (node.classList.contains("mermaid")) return;
      Array.from(node.childNodes).forEach(walk);
    }
  }

  walk(pane);

  totalMatches = matchCount;

  if (totalMatches > 0) {
    showSearchNavigator(totalMatches, query);
    goToMatch(1);
  } else {
    hideSearchNavigator();
  }
}

function goToMatch(index) {
  const marks = document.querySelectorAll("mark.search-highlight");
  if (!marks.length) return;

  if (index < 1) index = marks.length;
  if (index > marks.length) index = 1;
  currentMatchIndex = index;

  marks.forEach(m => m.classList.remove("active-match"));
  const target = marks[index - 1];
  if (target) {
    target.classList.add("active-match");

    // Expand parent <details> accordion if match is collapsed inside a question answer
    let parentDetails = target.closest("details");
    while (parentDetails) {
      parentDetails.open = true;
      parentDetails = parentDetails.parentElement.closest("details");
    }

    target.scrollIntoView({ behavior: "smooth", block: "center" });

    const currNum = document.getElementById("currentMatchNumber");
    if (currNum) currNum.textContent = index;
  }
}

function showSearchNavigator(total, query) {
  const nav = document.getElementById("searchMatchNavigator");
  const currNum = document.getElementById("currentMatchNumber");
  const totNum = document.getElementById("totalMatchNumber");
  const badge = document.getElementById("searchNavQueryBadge");

  if (!nav) return;
  if (currNum) currNum.textContent = 1;
  if (totNum) totNum.textContent = total;
  if (badge) badge.textContent = `"${query}"`;

  nav.style.display = "flex";
}

function hideSearchNavigator() {
  const nav = document.getElementById("searchMatchNavigator");
  if (nav) nav.style.display = "none";
}

function removeSearchHighlights() {
  document.querySelectorAll("mark.search-highlight").forEach(mark => {
    const parent = mark.parentNode;
    parent.replaceChild(document.createTextNode(mark.textContent), mark);
    parent.normalize();
  });
  currentMatchIndex = 0;
  totalMatches = 0;
}

// ------------------------------------------------------------------------------
// Interactive Image Lightbox Modal with Zoom, Scroll, Pan & Double Click
// ------------------------------------------------------------------------------
function initImageLightbox() {
  const modal = document.getElementById("imageLightboxModal");
  const closeBtn = document.getElementById("lightboxCloseBtn");
  const imgElem = document.getElementById("lightboxImage");
  const viewport = document.getElementById("lightboxViewport");

  if (!modal || !imgElem || !viewport) return;

  if (closeBtn) {
    closeBtn.addEventListener("click", () => closeLightbox());
  }

  viewport.addEventListener("click", (e) => {
    if (e.target === viewport) {
      closeLightbox();
    }
  });

  viewport.addEventListener("wheel", (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    applyLightboxZoom(lightboxZoom * zoomFactor);
  }, { passive: false });

  imgElem.addEventListener("dblclick", (e) => {
    e.preventDefault();
    if (lightboxZoom > 1.2) {
      resetLightboxTransform();
    } else {
      applyLightboxZoom(2.2);
    }
  });

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

  loadCustomReposIntoTree();
}

function getStoredCustomRepos() {
  try {
    return JSON.parse(localStorage.getItem("devops_hub_custom_repos") || "[]");
  } catch (e) {
    return [];
  }
}

function renderRecursiveCustomNodes(nodes, repoId, repoUrl, repoBranch, repoName) {
  let html = '';
  nodes.forEach(node => {
    if (node.type === "directory") {
      html += `
        <div class="tree-node folder">
          <div class="tree-node-row">
            <span class="tree-arrow"><i class="fa-solid fa-chevron-right"></i></span>
            <i class="fa-solid fa-folder tree-icon folder-icon"></i>
            <span class="tree-label">${escapeHtml(node.name)}</span>
          </div>
          <div class="tree-children">
            ${renderRecursiveCustomNodes(node.children || [], repoId, repoUrl, repoBranch, repoName)}
          </div>
        </div>
      `;
    } else {
      html += `
        <div class="tree-node file">
          <div class="tree-node-row" data-repo-id="${repoId}" data-file-path="${escapeHtml(node.path)}" data-is-custom="true" data-custom-url="${escapeHtml(repoUrl)}" data-custom-branch="${escapeHtml(repoBranch)}" data-custom-name="${escapeHtml(repoName)}">
            <span class="tree-arrow"></span>
            <i class="fa-regular fa-file-lines tree-icon"></i>
            <span class="tree-label">${escapeHtml(node.name)}</span>
          </div>
        </div>
      `;
    }
  });
  return html;
}

function loadCustomReposIntoTree() {
  const treeContainer = document.getElementById("treeNodesContainer");
  if (!treeContainer) return;

  const customRepos = getStoredCustomRepos();
  customRepos.forEach(repo => {
    const repoId = `custom_${repo.id}`;
    if (document.querySelector(`.repo-root-folder[data-repo-id="${repoId}"]`)) return;

    const rootNode = document.createElement("div");
    rootNode.className = "tree-node folder repo-root-folder expanded";
    rootNode.setAttribute("data-repo-id", repoId);
    rootNode.innerHTML = `
      <div class="tree-node-row repo-root-row">
        <span class="tree-arrow"><i class="fa-solid fa-chevron-right"></i></span>
        <i class="fa-brands fa-github tree-icon" style="color:var(--primary);"></i>
        <span class="tree-label" style="font-weight:700;">${escapeHtml(repo.name)}</span>
        <span class="badge badge-outline" style="font-size:0.68rem; margin-left:auto;">CUSTOM</span>
      </div>
      <div class="tree-children" id="customTreeChildren_${repo.id}">
        <div style="padding:0.5rem 1rem; color:var(--text-muted); font-size:0.8rem;">
          <i class="fa-solid fa-spinner fa-spin"></i> Fetching repository tree...
        </div>
      </div>
    `;
    treeContainer.appendChild(rootNode);

    // Fetch recursive tree via API
    fetch(`/api/training/custom-tree?repo_url=${encodeURIComponent(repo.url)}&branch=${encodeURIComponent(repo.branch)}`)
      .then(r => r.json())
      .then(data => {
        const childrenContainer = document.getElementById(`customTreeChildren_${repo.id}`);
        if (!childrenContainer) return;
        if (data.error || !data.tree || data.tree.length === 0) {
          childrenContainer.innerHTML = `
            <div class="tree-node file">
              <div class="tree-node-row" data-repo-id="${repoId}" data-file-path="README.md" data-is-custom="true" data-custom-url="${escapeHtml(repo.url)}" data-custom-branch="${escapeHtml(repo.branch)}" data-custom-name="${escapeHtml(repo.name)}">
                <span class="tree-arrow"></span>
                <i class="fa-regular fa-file-lines tree-icon"></i>
                <span class="tree-label">README.md (Live)</span>
              </div>
            </div>
          `;
        } else {
          childrenContainer.innerHTML = renderRecursiveCustomNodes(data.tree, repoId, repo.url, data.branch || repo.branch, repo.name);
        }
      })
      .catch(() => {
        const childrenContainer = document.getElementById(`customTreeChildren_${repo.id}`);
        if (childrenContainer) {
          childrenContainer.innerHTML = `
            <div class="tree-node file">
              <div class="tree-node-row" data-repo-id="${repoId}" data-file-path="README.md" data-is-custom="true" data-custom-url="${escapeHtml(repo.url)}" data-custom-branch="${escapeHtml(repo.branch)}" data-custom-name="${escapeHtml(repo.name)}">
                <span class="tree-arrow"></span>
                <i class="fa-regular fa-file-lines tree-icon"></i>
                <span class="tree-label">README.md (Live)</span>
              </div>
            </div>
          `;
        }
      });
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

  loadCustomReposIntoTree();
  loadLiveCustomRepo(url, branch, name, "README.md");
}

function loadLiveCustomRepo(url, branch, name, filePath = "README.md") {
  const contentBody = document.getElementById("trainingContentBody");
  const fileNameElem = document.getElementById("contentFileName");
  const filePathElem = document.getElementById("contentFilePath");

  currentRepoId = `custom_${name}`;
  currentFilePath = filePath;

  resetTrainingScroll();

  if (contentBody) {
    contentBody.innerHTML = `
      <div style="text-align:center; padding:3rem;">
        <i class="fa-solid fa-spinner fa-spin fa-2x" style="color:var(--primary); margin-bottom:1rem;"></i>
        <p>Fetching live file: <strong>${escapeHtml(filePath)}</strong> from <strong>${escapeHtml(name)}</strong>...</p>
      </div>
    `;
  }

  const baseFileName = filePath.split("/").pop();
  if (fileNameElem) fileNameElem.textContent = `${baseFileName} (Live)`;
  if (filePathElem) filePathElem.textContent = `${name} / ${filePath}`;

  fetch(`/api/training/custom-repo?repo_url=${encodeURIComponent(url)}&branch=${encodeURIComponent(branch)}&file_path=${encodeURIComponent(filePath)}`)
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        if (contentBody) contentBody.innerHTML = `<div class="toast toast-danger">${data.error}</div>`;
        return;
      }

      if (contentBody) {
        let html = marked.parse(data.formatted_content || data.raw_content);
        contentBody.innerHTML = `<div class="markdown-pane">${html}</div>`;
        resetTrainingScroll();
        postProcessMarkdownContent(contentBody, `custom_${name}`, filePath);
      }
    })
    .catch(err => {
      if (contentBody) contentBody.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    });
}

// ------------------------------------------------------------------------------
// Utility Helpers
// ------------------------------------------------------------------------------
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function highlightSubstr(escapedText, query) {
  if (!query) return escapedText;
  const regex = new RegExp(`(${escapeRegExp(escapeHtml(query))})`, "gi");
  return escapedText.replace(regex, '<mark style="background:#fef08a; font-weight:700;">$1</mark>');
}

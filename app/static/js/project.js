/* ==============================================================================
   Project Page JavaScript: Interactive EKS Cluster Sizing Calculator & Q&A
   ============================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  initClusterCalculator();
});

const INSTANCE_PROFILES = {
  "m6i.4xlarge": { vcpu: 16, ram: 64, allocatable_cpu: 14, allocatable_ram: 58, name: "General Purpose (m6i.4xlarge - Standard)" },
  "c6i.4xlarge": { vcpu: 16, ram: 32, allocatable_cpu: 14, allocatable_ram: 28, name: "Compute Optimized (c6i.4xlarge)" },
  "m6i.8xlarge": { vcpu: 32, ram: 128, allocatable_cpu: 29, allocatable_ram: 118, name: "Large Scale (m6i.8xlarge)" }
};

function initClusterCalculator() {
  const cpuSlider = document.getElementById("calcCpuSlider");
  const ramRatioSlider = document.getElementById("calcRamRatioSlider");
  const instanceSelect = document.getElementById("calcInstanceSelect");
  const azSelect = document.getElementById("calcAzSelect");

  if (!cpuSlider) return;

  const updateCalculations = () => {
    const targetCpu = parseInt(cpuSlider.value, 10);
    const ramRatio = parseFloat(ramRatioSlider.value);
    const instanceKey = instanceSelect ? instanceSelect.value : "m6i.4xlarge";
    const azCount = azSelect ? parseInt(azSelect.value, 10) : 3;

    const inst = INSTANCE_PROFILES[instanceKey] || INSTANCE_PROFILES["m6i.4xlarge"];

    // Update displayed slider values
    const cpuValEl = document.getElementById("calcCpuVal");
    if (cpuValEl) cpuValEl.textContent = `${targetCpu} vCPUs`;
    
    const ramRatioValEl = document.getElementById("calcRamRatioVal");
    if (ramRatioValEl) ramRatioValEl.textContent = `${ramRatio.toFixed(1)} GB / core`;

    // RAM demand
    const targetRamGb = Math.round(targetCpu * ramRatio);

    // Nodes needed by CPU
    const nodesByCpu = Math.ceil(targetCpu / inst.allocatable_cpu);
    // Nodes needed by RAM
    const nodesByRam = Math.ceil(targetRamGb / inst.allocatable_ram);
    const baseNodesNeeded = Math.max(nodesByCpu, nodesByRam);

    // High availability buffer: round up to multiple of AZs + 1 node per AZ buffer
    const nodesPerAzBase = Math.ceil(baseNodesNeeded / azCount);
    // Add 1 spare node per AZ for rolling upgrades & burst
    const nodesPerAzFinal = nodesPerAzBase + 1;
    const totalNodes = nodesPerAzFinal * azCount;

    const totalVcpu = totalNodes * inst.vcpu;
    const totalRam = totalNodes * inst.ram;
    const cpuHeadroom = Math.round(((totalVcpu - targetCpu) / totalVcpu) * 100);

    // Update UI Results
    const resTotalNodesEl = document.getElementById("resTotalNodes");
    if (resTotalNodesEl) resTotalNodesEl.textContent = totalNodes;

    const resNodesPerAzEl = document.getElementById("resNodesPerAz");
    if (resNodesPerAzEl) resNodesPerAzEl.textContent = `${nodesPerAzFinal} / AZ`;

    const resTotalVcpuEl = document.getElementById("resTotalVcpu");
    if (resTotalVcpuEl) resTotalVcpuEl.textContent = `${totalVcpu} vCPUs`;

    const resTotalRamEl = document.getElementById("resTotalRam");
    if (resTotalRamEl) resTotalRamEl.textContent = `${totalRam.toLocaleString()} GB`;

    const resHeadroomEl = document.getElementById("resHeadroom");
    if (resHeadroomEl) resHeadroomEl.textContent = `${cpuHeadroom}% Headroom`;

    const resTargetRamEl = document.getElementById("resTargetRam");
    if (resTargetRamEl) resTargetRamEl.textContent = `~${targetRamGb} GB RAM required`;

    // Update plain English formula banner
    const formulaBanner = document.getElementById("calcFormulaSentence");
    if (formulaBanner) {
      formulaBanner.innerHTML = `
        <i class="fa-solid fa-check-circle" style="color:var(--success); margin-right:0.35rem;"></i>
        <strong>Calculation:</strong> ${targetCpu} vCPUs &divide; ${inst.allocatable_cpu} usable = ${baseNodesNeeded} base nodes + ${azCount} HA buffer = <strong>${totalNodes} nodes</strong> (${nodesPerAzFinal} per AZ across ${azCount} AZs) with ${cpuHeadroom}% headroom.
      `;
    }
  };

  cpuSlider.addEventListener("input", updateCalculations);
  ramRatioSlider.addEventListener("input", updateCalculations);
  if (instanceSelect) instanceSelect.addEventListener("change", updateCalculations);
  if (azSelect) azSelect.addEventListener("change", updateCalculations);

  updateCalculations();
}

function togglePrepAccordion(accordionId) {
  const item = document.getElementById(accordionId);
  if (!item) return;

  // Check if text is currently selected by user
  const selectedText = window.getSelection().toString();
  if (selectedText && selectedText.length > 0) {
    return;
  }

  item.classList.toggle("expanded");
}

function toggleDeepDiveAnswer(cardId) {
  // If user is selecting text for copying, don't toggle
  const selectedText = window.getSelection().toString();
  if (selectedText && selectedText.length > 0) return;

  const card = document.getElementById(cardId);
  if (!card) return;
  const answerEl = card.querySelector(".highlight-qa-answer");
  const toggleBtn = card.querySelector(".toggle-ans-btn");
  const chevron = document.getElementById(`deepdive-chevron-${cardId}`);
  if (!answerEl) return;

  const isHidden = answerEl.style.display === "none" || window.getComputedStyle(answerEl).display === "none";
  if (isHidden) {
    answerEl.style.display = "block";
    card.classList.add("expanded");
    if (toggleBtn) {
      toggleBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i> Hide Answer';
    }
    if (chevron) {
      chevron.style.transform = "rotate(180deg)";
    }
  } else {
    answerEl.style.display = "none";
    card.classList.remove("expanded");
    if (toggleBtn) {
      toggleBtn.innerHTML = '<i class="fa-solid fa-eye"></i> Show Answer';
    }
    if (chevron) {
      chevron.style.transform = "rotate(0deg)";
    }
  }
}

function copyDeepDiveAnswer(cardId, event) {
  if (event) event.stopPropagation();
  const card = document.getElementById(cardId);
  if (!card) return;
  const answerEl = card.querySelector(".highlight-qa-answer");
  const text = answerEl ? answerEl.innerText : "";
  if (text) {
    copyText(text, event);
  }
}

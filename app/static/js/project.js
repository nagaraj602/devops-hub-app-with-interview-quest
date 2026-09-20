/* ==============================================================================
   Project Page JavaScript: Interactive EKS Cluster Sizing Calculator & Q&A
   ============================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  initClusterCalculator();
});

const INSTANCE_PROFILES = {
  "m6i.4xlarge": { vcpu: 16, ram: 64, allocatable_cpu: 14, allocatable_ram: 58, name: "General Purpose (m6i.4xlarge - Recommended)" },
  "c6i.4xlarge": { vcpu: 16, ram: 32, allocatable_cpu: 14, allocatable_ram: 28, name: "Compute Optimized (c6i.4xlarge)" },
  "m6i.8xlarge": { vcpu: 32, ram: 128, allocatable_cpu: 29, allocatable_ram: 118, name: "Large Scale (m6i.8xlarge)" },
  "r6i.4xlarge": { vcpu: 16, ram: 128, allocatable_cpu: 14, allocatable_ram: 118, name: "Memory Optimized (r6i.4xlarge)" }
};

function initClusterCalculator() {
  const cpuSlider = document.getElementById("calcCpuSlider");
  const ramRatioSlider = document.getElementById("calcRamRatioSlider");
  const msSlider = document.getElementById("calcMsSlider");
  const instanceSelect = document.getElementById("calcInstanceSelect");
  const azSelect = document.getElementById("calcAzSelect");

  if (!cpuSlider) return;

  const updateCalculations = () => {
    const targetCpu = parseInt(cpuSlider.value, 10);
    const ramRatio = parseFloat(ramRatioSlider.value);
    const msCount = parseInt(msSlider.value, 10);
    const instanceKey = instanceSelect.value;
    const azCount = parseInt(azSelect.value, 10);

    const inst = INSTANCE_PROFILES[instanceKey] || INSTANCE_PROFILES["m6i.4xlarge"];

    // Update displayed slider values
    document.getElementById("calcCpuVal").textContent = `${targetCpu} vCPUs`;
    document.getElementById("calcRamRatioVal").textContent = `${ramRatio.toFixed(1)} GB / core`;
    document.getElementById("calcMsVal").textContent = `${msCount} Services`;

    // RAM demand
    const targetRamGb = Math.round(targetCpu * ramRatio);

    // Nodes needed by CPU
    const nodesByCpu = Math.ceil(targetCpu / inst.allocatable_cpu);
    // Nodes needed by RAM
    const nodesByRam = Math.ceil(targetRamGb / inst.allocatable_ram);
    const baseNodesNeeded = Math.max(nodesByCpu, nodesByRam);

    // High availability buffer: round up to multiple of AZs + 1 node per AZ buffer
    const nodesPerAzBase = Math.ceil(baseNodesNeeded / azCount);
    // Add N+2 buffer (1 spare per AZ for rolling upgrades & burst)
    const nodesPerAzFinal = nodesPerAzBase + 1;
    const totalNodes = nodesPerAzFinal * azCount;

    const totalVcpu = totalNodes * inst.vcpu;
    const totalRam = totalNodes * inst.ram;
    const cpuHeadroom = Math.round(((totalVcpu - targetCpu) / totalVcpu) * 100);

    // Update UI Results
    document.getElementById("resTotalNodes").textContent = totalNodes;
    document.getElementById("resNodesPerAz").textContent = `${nodesPerAzFinal} / AZ`;
    document.getElementById("resTotalVcpu").textContent = `${totalVcpu} vCPUs`;
    document.getElementById("resTotalRam").textContent = `${totalRam.toLocaleString()} GB`;
    document.getElementById("resHeadroom").textContent = `${cpuHeadroom}% Headroom`;
    document.getElementById("resTargetRam").textContent = `~${targetRamGb} GB RAM required`;
  };

  cpuSlider.addEventListener("input", updateCalculations);
  ramRatioSlider.addEventListener("input", updateCalculations);
  msSlider.addEventListener("input", updateCalculations);
  instanceSelect.addEventListener("change", updateCalculations);
  azSelect.addEventListener("change", updateCalculations);

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

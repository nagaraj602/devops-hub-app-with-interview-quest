/**
 * ==============================================================================
 *  Cost Optimization Shutdown Controller
 *  Active from 10:30 PM IST (30:00 min countdown) to 11:00 PM IST (Shutdown)
 *  Offline Window: 11:00 PM IST to 6:00 AM IST (Auto-restart at 6:00 AM IST)
 * ==============================================================================
 */

(function () {
  'use strict';

  // Manual test override variables
  let testOverrideSeconds = null;

  /**
   * Helper: Calculates current time in Indian Standard Time (IST, UTC+5:30)
   */
  function getISTDate() {
    const now = new Date();
    const utcMs = now.getTime() + (now.getTimezoneOffset() * 60000);
    const istMs = utcMs + (5.5 * 3600000);
    return new Date(istMs);
  }

  /**
   * Formats seconds into MM:SS string
   */
  function formatSeconds(totalSeconds) {
    if (totalSeconds < 0) totalSeconds = 0;
    const mins = Math.floor(totalSeconds / 60);
    const secs = Math.floor(totalSeconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * Checks query parameters for test/demo mode (?test_shutdown=30 or ?test_shutdown=5)
   */
  function checkTestMode() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('test_shutdown')) {
      const mins = parseFloat(params.get('test_shutdown')) || 30;
      testOverrideSeconds = Math.round(mins * 60);
      console.log(`[Cost Optimization] Test mode enabled with ${mins} minutes (${testOverrideSeconds} seconds)`);
    }
  }

  /**
   * Core update loop executed every second
   */
  function updateMaintenanceBanner() {
    const banner = document.getElementById('cost-optimization-banner');
    if (!banner) return;

    const clockEl = document.getElementById('maintenance-countdown-clock');
    const titleEl = document.getElementById('maintenance-title');
    const descEl = document.getElementById('maintenance-desc');
    const iconEl = document.getElementById('maintenance-icon');
    const timerLabel = banner.querySelector('.timer-label');

    // Handle developer/interview test override
    if (testOverrideSeconds !== null) {
      banner.style.display = 'block';
      if (testOverrideSeconds > 0) {
        testOverrideSeconds--;
        if (clockEl) clockEl.textContent = formatSeconds(testOverrideSeconds);
        if (timerLabel) timerLabel.textContent = 'SHUTDOWN IN';
        if (titleEl) {
          titleEl.innerHTML = '<span class="badge-notice"><i class="fa-solid fa-circle-info"></i> Cost Optimization</span> <strong>Website Shutdown Notice</strong>';
        }
        if (descEl) {
          descEl.innerHTML = 'This website is getting shutdown for cost optimization. So it will come back at 6 am.';
        }
        
        if (testOverrideSeconds <= 300) {
          banner.classList.add('imminent-shutdown');
          banner.classList.remove('maintenance-offline');
          if (iconEl) iconEl.className = 'fa-solid fa-triangle-exclamation maintenance-pulse-icon';
        } else {
          banner.classList.remove('imminent-shutdown', 'maintenance-offline');
          if (iconEl) iconEl.className = 'fa-solid fa-clock-rotate-left maintenance-pulse-icon';
        }
      } else {
        if (clockEl) clockEl.textContent = '06:00 AM';
        banner.classList.add('maintenance-offline');
        banner.classList.remove('imminent-shutdown');
        if (timerLabel) timerLabel.textContent = 'RETURNS AT';
        if (iconEl) iconEl.className = 'fa-solid fa-moon maintenance-pulse-icon';
        if (titleEl) {
          titleEl.innerHTML = '<span class="badge-notice"><i class="fa-solid fa-moon"></i> Cost Optimization</span> <strong>Website Offline</strong>';
        }
        if (descEl) {
          descEl.innerHTML = 'This website is getting shutdown for cost optimization. So it will come back at 6 am.';
        }
      }
      return;
    }

    const istDate = getISTDate();
    const hours = istDate.getHours();
    const minutes = istDate.getMinutes();
    const seconds = istDate.getSeconds();

    // Check if within countdown window: 10:30 PM (22:30:00) to 10:59:59 PM (22:59:59)
    const isCountdownActive = (hours === 22 && minutes >= 30);

    // Check if within shutdown/maintenance window: 11:00 PM (23:00) to 5:59:59 AM (05:59:59)
    const isMaintenanceWindow = (hours >= 23 || hours < 6);

    if (isCountdownActive) {
      banner.style.display = 'block';

      // Remaining seconds until 23:00:00 IST
      const minutesRemaining = 59 - minutes;
      const secondsRemaining = 60 - seconds;
      const totalSecondsLeft = (minutesRemaining * 60) + secondsRemaining;

      if (clockEl) clockEl.textContent = formatSeconds(totalSecondsLeft);
      if (timerLabel) timerLabel.textContent = 'SHUTDOWN IN';

      if (titleEl) {
        titleEl.innerHTML = '<span class="badge-notice"><i class="fa-solid fa-circle-info"></i> Cost Optimization</span> <strong>Website Shutdown Notice</strong>';
      }
      if (descEl) {
        descEl.innerHTML = 'This website is getting shutdown for cost optimization. So it will come back at 6 am.';
      }

      // Imminent shutdown styling during the last 5 minutes
      if (totalSecondsLeft <= 300) {
        banner.classList.add('imminent-shutdown');
        banner.classList.remove('maintenance-offline');
        if (iconEl) iconEl.className = 'fa-solid fa-triangle-exclamation maintenance-pulse-icon';
      } else {
        banner.classList.remove('imminent-shutdown', 'maintenance-offline');
        if (iconEl) iconEl.className = 'fa-solid fa-clock-rotate-left maintenance-pulse-icon';
      }

    } else if (isMaintenanceWindow) {
      banner.style.display = 'block';
      banner.classList.add('maintenance-offline');
      banner.classList.remove('imminent-shutdown');

      if (iconEl) iconEl.className = 'fa-solid fa-moon maintenance-pulse-icon';
      if (timerLabel) timerLabel.textContent = 'RETURNS AT';
      if (clockEl) clockEl.textContent = '06:00 AM';

      if (titleEl) {
        titleEl.innerHTML = '<span class="badge-notice"><i class="fa-solid fa-moon"></i> Cost Optimization</span> <strong>Website Offline</strong>';
      }
      if (descEl) {
        descEl.innerHTML = 'This website is getting shutdown for cost optimization. So it will come back at 6 am.';
      }

    } else {
      // Normal operating hours (6:00 AM to 10:29:59 PM IST)
      banner.style.display = 'none';
      banner.classList.remove('imminent-shutdown', 'maintenance-offline');
    }
  }

  // Initialize once DOM is ready
  document.addEventListener('DOMContentLoaded', function () {
    checkTestMode();

    const banner = document.getElementById('cost-optimization-banner');
    const dismissBtn = document.getElementById('maintenance-dismiss-btn');

    if (dismissBtn && banner) {
      dismissBtn.addEventListener('click', function () {
        banner.style.display = 'none';
        sessionStorage.setItem('shutdown_banner_dismissed', Date.now());
      });
    }

    // Run immediately then tick every 1000ms
    updateMaintenanceBanner();
    setInterval(updateMaintenanceBanner, 1000);
  });

  // Developer / Interviewer Console Helper:
  // Allows testing the countdown at any time, e.g.: window.testShutdownTimer(30)
  window.testShutdownTimer = function (minutes) {
    const mins = typeof minutes === 'number' ? minutes : 30;
    testOverrideSeconds = Math.round(mins * 60);
    console.log(`[Cost Optimization] Testing shutdown countdown with ${mins} minutes.`);
    updateMaintenanceBanner();
  };

  window.resetShutdownTimer = function () {
    testOverrideSeconds = null;
    console.log(`[Cost Optimization] Reset to live IST system time.`);
    updateMaintenanceBanner();
  };

})();

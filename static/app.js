/**
 * FaceSwap — Frontend Logic
 * ─────────────────────────
 * Handles:
 *   - Drag-and-drop + click upload for both zones
 *   - Client-side validation (type + size)
 *   - Image preview on drop/select
 *   - POST /swap with FormData
 *   - Loading state management
 *   - Result display + download
 *   - Toast notifications
 *   - FAQ accordion
 *   - "Swap Again" reset
 */

(() => {
  'use strict';

  // ── Constants ──────────────────────────────────────────────
  const MAX_FILE_BYTES   = 10 * 1024 * 1024; // 10 MB
  const ALLOWED_TYPES    = new Set(['image/jpeg', 'image/png', 'image/webp']);
  const ALLOWED_EXT_RE   = /\.(jpe?g|png|webp)$/i;

  // ── State ──────────────────────────────────────────────────
  let sourceFile = null;
  let targetFile = null;

  // ── DOM refs ───────────────────────────────────────────────
  const sourceZone      = document.getElementById('source-zone');
  const targetZone      = document.getElementById('target-zone');
  const sourceInput     = document.getElementById('source-input');
  const targetInput     = document.getElementById('target-input');
  const sourcePreview   = document.getElementById('source-preview');
  const targetPreview   = document.getElementById('target-preview');
  const sourcePlaceholder = document.getElementById('source-placeholder');
  const targetPlaceholder = document.getElementById('target-placeholder');
  const sourceOverlay   = document.getElementById('source-overlay');
  const targetOverlay   = document.getElementById('target-overlay');
  const sourceBadge     = document.getElementById('source-badge');
  const targetBadge     = document.getElementById('target-badge');
  const swapBtn         = document.getElementById('swap-btn');
  const swapBtnLabel    = document.getElementById('swap-btn-label');
  const spinner         = document.getElementById('spinner');
  const enhanceToggle   = document.getElementById('enhance-toggle');
  const fileStatus      = document.getElementById('file-status');
  const resultArea      = document.getElementById('result-area');
  const resultImg       = document.getElementById('result-img');
  const downloadBtn     = document.getElementById('download-btn');
  const swapAgainBtn    = document.getElementById('swap-again-btn');
  const processingTime  = document.getElementById('processing-time');
  const toastContainer  = document.getElementById('toast-container');

  // ── Validation ─────────────────────────────────────────────
  function isValidFile(file) {
    const typeOk = ALLOWED_TYPES.has(file.type) || ALLOWED_EXT_RE.test(file.name);
    const sizeOk = file.size <= MAX_FILE_BYTES;
    return { typeOk, sizeOk };
  }

  // ── Toast ──────────────────────────────────────────────────
  function showToast(type, title, message, duration = 5000) {
    const icons = { error: '❌', success: '✅', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      <div class="toast-icon">${icons[type] || icons.info}</div>
      <div class="toast-body">
        <div class="toast-title">${title}</div>
        ${message ? `<div class="toast-message">${message}</div>` : ''}
      </div>`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = 'opacity .3s ease, transform .3s ease';
      toast.style.opacity    = '0';
      toast.style.transform  = 'translateX(20px)';
      setTimeout(() => toast.remove(), 320);
    }, duration);
  }

  // ── Preview ────────────────────────────────────────────────
  function setPreview(file, previewEl, placeholderEl, overlayEl, badgeEl, side) {
    const url = URL.createObjectURL(file);
    previewEl.src            = url;
    previewEl.style.display  = 'block';
    placeholderEl.style.display = 'none';
    overlayEl.style.display  = 'flex';

    // Show a simple "1 face" badge as UX feedback (actual detection is server-side)
    badgeEl.textContent    = '📷 Ready';
    badgeEl.style.display  = 'block';

    // Clean up the old object URL when the image loads
    previewEl.onload = () => {};
  }

  function clearZone(previewEl, placeholderEl, overlayEl, badgeEl) {
    previewEl.src            = '';
    previewEl.style.display  = 'none';
    placeholderEl.style.display = 'flex';
    overlayEl.style.display  = 'none';
    badgeEl.style.display    = 'none';
  }

  // ── Button state ───────────────────────────────────────────
  function refreshSwapButton() {
    const bothReady = sourceFile !== null && targetFile !== null;
    swapBtn.disabled = !bothReady;
    fileStatus.textContent = bothReady
      ? 'Both images ready — hit Swap!'
      : sourceFile
        ? 'Now drop the target image →'
        : 'Upload a source face to begin';
  }

  // ── Handle file ────────────────────────────────────────────
  function handleFile(file, side) {
    if (!file) return;

    const { typeOk, sizeOk } = isValidFile(file);

    if (!typeOk) {
      showToast('error', 'Unsupported format',
        `"${file.name}" is not a valid image. Use JPG, PNG, or WebP.`);
      return;
    }
    if (!sizeOk) {
      showToast('error', 'File too large',
        `Max 10 MB per image. "${file.name}" is ${(file.size / 1024 / 1024).toFixed(1)} MB.`);
      return;
    }

    if (side === 'source') {
      sourceFile = file;
      setPreview(file, sourcePreview, sourcePlaceholder, sourceOverlay, sourceBadge, 'source');
    } else {
      targetFile = file;
      setPreview(file, targetPreview, targetPlaceholder, targetOverlay, targetBadge, 'target');
    }

    refreshSwapButton();
  }

  // ── Wire upload zones ──────────────────────────────────────
  function wireZone(zone, input, side) {
    // File input change
    input.addEventListener('change', () => {
      if (input.files && input.files[0]) handleFile(input.files[0], side);
      input.value = ''; // allow re-selecting the same file
    });

    // Drag events
    zone.addEventListener('dragenter', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragover',  (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', (e) => {
      if (!zone.contains(e.relatedTarget)) zone.classList.remove('dragover');
    });
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file, side);
    });

    // Keyboard: Enter / Space triggers the file picker
    zone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        input.click();
      }
    });
  }

  wireZone(sourceZone, sourceInput, 'source');
  wireZone(targetZone, targetInput, 'target');

  // ── Swap ───────────────────────────────────────────────────
  async function doSwap() {
    if (!sourceFile || !targetFile) return;

    // Loading state
    swapBtn.disabled      = true;
    spinner.style.display = 'block';
    swapBtnLabel.textContent = 'Swapping faces…';
    resultArea.style.display = 'none';

    const enhance = enhanceToggle.checked;
    const form    = new FormData();
    form.append('source_image', sourceFile, sourceFile.name);
    form.append('target_image', targetFile, targetFile.name);

    const t0 = Date.now();

    try {
      const res = await fetch(`/swap?enhance=${enhance}`, {
        method: 'POST',
        body: form,
      });

      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

      if (!res.ok) {
        // Try to parse JSON error detail from FastAPI
        let detail = `HTTP ${res.status}`;
        try {
          const data = await res.json();
          detail = data.detail || detail;
        } catch (_) { /* ignore */ }
        showToast('error', 'Swap failed', detail);
        return;
      }

      // Build blob URL for the result image
      const blob   = await res.blob();
      const imgUrl = URL.createObjectURL(blob);

      resultImg.src         = imgUrl;
      downloadBtn.href      = imgUrl;
      processingTime.textContent = `Processed in ${elapsed}s`;

      resultArea.style.display = 'block';
      resultArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      showToast('success', 'Done!', `Face swapped in ${elapsed}s.`, 4000);

    } catch (err) {
      showToast('error', 'Network error', err.message || 'Could not reach the server.');
    } finally {
      // Restore button
      swapBtn.disabled      = false;
      spinner.style.display = 'none';
      swapBtnLabel.textContent = '⚡ Swap Face';
    }
  }

  swapBtn.addEventListener('click', doSwap);

  // ── Swap Again ─────────────────────────────────────────────
  function resetAll() {
    sourceFile = null;
    targetFile = null;

    clearZone(sourcePreview, sourcePlaceholder, sourceOverlay, sourceBadge);
    clearZone(targetPreview, targetPlaceholder, targetOverlay, targetBadge);

    sourceInput.value = '';
    targetInput.value = '';

    resultArea.style.display = 'none';
    resultImg.src            = '';
    downloadBtn.href         = '#';

    refreshSwapButton();
    window.scrollTo({ top: document.getElementById('swap-tool').offsetTop - 80, behavior: 'smooth' });
  }

  swapAgainBtn.addEventListener('click', resetAll);

  // ── FAQ accordion ──────────────────────────────────────────
  document.querySelectorAll('.faq-question').forEach((question) => {
    question.addEventListener('click', () => toggleFaq(question));
    question.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleFaq(question);
      }
    });
  });

  function toggleFaq(question) {
    const item     = question.closest('.faq-item');
    const isOpen   = item.classList.contains('open');

    // Close all others
    document.querySelectorAll('.faq-item.open').forEach((el) => {
      el.classList.remove('open');
      el.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
    });

    if (!isOpen) {
      item.classList.add('open');
      question.setAttribute('aria-expanded', 'true');
    }
  }

  // ── Initial state ──────────────────────────────────────────
  refreshSwapButton();

  // ── Smooth scroll for hero CTA ─────────────────────────────
  document.getElementById('hero-cta').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('swap-tool').scrollIntoView({ behavior: 'smooth' });
  });

  // ── Health check on page load (optional UX) ─────────────────
  (async () => {
    try {
      const res  = await fetch('/health');
      const data = await res.json();
      if (!data.model_loaded) {
        showToast('error', 'Model not loaded',
          'The AI model failed to load. Check server logs.', 10000);
      }
    } catch (_) {
      // Server not reachable — silent fail during static preview
    }
  })();

})();

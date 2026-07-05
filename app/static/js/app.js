(function () {
  const root = document.documentElement;
  const themeToggle = document.getElementById('themeToggle');

  function applyTheme(theme) {
    root.setAttribute('data-bs-theme', theme);
    if (themeToggle) {
      const icon = themeToggle.querySelector('i');
      if (icon) icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    }
  }

  // In-memory theme state (no localStorage per platform constraints);
  // defaults to light on each fresh page load, but toggling is instant.
  let currentTheme = 'light';
  applyTheme(currentTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      currentTheme = currentTheme === 'light' ? 'dark' : 'light';
      applyTheme(currentTheme);
    });
  }

  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('appSidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });
  }

  // ---------------------------------------------------------------------
  // Toast notifications: auto-dismiss each flash-derived toast after 5s,
  // and allow manual close via the "x" button.
  // ---------------------------------------------------------------------
  function dismissToast(toastEl) {
    if (!toastEl) return;
    toastEl.classList.add('toast-out');
    setTimeout(function () {
      if (toastEl.parentNode) toastEl.parentNode.removeChild(toastEl);
    }, 250);
  }

  document.querySelectorAll('.app-toast').forEach(function (toastEl) {
    const closeBtn = toastEl.querySelector('.app-toast-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () { dismissToast(toastEl); });
    }
    setTimeout(function () { dismissToast(toastEl); }, 5000);
  });

  // ---------------------------------------------------------------------
  // Confirmation dialogs: any form or button with data-confirm="message"
  // shows a SweetAlert2 confirmation before proceeding, instead of the
  // plain browser confirm(). Falls back to window.confirm if SweetAlert2
  // isn't loaded for any reason, so nothing ever silently breaks.
  // ---------------------------------------------------------------------
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (form.dataset.confirmed === 'true') return;
      e.preventDefault();
      const message = form.getAttribute('data-confirm') || 'Are you sure?';
      const title = form.getAttribute('data-confirm-title') || 'Please confirm';

      if (window.Swal) {
        Swal.fire({
          title: title,
          text: message,
          icon: 'warning',
          showCancelButton: true,
          confirmButtonText: 'Yes, continue',
          cancelButtonText: 'Cancel',
          confirmButtonColor: '#4f46e5',
          cancelButtonColor: '#6b7280',
        }).then(function (result) {
          if (result.isConfirmed) {
            form.dataset.confirmed = 'true';
            form.submit();
          }
        });
      } else if (window.confirm(message)) {
        form.dataset.confirmed = 'true';
        form.submit();
      }
    });
  });

  // Global helper so other pages/scripts can trigger a styled toast
  // programmatically if needed (e.g. after an AJAX action).
  window.showAppToast = function (message, category) {
    const stack = document.getElementById('toastStack') || (function () {
      const el = document.createElement('div');
      el.className = 'toast-stack';
      el.id = 'toastStack';
      document.body.appendChild(el);
      return el;
    })();

    const icons = {
      success: 'bi-check-circle-fill', danger: 'bi-x-circle-fill',
      warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill'
    };
    const cat = category || 'info';
    const toastEl = document.createElement('div');
    toastEl.className = 'app-toast app-toast-' + cat;
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML =
      '<i class="bi ' + (icons[cat] || icons.info) + ' app-toast-icon"></i>' +
      '<span class="app-toast-message"></span>' +
      '<button type="button" class="app-toast-close" aria-label="Close">&times;</button>';
    toastEl.querySelector('.app-toast-message').textContent = message;
    toastEl.querySelector('.app-toast-close').addEventListener('click', function () {
      dismissToast(toastEl);
    });
    stack.appendChild(toastEl);
    setTimeout(function () { dismissToast(toastEl); }, 5000);
  };
})();

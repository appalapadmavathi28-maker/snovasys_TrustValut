document.addEventListener('DOMContentLoaded', function () {
  // Auto dismiss flash alerts after 6 seconds
  setTimeout(function () {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    });
  }, 6000);

  // Setup generic confirmation modal actions
  const confirmModal = document.getElementById('confirmationModal');
  if (confirmModal) {
    confirmModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      const actionUrl = button.getAttribute('data-action-url');
      const actionTitle = button.getAttribute('data-action-title') || 'Confirm Action';
      const actionMessage = button.getAttribute('data-action-message') || 'Are you sure you want to proceed?';
      const buttonClass = button.getAttribute('data-btn-class') || 'btn-danger';
      const buttonText = button.getAttribute('data-btn-text') || 'Confirm';

      const modalTitle = confirmModal.querySelector('.modal-title');
      const modalBody = confirmModal.querySelector('.modal-body-message');
      const modalForm = confirmModal.querySelector('#confirmationForm');
      const modalSubmitBtn = confirmModal.querySelector('#confirmationSubmitBtn');

      if (modalTitle) modalTitle.textContent = actionTitle;
      if (modalBody) modalBody.textContent = actionMessage;
      if (modalForm) modalForm.setAttribute('action', actionUrl);
      if (modalSubmitBtn) {
        modalSubmitBtn.className = `btn ${buttonClass}`;
        modalSubmitBtn.textContent = buttonText;
      }
    });
  }

  // Password Strength Meter for registration
  const passwordInput = document.getElementById('password');
  const strengthMeter = document.getElementById('passwordStrengthBar');
  const strengthText = document.getElementById('passwordStrengthText');

  if (passwordInput && strengthMeter && strengthText) {
    passwordInput.addEventListener('input', function () {
      const val = passwordInput.value;
      let score = 0;
      if (val.length >= 8) score++;
      if (/[A-Z]/.test(val)) score++;
      if (/[a-z]/.test(val)) score++;
      if (/[0-9]/.test(val)) score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;

      let width = 0;
      let label = 'Very Weak';
      let colorClass = 'bg-danger';

      switch (score) {
        case 1:
        case 2:
          width = 30;
          label = 'Weak (Needs 8+ chars, upper, lower, numbers & symbols)';
          colorClass = 'bg-danger';
          break;
        case 3:
        case 4:
          width = 70;
          label = 'Moderate (Good, add special characters or length)';
          colorClass = 'bg-warning';
          break;
        case 5:
          width = 100;
          label = 'Strong Password';
          colorClass = 'bg-success';
          break;
        default:
          width = 5;
          label = 'Too Short';
          colorClass = 'bg-secondary';
      }

      strengthMeter.style.width = width + '%';
      strengthMeter.className = 'progress-bar ' + colorClass;
      strengthText.textContent = label;
    });
  }
});

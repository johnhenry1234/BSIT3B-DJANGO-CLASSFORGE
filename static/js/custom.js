// ClassForge custom scripts.
// Kept intentionally small: page-specific behaviour lives in the templates.
document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss Django messages after 6 seconds.
  document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
    setTimeout(function () {
      if (window.bootstrap && window.bootstrap.Alert) {
        window.bootstrap.Alert.getOrCreateInstance(alert).close();
      }
    }, 6000);
  });
});

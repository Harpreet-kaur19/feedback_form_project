// Client-side form validation for fill_form.html.
// If you already have your own form_validation.js, keep yours instead of
// this one -- this is just a safe default so the page doesn't 404 on the
// <script> tag if you don't have one yet.
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('feedback-form');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    const required = form.querySelectorAll('[required]');
    for (const field of required) {
      if (field.type === 'radio') {
        const group = form.querySelectorAll(`[name="${field.name}"]`);
        const checked = Array.from(group).some((r) => r.checked);
        if (!checked) {
          e.preventDefault();
          field.closest('.field')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
          return;
        }
      } else if (!field.value.trim()) {
        e.preventDefault();
        field.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
    }
  });
});

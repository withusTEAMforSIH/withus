// ============================================
// WithUS — plans.js
// Toggles between Basic and Premium tier panels
// ============================================

document.addEventListener('DOMContentLoaded', () => {

    const toggle = document.getElementById('tierToggle');
    if (!toggle) return;

    const buttons = toggle.querySelectorAll('.tier-btn');
    const panels = document.querySelectorAll('.tier-panel');

    buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tier;

            buttons.forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');

            panels.forEach((panel) => {
                panel.classList.toggle('active', panel.dataset.panel === target);
            });
        });
    });

});
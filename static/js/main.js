// ============================================
// WithUS — main.js
// ============================================

document.addEventListener('DOMContentLoaded', () => {

    // Mobile nav toggle
    const navToggle = document.getElementById('navToggle');
    const navMobile = document.getElementById('navMobile');

    if (navToggle && navMobile) {
        navToggle.addEventListener('click', () => {
            const isOpen = navMobile.classList.toggle('open');
            navToggle.setAttribute('aria-expanded', isOpen);
            navToggle.classList.toggle('active', isOpen);
        });
    }

    // Hero chat mock: reveal reply after "typing" delay
    const typingBubble = document.getElementById('typingBubble');
    const replyBubble = document.getElementById('replyBubble');

    if (typingBubble && replyBubble) {
        setTimeout(() => {
            typingBubble.style.display = 'none';
            replyBubble.classList.add('show');
        }, 1600);
    }

    // Prevent picking a past date/time on the booking form
    const scheduledInput = document.getElementById('scheduled_time');
    if (scheduledInput) {
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        scheduledInput.min = now.toISOString().slice(0, 16);
    }

    // Auto-dismiss flash messages after a few seconds
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach((flash) => {
        setTimeout(() => {
            flash.style.transition = 'opacity 0.4s ease';
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 400);
        }, 4000);
    });

});
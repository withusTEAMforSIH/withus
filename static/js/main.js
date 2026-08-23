// ============================================
// WithUS — main.js
// ============================================

document.addEventListener('DOMContentLoaded', () => {

    // ============================================
    // Mobile navigation
    // ============================================

    const navToggle = document.getElementById('navToggle');
    const navMobile = document.getElementById('navMobile');

    if (navToggle && navMobile) {

        navToggle.addEventListener('click', () => {

            const isOpen = navMobile.classList.toggle('open');

            navToggle.setAttribute('aria-expanded', isOpen);
            navToggle.classList.toggle('active', isOpen);

        });

    }


    // ============================================
    // Desktop "For professionals" dropdown
    // ============================================

    const professionalTrigger =
        document.getElementById('professionalTrigger');

    const professionalDropdown =
        document.getElementById('professionalDropdown');

    const professionalMenu =
        document.querySelector('.professional-menu');


    if (
        professionalTrigger &&
        professionalDropdown &&
        professionalMenu
    ) {

        professionalTrigger.addEventListener('click', (event) => {

            event.stopPropagation();

            const isOpen =
                professionalMenu.classList.toggle('open');

            professionalTrigger.setAttribute(
                'aria-expanded',
                isOpen
            );

        });


        // Close when clicking outside
        document.addEventListener('click', (event) => {

            if (!professionalMenu.contains(event.target)) {

                professionalMenu.classList.remove('open');

                professionalTrigger.setAttribute(
                    'aria-expanded',
                    'false'
                );

            }

        });

    }


    // ============================================
    // Mobile "For professionals" dropdown
    // ============================================

    const mobileProfessionalTrigger =
        document.getElementById(
            'mobileProfessionalTrigger'
        );

    const mobileProfessionals =
        document.querySelector(
            '.mobile-professionals'
        );


    if (
        mobileProfessionalTrigger &&
        mobileProfessionals
    ) {

        mobileProfessionalTrigger.addEventListener(
            'click',
            () => {

                const isOpen =
                    mobileProfessionals.classList.toggle(
                        'open'
                    );

                mobileProfessionalTrigger.setAttribute(
                    'aria-expanded',
                    isOpen
                );

            }
        );

    }


    // ============================================
    // Hero chat mock
    // ============================================

    const typingBubble =
        document.getElementById('typingBubble');

    const replyBubble =
        document.getElementById('replyBubble');


    if (typingBubble && replyBubble) {

        setTimeout(() => {

            typingBubble.style.display = 'none';

            replyBubble.classList.add('show');

        }, 1600);

    }


    // ============================================
    // Prevent past date/time
    // ============================================

    const scheduledInput =
        document.getElementById('scheduled_time');


    if (scheduledInput) {

        const now = new Date();

        now.setMinutes(
            now.getMinutes() -
            now.getTimezoneOffset()
        );

        scheduledInput.min =
            now.toISOString().slice(0, 16);

    }


    // ============================================
    // Auto-dismiss flash messages
    // ============================================

    const flashes =
        document.querySelectorAll('.flash');


    flashes.forEach((flash) => {

        setTimeout(() => {

            flash.style.transition =
                'opacity 0.4s ease';

            flash.style.opacity = '0';


            setTimeout(() => {

                flash.remove();

            }, 400);

        }, 4000);

    });

});




(function () {
    const form = document.getElementById('chatMockForm');
    if (!form) return; // not on this page

    const input = document.getElementById('chatMockInput');
    const messagesEl = document.getElementById('chatMockMessages');

    let history = [];

    function addBubble(text, sender) {
        const bubble = document.createElement('div');
        bubble.classList.add('chat-bubble');
        bubble.classList.add(sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-doc');
        bubble.textContent = text;
        messagesEl.appendChild(bubble);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return bubble;
    }

    function addTypingBubble() {
        const bubble = document.createElement('div');
        bubble.classList.add('chat-bubble', 'chat-bubble-doc', 'typing');
        bubble.innerHTML = `
            <span class="dot-flash"></span>
            <span class="dot-flash"></span>
            <span class="dot-flash"></span>
        `;
        messagesEl.appendChild(bubble);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return bubble;
    }

    form.addEventListener('submit', async function (event) {
        event.preventDefault();

        const message = input.value.trim();
        if (!message) return;

        addBubble(message, 'user');
        history.push({ role: 'user', content: message });

        input.value = '';
        input.disabled = true;

        const typingBubble = addTypingBubble();

        try {
            const response = await fetch('/api/chatbot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, history: history })
            });

            const data = await response.json();

            typingBubble.remove();

            if (!response.ok) {
                addBubble(data.reply || 'Something went wrong. Please try again.', 'doc');
                return;
            }

            addBubble(data.reply, 'doc');
            history.push({ role: 'assistant', content: data.reply });

        } catch (err) {
            typingBubble.remove();
            addBubble("Sorry, I couldn't connect. Please try again.", 'doc');
            console.error(err);
        } finally {
            input.disabled = false;
            input.focus();
        }
    });
})();
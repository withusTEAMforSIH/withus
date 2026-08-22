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
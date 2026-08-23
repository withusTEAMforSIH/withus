/* ============================================================
   WITHUS — CLEAN INTRO
   ============================================================

   ONLY ANIMATION:
   WITHUS letters scatter away as the user scrolls.

   REMOVED:
   - Three.js
   - GLB / GLTF loading
   - 3D models
   - Model rotation
   - Model movement
   - Model scaling
   - Model timelines
   - Scene text animation
   - Progress animation
   - Three.js renderer
   - Camera
   - Lighting
   - Model placeholders

   ============================================================ */


/* ============================================================
   CONFIGURATION
   ============================================================ */

/*
 * How much of the intro scroll area is used
 * for the WITHUS letter animation.
 *
 * 0.15 = first 15% of the intro.
 */
const LOGO_END = 1;


/* ============================================================
   LETTER DIRECTIONS
   ============================================================

   Each letter gets its own direction.

   W → top-left
   I → upper-left
   T → bottom
   H → top
   U → bottom-right
   S → right

   Change these values if you want different movement.
   ============================================================ */

const LETTER_DIRECTIONS = [
    {
        x: -1.4,
        y: -1.0,
        r: -0.4
    },

    {
        x: -0.8,
        y: 1.3,
        r: 0.35
    },

    {
        x: 0.15,
        y: -1.5,
        r: -0.5
    },

    {
        x: -0.25,
        y: 1.4,
        r: 0.45
    },

    {
        x: 1.0,
        y: -1.2,
        r: 0.45
    },

    {
        x: 1.5,
        y: 0.8,
        r: -0.4
    }
];


/* ============================================================
   HELPERS
   ============================================================ */

function clamp(value, min, max) {
    return Math.min(
        Math.max(value, min),
        max
    );
}


function easeInOutCubic(t) {

    t = clamp(t, 0, 1);

    return t < 0.5
        ? 4 * t * t * t
        : 1 - Math.pow(-2 * t + 2, 3) / 2;
}


/* ============================================================
   BOOT
   ============================================================ */

function bootIntro() {

    const wrapper =
        document.getElementById("introScroller");

    if (!wrapper) {
        console.warn(
            "WITHUS intro: #introScroller not found."
        );

        return;
    }


    /* ========================================================
       GET WITHUS LETTERS
       ======================================================== */

    const introWord =
        document.getElementById("introWord");

    if (!introWord) {
        console.warn(
            "WITHUS intro: #introWord not found."
        );

        return;
    }


    const logoLetters = [
        ...introWord.querySelectorAll(".intro-letter")
    ];


    if (!logoLetters.length) {

        console.warn(
            "WITHUS intro: no .intro-letter elements found."
        );

        return;
    }


    /* ========================================================
       CLEAN UP EVERYTHING ELSE
       ======================================================== */

    /*
     * The old version used a Three.js canvas for the models.
     * We don't need it anymore.
     */

    const canvas =
        document.getElementById("introCanvas");

    if (canvas) {
        canvas.style.display = "none";
    }


    /*
     * Hide old scene text because the only animation
     * remaining is the WITHUS logo animation.
     */

    const textElements = [
        ...document.querySelectorAll(".intro-scene-text")
    ];

    textElements.forEach(element => {

        element.style.opacity = "0";
        element.style.pointerEvents = "none";
        element.style.visibility = "hidden";

    });


    /*
     * Disable the old progress animation.
     */

    const progressFill =
        document.querySelector(".intro-progress-fill");

    if (progressFill) {

        progressFill.style.height = "0";
        progressFill.style.opacity = "0";
        progressFill.style.visibility = "hidden";

    }


    /* ========================================================
       PREPARE LETTERS
       ======================================================== */

    logoLetters.forEach(letter => {

        letter.style.willChange =
            "transform, opacity";

        letter.style.opacity = "1";

        letter.style.transform =
            "translate3d(0, 0, 0) rotate(0rad)";

    });


    /* ========================================================
       LOGO ANIMATION
       ======================================================== */

    function updateLogo(progress) {

        /*
         * Convert overall scroll progress into
         * logo-only progress.
         *
         * 0 → logo intact
         * 1 → logo completely scattered
         */

        const logoProgress =
            clamp(
                progress / LOGO_END,
                0,
                1
            );


        logoLetters.forEach(
            (letter, index) => {

                const direction =
                    LETTER_DIRECTIONS[index];


                if (!direction) {
                    return;
                }


                /*
                 * Small delay before the letters
                 * begin moving.
                 */

                const movement =
                    easeInOutCubic(
                        clamp(
                            (logoProgress - 0.08) / 0.92,
                            0,
                            1
                        )
                    );


                /*
                 * Horizontal movement.
                 */

                const x =
                    direction.x *
                    window.innerWidth *
                    movement;


                /*
                 * Vertical movement.
                 */

                const y =
                    direction.y *
                    window.innerHeight *
                    movement;


                /*
                 * Rotation.
                 */

                const rotation =
                    direction.r *
                    2.5 *
                    movement;


                /*
                 * Apply transform.
                 */

                letter.style.transform =
                    `translate3d(
                        ${x}px,
                        ${y}px,
                        0
                    ) rotate(${rotation}rad)`;


                /*
                 * Fade the letters away
                 * after they start scattering.
                 */

                letter.style.opacity =
                    1 -
                    clamp(
                        (logoProgress - 0.30) / 0.70,
                        0,
                        1
                    );

            }
        );
    }


    /* ========================================================
       SCROLL PROGRESS
       ======================================================== */

    let targetProgress = 0;

    let currentProgress = 0;


   function readScroll() {

    const rect =
        wrapper.getBoundingClientRect();

    const total =
        wrapper.offsetHeight -
        window.innerHeight;

    const scrolled =
        -rect.top;

    targetProgress =
        total > 0
            ? clamp(
                scrolled / total,
                0,
                1
            )
            : 0;

    wrapper.classList.toggle(
        "scrolled",
        targetProgress > 0.02
    );
}

    /* ========================================================
       RESIZE
       ======================================================== */

    /*
     * Recalculate the letter positions automatically
     * when the browser is resized.
     */

    window.addEventListener(
        "resize",
        () => {
            updateLogo(currentProgress);
        }
    );


    /* ========================================================
       SCROLL LISTENER
       ======================================================== */

    window.addEventListener(
        "scroll",
        readScroll,
        {
            passive: true
        }
    );


    /* ========================================================
       INITIAL STATE
       ======================================================== */

    readScroll();

    updateLogo(0);


    /* ========================================================
       ANIMATION LOOP
       ======================================================== */

    function animate() {

        requestAnimationFrame(
            animate
        );


        /*
         * Smoothly approach the scroll position.
         */

        currentProgress +=
            (
                targetProgress -
                currentProgress
            ) * 0.075;


        /*
         * The ONLY animation being updated.
         */

        updateLogo(
            currentProgress
        );

    }


    /* ========================================================
       READY
       ======================================================== */

    wrapper.classList.add(
        "intro-ready"
    );


    animate();

}


/* ============================================================
   START
   ============================================================ */

bootIntro();
/*
 * Hero: mientras se recorre la pista (180vh), el texto sube y se desvanece
 * y el robot asciende desde debajo de los botones con un leve zoom.
 */
(function () {
    const pista = document.querySelector('[data-hero]');
    if (!pista) return;
    const escenario = pista.querySelector('[data-hero-escenario]');
    const robot = pista.querySelector('[data-hero-robot]');
    const texto = pista.querySelector('[data-hero-texto]');
    const botones = pista.querySelector('[data-hero-botones]');
    const brillo = pista.querySelector('[data-hero-brillo]');
    const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');

    const ZOOM = 0.05;
    const limitar = (x) => Math.min(1, Math.max(0, x));
    const suave = (x) => x * x * (3 - 2 * x);

    let geom = null;   // recorrido vertical del robot: { inicio, fin }
    let textoY = 0;
    let actual = null; // progreso suavizado 0..1
    let pendiente = false;

    function objetivo() {
        const r = pista.getBoundingClientRect();
        const recorrido = r.height - escenario.clientHeight;
        return recorrido > 0 ? limitar(-r.top / recorrido) : 0;
    }

    // Tamaño y recorrido del robot según la pantalla (como en el boceto)
    function medir() {
        const vw = escenario.clientWidth;
        const vh = escenario.clientHeight;
        const movil = vw < 768;
        const ratio = robot.naturalWidth ? robot.naturalHeight / robot.naturalWidth : 941 / 1672;
        const W = movil ? 1.7 * vw : Math.max(1.1 * vw, (vh * 1.02) / ratio);
        const H = W * ratio;
        robot.style.width = `${W}px`;
        robot.style.left = `${vw / 2 - (movil ? 0.5 : 0.53) * W}px`;

        const finBotones = botones.getBoundingClientRect().bottom - escenario.getBoundingClientRect().top - textoY;
        const margen = movil ? 44 : Math.max(56, vh * 0.075);
        const inicio = Math.min(finBotones + margen - 0.26 * H, vh - 0.5 * H);
        let fin = movil ? vh * 0.5 - 0.74 * H : vh - H;
        if (fin > inicio - vh * 0.25) fin = inicio - vh * 0.25;
        geom = { inicio, fin };
        aplicar(actual ?? objetivo());
    }

    function aplicar(p) {
        const tp = suave(limitar(p / 0.32));
        textoY = -90 * tp;
        texto.style.transform = `translate3d(0, ${textoY}px, 0)`;
        texto.style.opacity = 1 - tp;
        texto.style.pointerEvents = tp > 0.9 ? 'none' : '';

        const ip = suave(limitar(p / 0.92));
        const y = geom.inicio + (geom.fin - geom.inicio) * ip;
        robot.style.transform = `translate3d(0, ${y}px, 0) scale(${1 + ZOOM * ip})`;
        brillo.style.opacity = 0.6 + 0.4 * ip;
    }

    function pintar() {
        pendiente = false;
        const meta = objetivo();
        // El scroll ya llega suavizado (scroll-suave.js); aquí solo se afina, como en el boceto
        actual = actual === null || sinMovimiento.matches ? meta : actual + (meta - actual) * 0.22;
        if (Math.abs(meta - actual) < 0.0005) actual = meta;
        aplicar(actual);
        if (actual !== meta) pedirPintado();
    }

    function pedirPintado() {
        if (!pendiente) {
            pendiente = true;
            requestAnimationFrame(pintar);
        }
    }

    window.addEventListener('scroll', pedirPintado, { passive: true });
    window.addEventListener('resize', medir);
    if (!robot.complete) robot.addEventListener('load', medir);
    if (document.fonts) document.fonts.ready.then(medir);
    medir();
})();

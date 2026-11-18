/*
 * Scroll suave (todas las páginas), como en el boceto:
 * - Rueda del ratón: avanza un poco menos y la página se desliza con inercia.
 * - Enlaces a anclas de la misma página (#servicios) y a la página actual sin
 *   ancla (logo, "Volver arriba"): viaje con duración fija que acelera y frena
 *   suave, para que se vea la página pasar.
 */
(function () {
    // Rueda: menos VELOCIDAD = avanza menos por giro; menos SUAVIDAD = desliza más lento
    const VELOCIDAD = 0.75;
    const SUAVIDAD = 0.05;
    // Enlaces: la duración crece con la distancia, entre un mínimo y un máximo (ms)
    const VIAJE_MIN = 1000;
    const VIAJE_MAX = 2400;
    const VIAJE_MS_POR_PX = 0.5;

    const raiz = document.documentElement;
    const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');

    let actual = window.scrollY;
    let destino = actual;
    let viaje = null;      // { desde, hasta, inicio, duracion } mientras dura un viaje por enlace
    let animando = false;

    const maximo = () => raiz.scrollHeight - window.innerHeight;
    const limitar = (y) => Math.max(0, Math.min(maximo(), y));
    // Curva pareja: arranca y frena suave sin acelerar demasiado en el centro
    const suaveInOut = (t) => -(Math.cos(Math.PI * t) - 1) / 2;

    function paso() {
        if (viaje) {
            // Mismo reloj que al iniciar el viaje (el de requestAnimationFrame puede ir por detrás)
            const t = Math.min(1, Math.max(0, (performance.now() - viaje.inicio) / viaje.duracion));
            actual = viaje.desde + (viaje.hasta - viaje.desde) * suaveInOut(t);
            if (t === 1) viaje = null;
        } else {
            actual += (destino - actual) * SUAVIDAD;
            if (Math.abs(destino - actual) < 0.5) actual = destino;
        }
        window.scrollTo({ top: actual, behavior: 'instant' });
        animando = viaje !== null || actual !== destino;
        if (animando) requestAnimationFrame(paso);
    }

    function arrancar() {
        if (!animando) {
            animando = true;
            requestAnimationFrame(paso);
        }
    }

    // Rueda: suma al destino y desliza con inercia (cancela un viaje en curso)
    function deslizar(y) {
        if (!animando) actual = window.scrollY;
        viaje = null;
        destino = limitar(y);
        arrancar();
    }

    // Enlace: viaje con duración proporcional a la distancia
    function viajarA(y) {
        const hasta = limitar(y);
        if (sinMovimiento.matches) {
            window.scrollTo({ top: hasta, behavior: 'instant' });
            return;
        }
        const desde = window.scrollY;
        const duracion = Math.min(VIAJE_MAX, Math.max(VIAJE_MIN, Math.abs(hasta - desde) * VIAJE_MS_POR_PX));
        viaje = { desde, hasta, inicio: performance.now(), duracion };
        destino = hasta;
        arrancar();
    }

    // ¿El elemento bajo el ratón puede desplazarse por sí mismo (p. ej. un chat)?
    function tieneScrollPropio(el, dy) {
        for (; el && el !== document.body; el = el.parentElement) {
            const estilo = getComputedStyle(el);
            if (!/(auto|scroll)/.test(estilo.overflowY)) continue;
            if (dy > 0 ? el.scrollTop + el.clientHeight < el.scrollHeight : el.scrollTop > 0) return true;
        }
        return false;
    }

    window.addEventListener('wheel', (ev) => {
        if (sinMovimiento.matches || ev.ctrlKey || raiz.classList.contains('menu-abierto')) return;
        if (Math.abs(ev.deltaX) > Math.abs(ev.deltaY)) return;
        if (tieneScrollPropio(ev.target, ev.deltaY)) return;
        ev.preventDefault();
        let d = ev.deltaY;
        if (ev.deltaMode === 1) d *= 16;                       // por líneas
        else if (ev.deltaMode === 2) d *= window.innerHeight;  // por páginas
        deslizar((animando ? (viaje ? window.scrollY : destino) : window.scrollY) + d * VELOCIDAD);
    }, { passive: false });

    // Si el usuario arrastra la barra o usa el teclado, seguir desde ahí
    window.addEventListener('scroll', () => {
        if (!animando) actual = destino = window.scrollY;
    }, { passive: true });

    document.addEventListener('click', (ev) => {
        const a = ev.target.closest('a[href]');
        if (!a || ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
        const url = new URL(a.href, location.href);
        if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search) return;

        let y;
        if (!url.hash) {
            y = 0;
        } else {
            const objetivo = document.getElementById(decodeURIComponent(url.hash.slice(1)));
            if (!objetivo) return;
            y = objetivo.getBoundingClientRect().top + window.scrollY;
        }
        ev.preventDefault();
        history.pushState(null, '', url.hash || url.pathname);
        viajarA(y);
    });
})();

/*
 * Header, botón circular y menú a pantalla completa (todas las páginas).
 * - Al bajar, el logo y el botón MENÚ se van al centro y se desvanecen,
 *   y aparece el botón circular con el logo.
 * - El menú se abre/cierra con los botones, con Escape o al elegir un enlace.
 */
(function () {
    const cabecera = document.querySelector('[data-cabecera]');
    const piezas = document.querySelectorAll('[data-cabecera-pieza]');
    const circulo = document.querySelector('[data-boton-circulo]');
    const menu = document.querySelector('[data-menu]');
    if (!cabecera || !circulo || !menu) return;

    const abridores = document.querySelectorAll('[data-abrir-menu]');
    const cerrar = menu.querySelector('[data-cerrar-menu]');
    const enlaces = menu.querySelectorAll('[data-menu-enlace]');
    const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');

    const limitar = (x) => Math.min(1, Math.max(0, x));
    const suave = (x) => x * x * (3 - 2 * x);

    /* ---------- Header según el scroll ---------- */

    let progreso = null; // valor suavizado 0..1
    let pendiente = false;

    function pintarCabecera() {
        pendiente = false;
        const objetivo = limitar(window.scrollY / (window.innerHeight * 0.4));
        progreso = progreso === null || sinMovimiento.matches
            ? objetivo
            : progreso + (objetivo - progreso) * 0.14;
        if (Math.abs(objetivo - progreso) < 0.001) progreso = objetivo;

        const e = progreso;
        const centro = window.innerWidth / 2;
        const mover = suave(limitar(e / 0.75));
        const opacidad = 1 - suave(limitar((e - 0.45) / 0.35));

        piezas.forEach((el) => {
            const dx = (centro - (el.offsetLeft + el.offsetWidth / 2)) * mover;
            el.style.transform = `translateX(${dx}px) scale(${1 - 0.55 * mover})`;
            el.style.opacity = opacidad;
            el.style.pointerEvents = e > 0.4 ? 'none' : '';
            el.toggleAttribute('inert', e > 0.4);
        });

        // Aparición del círculo con un pequeño rebote
        const c = limitar((e - 0.55) / 0.45);
        const rebote = c === 0 ? 0 : 1 + 2.2 * Math.pow(c - 1, 3) + 1.2 * Math.pow(c - 1, 2);
        const boton = piezas[piezas.length - 1];
        circulo.style.top = `${boton.offsetTop + boton.offsetHeight / 2 - circulo.offsetHeight / 2}px`;
        circulo.style.opacity = suave(c);
        circulo.style.transform = `translateX(-50%) scale(${0.3 + 0.7 * rebote}) rotate(${(1 - c) * -40}deg)`;
        const visible = c > 0.6;
        circulo.style.pointerEvents = visible ? 'auto' : 'none';
        circulo.tabIndex = visible ? 0 : -1;
        circulo.setAttribute('aria-hidden', String(!visible));

        if (progreso !== objetivo) pedirPintado();
    }

    function pedirPintado() {
        if (!pendiente) {
            pendiente = true;
            requestAnimationFrame(pintarCabecera);
        }
    }

    window.addEventListener('scroll', pedirPintado, { passive: true });
    window.addEventListener('resize', pedirPintado);
    pintarCabecera();

    /* ---------- Menú ---------- */

    let ultimoFoco = null;

    function seccionActual() {
        const y = window.scrollY + window.innerHeight * 0.4;
        let actual = null;
        enlaces.forEach((a) => {
            const url = new URL(a.href);
            if (url.pathname !== location.pathname) return;
            const destino = url.hash ? document.getElementById(url.hash.slice(1)) : null;
            const top = destino ? destino.getBoundingClientRect().top + window.scrollY : 0;
            if (url.hash && !destino) return;
            if (top <= y) actual = a;
        });
        return actual;
    }

    function abrirMenu() {
        ultimoFoco = document.activeElement;
        const actual = seccionActual();
        enlaces.forEach((a) => a.classList.toggle('es-actual', a === actual));
        menu.removeAttribute('inert');
        menu.classList.add('esta-abierto');
        document.documentElement.classList.add('menu-abierto');
        abridores.forEach((b) => b.setAttribute('aria-expanded', 'true'));
        cerrar.focus({ preventScroll: true });
    }

    function cerrarMenu() {
        menu.classList.remove('esta-abierto');
        menu.setAttribute('inert', '');
        document.documentElement.classList.remove('menu-abierto');
        abridores.forEach((b) => b.setAttribute('aria-expanded', 'false'));
        if (ultimoFoco) ultimoFoco.focus({ preventScroll: true });
    }

    abridores.forEach((b) => b.addEventListener('click', abrirMenu));
    cerrar.addEventListener('click', cerrarMenu);
    document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape' && menu.classList.contains('esta-abierto')) cerrarMenu();
    });
    // Cualquier enlace del menú (secciones o logo) lo cierra; scroll-suave.js
    // desliza la página hasta el destino mientras la cortina sube
    menu.querySelectorAll('a[href]').forEach((a) => a.addEventListener('click', () => {
        ultimoFoco = null;
        cerrarMenu();
    }));
})();

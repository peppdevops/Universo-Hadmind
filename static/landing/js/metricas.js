/*
 * Métricas: al entrar en pantalla, las cajas aparecen escalonadas y los
 * números cuentan desde cero. Al salir se reinician para repetirse.
 */
(function () {
    const seccion = document.querySelector('[data-metricas]');
    if (!seccion) return;
    const items = [...seccion.querySelectorAll('[data-metrica]')];
    const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)');

    // "70%" -> { pre: '', n: 70, dec: 0, suf: '%' }; "24/7" -> { n: 24, suf: '/7' }
    function separar(valor) {
        const m = String(valor).match(/^([^\d]*)([\d.,]+)(.*)$/);
        if (!m) return null;
        return {
            pre: m[1],
            n: parseFloat(m[2].replace(',', '.')),
            dec: (m[2].split(/[.,]/)[1] || '').length,
            suf: m[3],
        };
    }

    const numeros = items.map((item) => {
        const el = item.querySelector('[data-metrica-valor]');
        const final = el.dataset.metricaValor;
        el.setAttribute('aria-label', final); // los lectores de pantalla leen siempre el valor final
        return { el, final, partes: separar(final) };
    });

    function escribir(i, fraccion) {
        const { el, final, partes } = numeros[i];
        el.textContent = partes
            ? partes.pre + (partes.n * fraccion).toFixed(partes.dec) + partes.suf
            : final;
    }

    let inicio = null; // momento en que empezó la animación; null = oculta

    function ocultar() {
        inicio = null;
        items.forEach((item, i) => {
            item.classList.remove('es-visible');
            item.style.transitionDelay = '0s';
            escribir(i, 0);
        });
    }

    function contar(ahora) {
        if (inicio === null) return;
        let sigue = false;
        numeros.forEach((_, i) => {
            const t = Math.min(1, Math.max(0, (ahora - inicio - i * 120) / 1800));
            escribir(i, 1 - Math.pow(1 - t, 3));
            if (t < 1) sigue = true;
        });
        if (sigue) requestAnimationFrame(contar);
    }

    function revisar() {
        const r = seccion.getBoundingClientRect();
        const vh = window.innerHeight;
        if (inicio !== null && (r.top > vh * 0.85 || r.bottom < 0)) {
            ocultar();
        } else if (inicio === null && r.top < vh * 0.7 && r.bottom > 0) {
            items.forEach((item, i) => {
                item.style.transitionDelay = `${i * 0.12}s`;
                item.classList.add('es-visible');
            });
            inicio = performance.now();
            requestAnimationFrame(contar);
        }
    }

    // Con "reducir movimiento" se dejan los valores finales sin animar
    if (sinMovimiento.matches) return;

    seccion.classList.add('metricas--animada');
    ocultar();
    window.addEventListener('scroll', revisar, { passive: true });
    revisar();
})();

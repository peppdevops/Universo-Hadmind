/*
 * Servicios: carrusel infinito que avanza solo y se pausa con el ratón encima.
 * Al pasar el ratón (o tocar en móvil) una tarjeta muestra su "QUÉ ES".
 */
(function () {
    const ventana = document.querySelector('[data-carrusel]');
    if (!ventana) return;
    const pista = ventana.querySelector('[data-carrusel-pista]');
    const tarjetas = ventana.querySelectorAll('[data-servicio]');

    // En pantallas táctiles no hay hover: un toque abre/cierra el detalle
    tarjetas.forEach((t) => t.addEventListener('click', () => {
        const abrir = !t.classList.contains('es-activa');
        tarjetas.forEach((o) => o.classList.remove('es-activa'));
        t.classList.toggle('es-activa', abrir);
    }));

    // Con "reducir movimiento" no se mueve solo; se puede desplazar a mano (ver CSS)
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        ventana.classList.add('servicios__ventana--manual');
        return;
    }

    const VELOCIDAD = 40; // píxeles por segundo
    let x = 0;
    let ultimo = null;
    let pausado = false;
    let visible = false;

    ventana.addEventListener('mouseenter', () => { pausado = true; });
    ventana.addEventListener('mouseleave', () => { pausado = false; });
    ventana.addEventListener('focusin', () => { pausado = true; });
    ventana.addEventListener('focusout', () => { pausado = false; });

    function avanzar(ahora) {
        const dt = ultimo === null ? 16 : Math.min(64, ahora - ultimo);
        ultimo = ahora;
        if (!pausado) x -= (VELOCIDAD * dt) / 1000;
        const mitad = pista.scrollWidth / 2; // ancho de una copia de la lista
        if (mitad > 0 && -x >= mitad) x += mitad;
        pista.style.transform = `translate3d(${x}px, 0, 0)`;
        if (visible) requestAnimationFrame(avanzar);
    }

    // Solo se anima mientras el carrusel está en pantalla
    new IntersectionObserver(([entrada]) => {
        const antes = visible;
        visible = entrada.isIntersecting;
        if (visible && !antes) {
            ultimo = null;
            requestAnimationFrame(avanzar);
        }
    }).observe(ventana);
})();

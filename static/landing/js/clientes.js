/*
 * Clientes: las flechas desplazan la fila de logos una tarjeta a la vez.
 * En móvil también se puede deslizar con el dedo (scroll horizontal nativo).
 */
(function () {
    const bloque = document.querySelector('[data-clientes]');
    if (!bloque) return;
    const lista = bloque.querySelector('[data-clientes-lista]');
    const anterior = bloque.querySelector('[data-clientes-anterior]');
    const siguiente = bloque.querySelector('[data-clientes-siguiente]');

    function paso() {
        const tarjeta = lista.querySelector('li');
        const gap = parseFloat(getComputedStyle(lista).columnGap) || 0;
        return tarjeta ? tarjeta.offsetWidth + gap : lista.clientWidth;
    }

    // Las flechas se apagan en los extremos y se ocultan si todo cabe
    function actualizar() {
        const max = lista.scrollWidth - lista.clientWidth;
        anterior.disabled = lista.scrollLeft <= 1;
        siguiente.disabled = lista.scrollLeft >= max - 1;
        bloque.classList.toggle('clientes--sin-flechas', max <= 1);
    }

    anterior.addEventListener('click', () => lista.scrollBy({ left: -paso(), behavior: 'smooth' }));
    siguiente.addEventListener('click', () => lista.scrollBy({ left: paso(), behavior: 'smooth' }));
    lista.addEventListener('scroll', actualizar, { passive: true });
    window.addEventListener('resize', actualizar);
    actualizar();
})();

/*
 * Arreglo del menú lateral de unfold 0.110.1 (va con admin.css).
 *
 * unfold cierra el menú cada vez que "cambia el tamaño", pero lo que vigila es
 * el tamaño de la PÁGINA (ResizeObserver sobre <html>), no el de la ventana.
 * Con el menú al lado del contenido (admin.css, desde 1024 px), al abrirlo la
 * página cambia de alto y unfold lo cerraba en el mismo instante.
 *
 * Aquí se envuelve su función theme() para que esa reacción solo ocurra si el
 * ANCHO DE LA VENTANA cambió de verdad (por ejemplo, al achicarla). La primera
 * llamada (al cargar) pasa siempre: es la que deja el menú abierto o cerrado
 * según el ancho, como hace unfold.
 *
 * Se espera a "alpine:init": para entonces ya se cargó app.js de unfold (que
 * define theme) y Alpine todavía no ha creado la página (que la usa).
 */
document.addEventListener('alpine:init', () => {
    const themeOriginal = window.theme;
    if (typeof themeOriginal !== 'function') return;

    window.theme = function (...args) {
        const datos = themeOriginal(...args);
        // unfold guarda sidebarOpen como una FUNCIÓN que calcula si empieza
        // abierto. La plantilla propia del menú (templates/admin/nav_sidebar.html)
        // necesita un sí/no desde el principio para el ancho de la columna.
        if (typeof datos.sidebarOpen === 'function') {
            datos.sidebarOpen = datos.sidebarOpen();
        }
        const bindings = datos.themeBindings || {};
        const clave = Object.keys(bindings).find((k) => k.startsWith('x-resize'));
        if (!clave) return datos;

        const reaccionOriginal = bindings[clave];
        let anchoAnterior = null;
        bindings[clave] = function () {
            if (anchoAnterior === window.innerWidth) return; // solo cambió la página
            anchoAnterior = window.innerWidth;
            return reaccionOriginal.call(this);
        };
        return datos;
    };
});

// El menú se anima solo cuando la persona lo abre o lo cierra, no al cargar la
// página (si no, en cada página se vería deslizarse). La clase se pone después
// del primer dibujo.
window.addEventListener('load', () => {
    requestAnimationFrame(() => requestAnimationFrame(() => {
        document.documentElement.classList.add('hd-menu-animado');
    }));
});

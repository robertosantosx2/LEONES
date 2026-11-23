/* LEONES — navegación común */
(() => {
    "use strict";
    const navigation = [
        ["Inicio", "index.html", "top"],
        ["Inicio rápido", "inicio-rapido.html", "top"],
        ["Estado", "estado.html", "top"],
        ["Roadmap", "roadmap.html", "top"],
        ["Prospección", "prospeccion.html", "top"],
        ["Atlas", "atlas.html", "project"],
        ["Descubrimiento Atlas", "discovery-atlas.html", "project"],
        ["Casos de uso agentivos", "agent-use-cases.html", "project"],
        ["Diagramas", "diagramas.html", "project"],
        ["Runtimes locales", "runtimes-locales.html", "project"],
        ["Scripts", "scripts.html", "project"],
        ["Conocimiento de IA local", "conocimiento.html", "top"],
        ["Optimización de inferencia", "conocimiento-optimizacion.html", "top"],
        ["Hardware RTX Spark", "conocimiento-rtx-spark.html", "top"],
        ["Harnesses", "conocimiento-harnesses.html", "top"],
        ["Buddy", "buddy.html", "top"],
        ["Fuentes", "fuentes.html", "top"],
        ["RC3 · cerrada", "rc3.html", "application"],
        ["RC4 · recomendación", "rc4.html", "application"],
        ["¿Puede mi PC?", "puede-mi-pc.html", "application"],
        ["Cuadros maestros", "cuadros-maestros.html", "application"],
        ["Stack Explorer", "stack-explorer.html", "application"],
        ["Recomendaciones", "recommendations.html", "application"],
        ["Recomendaciones de visita", "recomendaciones-visita.html", "application"],
        ["Recomendar a LEONES", "recomendar.html", "application"],
        ["Resultados", "resultados.html", "application"],
        ["Manada", "manada.html", "top"],
        ["Horizonte", "horizon.html", "top"],
        ["Logos", "logos.html", "top"],
        ["Contacto", "contacto.html", "top"]
    ];
    const currentPath = window.location.pathname.split("/").pop() || "index.html";
    const createLink = ([label, path, level]) => {
        const link = document.createElement("a");
        link.className = `level-${level}`;
        link.href = path;
        link.textContent = label;
        if (path === currentPath) {
            link.classList.add("active");
            link.setAttribute("aria-current", "page");
        }
        return link;
    };
    function renderNavigation() {
        if (document.querySelector(".leones-nav-root")) return;
        document.body.classList.add("has-leones-navigation");
        const root = document.createElement("div");
        root.className = "leones-nav-root";
        const side = document.createElement("nav");
        side.className = "leones-side-nav";
        side.setAttribute("aria-label", "Secciones");
        const title = document.createElement("div");
        title.className = "side-title";
        title.textContent = "Explorar";
        side.appendChild(title);
        navigation.forEach((item) => side.appendChild(createLink(item)));
        root.appendChild(side);
        document.body.prepend(root);
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", renderNavigation);
    else renderNavigation();
})();

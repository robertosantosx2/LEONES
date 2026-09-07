/* LEONES — navegación común */
(() => {
    "use strict";
    const navigation = [
        ["Inicio", "index.html", "top"],
        ["Inicio rápido", "inicio-rapido.html", "top"],
        ["Proyectos", "proyectos.html", "top"],
        ["Estado", "estado.html", "top"],
        ["Roadmap", "roadmap.html", "top"],

        ["Atlas", "atlas.html", "project"],
        ["Pilares", "pilares.html", "project"],
        ["Arquitectura", "arquitectura.html", "project"],
        ["Diagramas", "diagramas.html", "project"],
        ["Pila", "pila.html", "project"],
        ["Runtimes locales", "runtimes-locales.html", "project"],
        ["Operación", "operacion.html", "project"],
        ["Scripts", "scripts.html", "project"],

        ["Conocimiento de IA en Local", "conocimiento.html", "top"],
        ["SGLang", "conocimiento-sglang.html", "top"],
        ["Optimización de inferencia", "conocimiento-optimizacion.html", "top"],
        ["Harnesses", "conocimiento-harnesses.html", "top"],
        ["Buddy", "buddy.html", "top"],
        ["Fuentes", "fuentes.html", "top"],

        ["Aplicación", "app.html", "top"],
        ["RC2 · histórico", "rc2.html", "application"],
        ["RC3 · cerrada", "rc3.html", "application"],
        ["RC4 · FitLLM", "rc4.html", "application"],
        ["¿Puede mi PC?", "puede-mi-pc.html", "application"],
        ["Cuadros maestros", "cuadros-maestros.html", "application"],
        ["Stack Explorer", "stack-explorer.html", "application"],
        ["Evaluación", "evaluacion.html", "application"],
        ["Recomendaciones", "recommendations.html", "application"],
        ["Recomendaciones de visita", "recomendaciones-visita.html", "application"],
        ["Recomendar a LEONES", "recomendar.html", "application"],
        ["Resultados", "resultados.html", "application"],

        ["Manada", "manada.html", "top"],
        ["Prospección", "prospeccion.html", "top"],
        ["Horizonte", "horizon.html", "top"],
        ["Logos", "logos.html", "top"],
        ["Contacto", "contacto.html", "top"]
    ];
    const base = "assets/graphics/leones-logo-principal.jpg";
    const currentPath = window.location.pathname.split("/").pop() || "index.html";
    const currentPage = navigation.find(([, path]) => path === currentPath);
    const createLink = ([label, path, level]) => {
        const link = document.createElement("a"); link.className = `level-${level}`; link.href = path; link.textContent = label;
        if (path === currentPath) { link.classList.add("active"); link.setAttribute("aria-current", "page"); }
        return link;
    };
    function renderNavigation() {
        if (document.querySelector(".leones-nav-root")) return;
        document.body.classList.add("has-leones-navigation");
        const root = document.createElement("div"); root.className = "leones-nav-root";
        const side = document.createElement("nav"); side.className = "leones-side-nav"; side.setAttribute("aria-label", "Secciones");
        const title = document.createElement("div"); title.className = "side-title"; title.textContent = "Explorar"; side.appendChild(title);
        navigation.forEach((item) => side.appendChild(createLink(item)));
        root.appendChild(side);
        document.body.prepend(root);
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", renderNavigation);
    else renderNavigation();
})();

/* LEONES — shared navigation runtime */
(() => {
    "use strict";
    const navigation = [
        ["Inicio", "index.html", "top"], ["Proyectos", "proyectos.html", "top"],
        ["Atlas", "atlas.html", "project"], ["Pilares", "pilares.html", "project"], ["Arquitectura", "arquitectura.html", "project"], ["Diagramas", "diagramas.html", "project"], ["Pila", "pila.html", "project"], ["Operación", "operacion.html", "project"],
        ["Aplicación", "app.html", "top"], ["Scripts", "scripts.html", "application"], ["Resultados", "resultados.html", "application"], ["Evaluación", "evaluacion.html", "application"], ["Recomendaciones", "recommendations.html", "application"], ["Recomendaciones de visita", "recomendaciones-visita.html", "application"], ["Recomendar a LEONES", "recomendar.html", "application"],
        ["Manada", "manada.html", "top"], ["Prospección", "prospeccion.html", "top"], ["Horizonte", "horizon.html", "top"], ["Contacto", "contacto.html", "top"]
    ];
    const base = "assets/graphics/leones-logo-principal.jpg";
    const currentPath = window.location.pathname.split("/").pop() || "index.html";
    const currentPage = navigation.find(([, path]) => path === currentPath);
    function createLink([label, path, level]) {
        const link = document.createElement("a"); link.className = `level-${level}`; link.href = path; link.textContent = label;
        if (path === currentPath) { link.classList.add("active"); link.setAttribute("aria-current", "page"); }
        return link;
    }
    function renderNavigation() {
        if (document.querySelector(".leones-nav-runtime")) return;
        document.body.classList.add("has-leones-navigation");
        const root = document.createElement("nav"); root.className = "leones-nav-runtime"; root.setAttribute("aria-label", "Navegación principal");
        const skip = document.createElement("a"); skip.className = "skip-link"; skip.href = "#main"; skip.textContent = "Saltar al contenido"; root.appendChild(skip);
        const crumb = document.createElement("div"); crumb.className = "site-crumb"; const ci = document.createElement("div"); ci.className = "site-crumb-inner";
        const home = document.createElement("a"); home.href = "index.html"; home.textContent = "Inicio"; ci.appendChild(home); const sep = document.createElement("span"); sep.textContent = "›"; ci.appendChild(sep);
        const group = currentPage?.[2]; if (group && group !== "top") { const gl = document.createElement("a"); gl.href = group === "project" ? "proyectos.html" : "app.html"; gl.textContent = group === "project" ? "Proyectos" : "Aplicación"; ci.appendChild(gl); const gs = document.createElement("span"); gs.textContent = "›"; ci.appendChild(gs); }
        const cur = document.createElement("strong"); cur.textContent = currentPage?.[0] || document.title; ci.appendChild(cur); crumb.appendChild(ci); root.appendChild(crumb);
        const toggle = document.createElement("button"); toggle.className = "leones-nav-toggle"; toggle.type = "button"; toggle.setAttribute("aria-controls", "leones-side"); toggle.setAttribute("aria-expanded", "false"); toggle.textContent = "☰ Menú"; root.appendChild(toggle);
        const backdrop = document.createElement("div"); backdrop.className = "site-side-backdrop"; root.appendChild(backdrop);
        const side = document.createElement("aside"); side.className = "site-side"; side.id = "leones-side"; side.setAttribute("aria-label", "Secciones LEONES");
        const brand = document.createElement("div"); brand.className = "site-brand"; const bl = document.createElement("a"); bl.href = "index.html"; bl.setAttribute("aria-label", "LEONES · Inicio");
        const bi = document.createElement("img"); bi.src = base; bi.alt = "LEONES · dos leones"; bi.width = 72; bi.height = 72; bi.className = "leones-sidebar-face"; bl.appendChild(bi); brand.appendChild(bl); side.appendChild(brand);
        const title = document.createElement("div"); title.className = "side-title"; title.textContent = "Navegación"; side.appendChild(title);
        navigation.forEach((item) => side.appendChild(createLink(item))); root.appendChild(side); document.body.prepend(root);
        const main = document.querySelector("main"); if (main && !main.id) main.id = "main";
        const close = () => { side.classList.remove("is-open"); backdrop.classList.remove("is-open"); toggle.setAttribute("aria-expanded", "false"); };
        toggle.addEventListener("click", () => { const open = !side.classList.contains("is-open"); side.classList.toggle("is-open", open); backdrop.classList.toggle("is-open", open); toggle.setAttribute("aria-expanded", String(open)); });
        backdrop.addEventListener("click", close); side.addEventListener("click", (e) => { if (e.target.closest("a")) close(); }); document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", renderNavigation); else renderNavigation();
})();

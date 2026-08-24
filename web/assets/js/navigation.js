/* LEONES — navegación común */
(() => {
    "use strict";
    const navigation = [
        ["Inicio", "index.html", "top"],
        ["Proyectos", "proyectos.html", "top"],
        ["Atlas", "atlas.html", "project"],
        ["Pilares", "pilares.html", "project"],
        ["Arquitectura", "arquitectura.html", "project"],
        ["Pila", "pila.html", "project"],
        ["Operación", "operacion.html", "project"],
        ["Conocimiento de IA en Local", "conocimiento.html", "top"],
        ["Aplicación", "app.html", "top"],
        ["Evaluación", "evaluacion.html", "application"],
        ["Recomendaciones", "recommendations.html", "application"],
        ["Recomendar a LEONES", "recomendar.html", "application"],
        ["Resultados", "resultados.html", "application"],
        ["Manada", "manada.html", "top"],
        ["Prospección", "prospeccion.html", "top"],
        ["Horizonte", "horizon.html", "top"],
        ["Contacto", "contacto.html", "top"],
    ];
    const base = "assets/graphics/leones-logo-principal.jpg";
    const currentPath = window.location.pathname.split("/").pop() || "index.html";
    const currentPage = navigation.find(([, path]) => path === currentPath);
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
        if (document.querySelector(".leones-nav-runtime")) return;
        document.body.classList.add("has-leones-navigation");
        const root = document.createElement("nav");
        root.className = "leones-nav-runtime";
        root.setAttribute("aria-label", "Navegación principal");
        const skip = document.createElement("a");
        skip.className = "skip-link";
        skip.href = "#main";
        skip.textContent = "Saltar al contenido";
        root.appendChild(skip);
        const crumb = document.createElement("div");
        crumb.className = "site-crumb";
        const ci = document.createElement("div");
        ci.className = "site-crumb-inner";
        const home = document.createElement("a");
        home.href = "index.html";
        home.textContent = "Inicio";
        ci.appendChild(home);
        if (currentPage?.[2] && currentPage[2] !== "top") {
            const sep = document.createElement("span");
            sep.textContent = "›";
            ci.appendChild(sep);
            const gl = document.createElement("a");
            gl.href = currentPage[2] === "project" ? "proyectos.html" : "app.html";
            gl.textContent = currentPage[2] === "project" ? "Proyectos" : "Aplicación";
            ci.appendChild(gl);
        }
        const sep2 = document.createElement("span");
        sep2.textContent = "›";
        ci.appendChild(sep2);
        const cur = document.createElement("strong");
        cur.textContent = currentPage?.[0] || document.title;
        ci.appendChild(cur);
        crumb.appendChild(ci);
        root.appendChild(crumb);
        const toggle = document.createElement("button");
        toggle.className = "leones-nav-toggle";
        toggle.type = "button";
        toggle.setAttribute("aria-controls", "leones-side");
        toggle.setAttribute("aria-expanded", "false");
        toggle.textContent = "☰ Menú";
        root.appendChild(toggle);
        const backdrop = document.createElement("div");
        backdrop.className = "site-side-backdrop";
        root.appendChild(backdrop);
        const side = document.createElement("aside");
        side.className = "site-side";
        side.id = "leones-side";
        side.setAttribute("aria-label", "Secciones LEONES");
        const brand = document.createElement("div");
        brand.className = "site-brand";
        const bl = document.createElement("a");
        bl.href = "index.html";
        bl.setAttribute("aria-label", "LEONES · Inicio");
        const bi = document.createElement("img");
        bi.src = base;
        bi.alt = "LEONES";
        bi.width = 112;
        bi.height = 62;
        bl.appendChild(bi);
        brand.appendChild(bl);
        side.appendChild(brand);
        const title = document.createElement("div");
        title.className = "side-title";
        title.textContent = "Explorar";
        side.appendChild(title);
        navigation.forEach((item) => side.appendChild(createLink(item)));
        root.appendChild(side);
        document.body.prepend(root);
        const main = document.querySelector("main");
        if (main && !main.id) main.id = "main";
        const close = () => {
            side.classList.remove("is-open");
            backdrop.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
        };
        toggle.addEventListener("click", () => {
            const open = !side.classList.contains("is-open");
            side.classList.toggle("is-open", open);
            backdrop.classList.toggle("is-open", open);
            toggle.setAttribute("aria-expanded", String(open));
        });
        backdrop.addEventListener("click", close);
        side.addEventListener("click", (e) => {
            if (e.target.closest("a")) close();
        });
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") close();
        });
    }
    if (document.readyState === "loading")
        document.addEventListener("DOMContentLoaded", renderNavigation);
    else renderNavigation();
})();

/* LEONES — Prospección: publicar explicación funcional en español */
(() => {
    "use strict";
    const page = window.location.pathname.split("/").pop() || "index.html";
    if (page !== "prospeccion.html") return;

    const load = () => {
        if (document.querySelector('script[data-leones-prospeccion-explanations="1"]')) return;
        const script = document.createElement("script");
        script.src = "assets/js/prospeccion-explanations.js?v=2026-08-24-1";
        script.dataset.leonesProspeccionExplanations = "1";
        script.defer = true;
        document.head.appendChild(script);
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
    else load();
})();

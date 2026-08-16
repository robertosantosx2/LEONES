/* LEONES — shared navigation runtime + identity icons */
(() => {
    "use strict";
    const navigation = [
        ["Inicio", "index.html", "top"],
        ["Proyectos", "proyectos.html", "top"],
        ["Atlas", "atlas.html", "project"],
        ["Pilares", "pilares.html", "project"],
        ["Arquitectura", "arquitectura.html", "project"],
        ["Diagramas", "diagramas.html", "project"],
        ["Pila", "pila.html", "project"],
        ["Operación", "operacion.html", "project"],
        ["Aplicación", "app.html", "top"],
        ["Scripts", "scripts.html", "application"],
        ["Resultados", "resultados.html", "application"],
        ["Evaluación", "evaluacion.html", "application"],
        ["Recomendaciones", "recommendations.html", "application"],
        ["Recomendaciones de visita", "recomendaciones-visita.html", "application"],
        ["Recomendar a LEONES", "recomendar.html", "application"],
        ["Manada", "manada.html", "top"],
        ["Prospección", "prospeccion.html", "top"],
        ["Horizonte", "horizon.html", "top"],
        ["Contacto", "contacto.html", "top"],
    ];
    const identity = {
        prospeccion: ["🔎", "Prospección"],
        atlas: ["▦", "Atlas"],
        task: ["◉", "Task Intelligence"],
        router: ["↗", "Router"],
        quant: ["⚖", "Quant"],
        finetune: ["⚙", "Fine-Tuning"],
        hardware: ["▣", "Hardware"],
        modelos: ["◆", "Modelos"],
        inferencia: ["▶", "Inferencia"],
        agents: ["⚒", "Agents"],
        evidencia: ["✓", "Evidencia"],
        privacidad: ["◆", "Privacidad"],
        publicacion: ["↑", "Publicación"],
        manada: ["♟", "Manada"],
        stats: ["▥", "Stats"],
        herramientas: ["⚒", "Herramientas"],
        arquitectura: ["⌘", "Arquitectura"],
        pilares: ["✦", "Pilares"],
        acerca: ["i", "Acerca de"],
    };

    // La navegación SIEMPRE usa el JPG oficial de los DOS LEONES.
    const base = "assets/graphics/leones-section-base.jpg";
    const currentPath = window.location.pathname.split("/").pop() || "index.html";
    const currentPage = navigation.find(([label, path]) => path === currentPath);

    function createLink([label, path, level]) {
        const link = document.createElement("a");
        link.className = `level-${level}`;
        link.href = path;
        link.textContent = label;
        if (path === currentPath) {
            link.classList.add("active");
            link.setAttribute("aria-current", "page");
        }
        return link;
    }
    function roleFromSrc(src = "") {
        const m = src.match(/leones-([a-z0-9-]+)\.svg/i);
        return m ? m[1].replace("-", "_") : "";
    }
    function decorateImage(img) {
        if (!img || img.dataset.leonesIdentity === "1") return;
        const role = roleFromSrc(img.getAttribute("src") || "");
        const key = role.replace(/_/g, "-").toLowerCase();
        const data = identity[key] || identity[role] || ["✦", img.alt || "LEONES"];
        img.dataset.leonesIdentity = "1";
        img.src = base;
        img.classList.add("leones-composite-face");
        img.width = 44;
        img.height = 44;
        img.alt = img.alt || `LEONES · ${data[1]}`;
        const wrap = document.createElement("span");
        wrap.className = "leones-composite-icon";
        wrap.setAttribute("aria-label", data[1]);
        const badge = document.createElement("span");
        badge.className = "leones-composite-badge";
        badge.textContent = data[0];
        badge.setAttribute("aria-hidden", "true");
        img.parentNode.insertBefore(wrap, img);
        wrap.appendChild(img);
        wrap.appendChild(badge);
    }
    function decorateExistingLogos() {
        document
            .querySelectorAll('img[src*="/graphics/logos/"], img[src*="assets/graphics/logos/"]')
            .forEach(decorateImage);
    }
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
        const sep = document.createElement("span");
        sep.textContent = "›";
        ci.appendChild(sep);
        const group = currentPage?.[2];
        if (group && group !== "top") {
            const gl = document.createElement("a");
            gl.href = group === "project" ? "proyectos.html" : "app.html";
            gl.textContent = group === "project" ? "Proyectos" : "Aplicación";
            ci.appendChild(gl);
            const gs = document.createElement("span");
            gs.textContent = "›";
            ci.appendChild(gs);
        }
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
        bi.alt = "LEONES · dos leones";
        bi.width = 72;
        bi.height = 72;
        bi.className = "leones-sidebar-face";
        bl.appendChild(bi);
        brand.appendChild(bl);
        side.appendChild(brand);
        const title = document.createElement("div");
        title.className = "side-title";
        title.textContent = "Navegación";
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
    function boot() {
        renderNavigation();
        decorateExistingLogos();
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
})();

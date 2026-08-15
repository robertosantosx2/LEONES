/*
 * LEONES — shared navigation runtime
 *
 * Responsibilities:
 *   1. Render one consistent navigation on every static page.
 *   2. Reserve sidebar space through a body class.
 *   3. Provide keyboard- and mobile-friendly navigation.
 *
 * The script deliberately does not style or reposition page content.
 */

(() => {
    "use strict";

    const navigation = [
        ["Inicio", "index.html", "top"],
        ["Proyectos", "proyecto.html", "top"],
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
        ["Manada", "manada.html", "top"],
        ["Prospección", "prospeccion.html", "top"],
        ["Horizonte", "horizon.html", "top"],
        ["Contacto", "contacto.html", "top"]
    ];

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

    function renderNavigation() {
        if (document.querySelector(".leones-nav-runtime")) {
            return;
        }

        document.body.classList.add("has-leones-navigation");

        const navigationRoot = document.createElement("nav");
        navigationRoot.className = "leones-nav-runtime";
        navigationRoot.setAttribute("aria-label", "Navegación principal");

        const skipLink = document.createElement("a");
        skipLink.className = "skip-link";
        skipLink.href = "#main";
        skipLink.textContent = "Saltar al contenido";
        navigationRoot.appendChild(skipLink);

        const breadcrumb = document.createElement("div");
        breadcrumb.className = "site-crumb";

        const breadcrumbInner = document.createElement("div");
        breadcrumbInner.className = "site-crumb-inner";

        const home = document.createElement("a");
        home.href = "index.html";
        home.textContent = "Inicio";
        breadcrumbInner.appendChild(home);

        const separator = document.createElement("span");
        separator.setAttribute("aria-hidden", "true");
        separator.textContent = "›";
        breadcrumbInner.appendChild(separator);

        const group = currentPage?.[2];
        if (group && group !== "top") {
            const groupLink = document.createElement("a");
            groupLink.href = group === "project" ? "proyecto.html" : "app.html";
            groupLink.textContent = group === "project" ? "Proyectos" : "Aplicación";
            breadcrumbInner.appendChild(groupLink);

            const groupSeparator = document.createElement("span");
            groupSeparator.setAttribute("aria-hidden", "true");
            groupSeparator.textContent = "›";
            breadcrumbInner.appendChild(groupSeparator);
        }

        const current = document.createElement("strong");
        current.textContent = currentPage?.[0] || document.title;
        current.setAttribute("aria-current", "page");
        breadcrumbInner.appendChild(current);

        breadcrumb.appendChild(breadcrumbInner);
        navigationRoot.appendChild(breadcrumb);

        const toggle = document.createElement("button");
        toggle.className = "leones-nav-toggle";
        toggle.type = "button";
        toggle.setAttribute("aria-controls", "leones-side");
        toggle.setAttribute("aria-expanded", "false");
        toggle.textContent = "☰ Menú";
        navigationRoot.appendChild(toggle);

        const backdrop = document.createElement("div");
        backdrop.className = "site-side-backdrop";
        backdrop.setAttribute("aria-hidden", "true");
        navigationRoot.appendChild(backdrop);

        const sidebar = document.createElement("aside");
        sidebar.className = "site-side";
        sidebar.id = "leones-side";
        sidebar.setAttribute("aria-label", "Secciones LEONES");

        const brand = document.createElement("div");
        brand.className = "site-brand";

        const brandLink = document.createElement("a");
        brandLink.href = "index.html";
        brandLink.setAttribute("aria-label", "LEONES · Inicio");

        const brandImage = document.createElement("img");
        brandImage.src = "assets/graphics/leones-logo-principal.svg";
        brandImage.alt = "LEONES";

        brandLink.appendChild(brandImage);
        brand.appendChild(brandLink);
        sidebar.appendChild(brand);

        const title = document.createElement("div");
        title.className = "side-title";
        title.textContent = "Navegación";
        sidebar.appendChild(title);

        navigation.forEach((item) => {
            sidebar.appendChild(createLink(item));
        });

        navigationRoot.appendChild(sidebar);
        document.body.prepend(navigationRoot);

        const main = document.querySelector("main");
        if (main && !main.id) {
            main.id = "main";
        }

        const closeMenu = () => {
            sidebar.classList.remove("is-open");
            backdrop.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
        };

        toggle.addEventListener("click", () => {
            const isOpen = !sidebar.classList.contains("is-open");
            sidebar.classList.toggle("is-open", isOpen);
            backdrop.classList.toggle("is-open", isOpen);
            toggle.setAttribute("aria-expanded", String(isOpen));
        });

        backdrop.addEventListener("click", closeMenu);
        sidebar.addEventListener("click", (event) => {
            if (event.target.closest("a")) {
                closeMenu();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeMenu();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", renderNavigation);
    } else {
        renderNavigation();
    }
})();

/* app.js — Global client-side logic for MailMind
   ================================================================
   Handles sidebar active state by matching <a> href attributes
   against the current page path.
   ================================================================ */

document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll("aside .nav .nav-link[data-page]");

    navLinks.forEach(link => {
        const page = link.getAttribute("data-page");
        if (!page) return;

        // Exact match for home ("/"), startsWith for other pages
        const isActive =
            (page === "/" && currentPath === "/") ||
            (page !== "/" && currentPath.startsWith(page));

        if (isActive) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });
});

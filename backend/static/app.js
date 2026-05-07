document.addEventListener("DOMContentLoaded", () => {
    // Basic navigation active state handling for the sidebar
    const currentPath = window.location.pathname;
    const navButtons = document.querySelectorAll("aside nav button");

    navButtons.forEach(button => {
        const span = button.querySelector("span.text-label-sm");
        if (!span) return;
        
        const text = span.textContent.trim().toLowerCase();
        
        let pathMatches = false;
        if (text === "home" && currentPath === "/") pathMatches = true;
        if (text === "email" && currentPath.startsWith("/email")) pathMatches = true;
        if (text === "crafter" && currentPath.startsWith("/crafter")) pathMatches = true;
        if (text === "orders" && currentPath.startsWith("/orders")) pathMatches = true;
        if (text === "settings" && currentPath.startsWith("/settings")) pathMatches = true;

        if (pathMatches) {
            // Apply active styles
            button.classList.remove("text-on-surface-variant", "dark:text-surface-variant");
            button.classList.add("text-primary", "dark:text-primary-fixed-dim", "border-r-4", "border-primary");
            
            const icon = button.querySelector(".material-symbols-outlined");
            if (icon) {
                icon.style.fontVariationSettings = "'FILL' 1";
            }
        } else {
            // Remove active styles (in case they were hardcoded in HTML)
            button.classList.remove("text-primary", "dark:text-primary-fixed-dim", "border-r-4", "border-primary");
            button.classList.add("text-on-surface-variant", "dark:text-surface-variant");
            
            const icon = button.querySelector(".material-symbols-outlined");
            if (icon) {
                icon.style.fontVariationSettings = "'FILL' 0";
            }
        }
    });
});

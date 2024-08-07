import { isHrefCurrentPage } from "../_utils.js"

// Add active class to current nav-lik
const navLinks = document.querySelectorAll(".settings-nav .nav-link")
for (const link of navLinks) {
    if (isHrefCurrentPage(link.href)) {
        link.classList.add("active")
        link.ariaCurrent = "page"
        break
    }
}

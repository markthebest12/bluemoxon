/* BlueMoxon Marketing Site — Shared JavaScript */

function toggleMenu() {
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');
    if (!hamburger || !navLinks) return;
    hamburger.classList.toggle('active');
    navLinks.classList.toggle('active');
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-links a').forEach((link) => {
        link.addEventListener('click', () => {
            const hamburger = document.querySelector('.hamburger');
            const navLinks = document.querySelector('.nav-links');
            if (!hamburger || !navLinks) return;
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
        });
    });
});

/* BlueMoxon Marketing Site — Shared JavaScript */

function toggleMenu() {
    var hamburger = document.querySelector('.hamburger');
    var navLinks = document.querySelector('.nav-links');
    hamburger.classList.toggle('active');
    navLinks.classList.toggle('active');
}

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.nav-links a').forEach(function (link) {
        link.addEventListener('click', function () {
            var hamburger = document.querySelector('.hamburger');
            var navLinks = document.querySelector('.nav-links');
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
        });
    });
});

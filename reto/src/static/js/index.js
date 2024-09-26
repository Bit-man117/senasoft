var mapSmall = L.map('map').setView([4.5709, -74.2973], 5); // Centro de Colombia

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    noWrap: true // Evitar que el mapa se repita
}).addTo(mapSmall);

// Definición del icono personalizado
var customIcon = L.icon({
    iconUrl: 'https://certificadossena.net/wp-content/uploads/2022/10/logo-sena-negro-svg-2022.svg', // Reemplaza con la URL de tu icono
    iconSize: [32, 32], // Tamaño del ícono
    iconAnchor: [16, 32], // Punto del ícono que se alineará con las coordenadas
    popupAnchor: [0, -32] // Punto desde el que se abrirá el popup
});

// Lista de regionales del SENA
var regionales = [
    { nombre: "SENA Bogotá", lat: 4.60971, lon: -74.08175 },
    { nombre: "SENA Antioquia", lat: 6.25184, lon: -75.56359 },
    { nombre: "SENA Valle del Cauca", lat: 3.42332, lon: -76.52493 },
    { nombre: "SENA Atlántico", lat: 10.96389, lon: -74.79694 },
    { nombre: "SENA Santander", lat: 7.11381, lon: -73.1198 },
    { nombre: "SENA Bolívar", lat: 10.40236, lon: -75.51478 },
    { nombre: "SENA Cundinamarca", lat: 4.60017, lon: -74.14361 },
    { nombre: "SENA Cesar", lat: 10.43333, lon: -74.18883 },
    { nombre: "SENA Huila", lat: 2.72672, lon: -75.30028 },
    { nombre: "SENA Magdalena", lat: 10.47371, lon: -74.20393 },
    { nombre: "SENA Nariño", lat: 1.21253, lon: -77.27365 },
    { nombre: "SENA Norte de Santander", lat: 7.90889, lon: -72.50539 },
    { nombre: "SENA Quindío", lat: 4.53611, lon: -75.64167 },
    { nombre: "SENA Risaralda", lat: 4.81134, lon: -75.69719 },
    { nombre: "SENA Sucre", lat: 9.31314, lon: -75.20271 },
    { nombre: "SENA Tolima", lat: 4.43711, lon: -75.22004 },
    { nombre: "SENA Caquetá", lat: 1.57351, lon: -75.61682 },
    // { nombre: "SENA San Andrés y Providencia", lat: 12.58333, lon: -81.70000 }
];

// Agregar marcadores al mapa pequeño
regionales.forEach(function (regional) {
    L.marker([regional.lat, regional.lon], { icon: customIcon }).addTo(mapSmall)
        .bindPopup(regional.nombre)
        .openPopup();
});

// Inicializar el modal
var modal = document.getElementById("myModal");
var closeModal = document.getElementsByClassName("close")[0];

// Función para abrir el mapa completo en el modal
function openFullMap() {
    modal.style.display = "block";
    var fullMap = L.map('fullMap').setView([4.5709, -74.2973], 5); // Centro de Colombia

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        noWrap: true // Evitar que el mapa se repita
    }).addTo(fullMap);

    // Agregar los mismos marcadores al mapa completo
    regionales.forEach(function (regional) {
        L.marker([regional.lat, regional.lon], { icon: customIcon }).addTo(fullMap)
            .bindPopup(regional.nombre)
            .openPopup();
    });
}

// Abrir el modal al hacer clic en el enlace "Consultar"
document.querySelector('.consultar-permiso').onclick = function (event) {
    event.preventDefault(); // Evitar el comportamiento por defecto del enlace
    openFullMap();
};

// Cerrar el modal al hacer clic en el "x"
closeModal.onclick = function () {
    modal.style.display = "none";
}

// Cerrar el modal al hacer clic fuera del contenido
window.onclick = function (event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

// --------GALERIA DEL PUBLICACIONES --------
const galleryItems = document.querySelectorAll('.gallery-item');
let currentIndex = 0;

function showNextSet() {
    // Ocultamos todas las publicaciones
    galleryItems.forEach(item => item.classList.remove('active'));

    // Mostramos las siguientes tres publicaciones
    for (let i = 0; i < 3; i++) {
        const index = (currentIndex + i) % galleryItems.length;
        galleryItems[index].classList.add('active');
    }

    // Actualizamos el índice para el próximo ciclo
    currentIndex = (currentIndex + 3) % galleryItems.length; // Incrementa en 3
}

// Muestra las publicaciones iniciales
showNextSet(); // Muestra el primer conjunto al cargar

// Cambiamos las publicaciones cada 4 segundos
setInterval(showNextSet, 4000);
/* -------------------------------- */

/* -------------------------------- */

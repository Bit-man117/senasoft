// Función para validar las horas de entrada y salida
function validarHoras() {
    var horaSalida = document.getElementById('horaSalidas').value;
    var horaEntrada = document.getElementById('horaEntradas').value;

    // Validar solo si ambos campos tienen valores
    if (horaSalida && horaEntrada) {
        if (horaEntrada < horaSalida) {
            Swal.fire({
                title: "La hora de entrada no puede ser mayor que la hora de salida.",
                icon: "info",
                confirmButtonText: 'Aceptar'
            }).then((result) => {
                // Limpiar los campos si el usuario confirma el alerta
                if (result.isConfirmed) {
                    document.getElementById('horaEntradas').value = '';
                    document.getElementById('horaSalidas').value = '';
                }
            });
        }
    }
}

// Configurar los eventos para validar las horas cuando cambian
document.getElementById('horaSalidas').addEventListener('input', validarHoras);
document.getElementById('horaEntradas').addEventListener('input', validarHoras);

// Función para manejar el cambio del tipo de servicio
function handleServiceTypeChange() {
    var tipoSeleccionado = document.getElementById("service-type").value;

    // Oculta todos los grupos de campos
    document.getElementById("hora-entrada-group").style.display = "none";
    document.getElementById("hora-salida-group").style.display = "none";
    document.getElementById("salida-regreso-group").style.display = "none";

    // Limpia los valores de los campos
    document.getElementById("horaEntrada").value = "";
    document.getElementById("horaSalida").value = "";
    document.getElementById("fecha").value = "";
    document.getElementById("horaSalidas").value = "";
    document.getElementById("horaEntradas").value = "";

    // Reinicia el atributo required de los campos
    document.getElementById("fecha").removeAttribute("required");
    document.getElementById("horaSalida").removeAttribute("required");
    document.getElementById("horaEntrada").removeAttribute("required");

    // Muestra los campos correspondientes según la opción seleccionada
    if (tipoSeleccionado === "1") {
        document.getElementById("hora-entrada-group").style.display = "block";
        document.getElementById("horaEntrada").setAttribute("required", "true");
    } else if (tipoSeleccionado === "2") {
        document.getElementById("hora-salida-group").style.display = "block";
        document.getElementById("horaSalida").setAttribute("required", "true");
    } else if (tipoSeleccionado === "3") {
        document.getElementById("salida-regreso-group").style.display = "flex";
        document.getElementById("fecha").setAttribute("required", "true");
        document.getElementById("horaSalidas").setAttribute("required", "true");
        document.getElementById("horaEntradas").setAttribute("required", "true");
    }
}

// Función para establecer la fecha y hora mínima en los inputs
function setMinDateTime() {
    const now = new Date();

    // Convertir la fecha y hora a la zona horaria de Colombia (UTC-5)
    const colombiaOffset = -5 * 60; // -5 horas en minutos
    const localDate = new Date(now.getTime() + colombiaOffset * 60 * 1000);

    const dateString = localDate.toISOString().split('T')[0]; // Obtener la fecha en formato YYYY-MM-DD
    const timeString = localDate.toISOString().split('T')[1].slice(0, 5); // Obtener la hora en formato HH:MM

    // Establecer la fecha mínima en el input de fecha
    document.getElementById('fecha').setAttribute('min', dateString);

    // Establecer la fecha y hora mínimas en los inputs de datetime-local
    document.getElementById('horaEntrada').setAttribute('min', dateString + 'T00:00');
    document.getElementById('horaSalida').setAttribute('min', dateString + 'T00:00');
}

// Llama a la función para establecer la fecha mínima y hora mínima cuando el documento esté listo
document.addEventListener("DOMContentLoaded", function () {
    handleServiceTypeChange(); // Llama a la función para manejar el estado inicial
    setMinDateTime(); // Establece la fecha y hora mínima
});

/* BUSCAR INSTRUCTOR */
$(document).ready(function () {
    const suggestionsList = $('#suggestions');
    const inputNombreInstructor = $('#NombreInstructor');

    inputNombreInstructor.on('input', function () {
        const userInput = $(this).val().trim();

        if (userInput.length >= 3) {
            $.ajax({
                url: '/buscar_instructores',
                method: 'GET',
                data: { nombre: userInput },
                success: function (response) {
                    suggestionsList.empty();
                    try {
                        if (response.hasOwnProperty('mensaje')) {
                            Swal.fire({
                                title: response.mensaje,
                                icon: "error"
                            }).then(function () {
                                inputNombreInstructor.val(''); // Borrar el texto del input
                            });
                        } else {
                            response.forEach(function (instructor) {
                                suggestionsList.append('<li>' + instructor + '</li>');
                            });
                            suggestionsList.show();
                        }
                    } catch (error) {
                        console.error('Error processing response:', error);
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.error('AJAX error:', textStatus, errorThrown);
                }
            });
        } else {
            suggestionsList.empty();
            suggestionsList.hide();
        }
    });

    $('#suggestions').on('click', 'li', function () {
        const selectedInstructor = $(this).text();
        inputNombreInstructor.val(selectedInstructor);
        suggestionsList.empty();
        suggestionsList.hide();
    });
});

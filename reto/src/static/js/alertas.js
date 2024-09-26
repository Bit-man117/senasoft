$(document).ready(function () {
    $('#login-form').submit(function (event) {
        event.preventDefault();

        var formData = $(this).serialize();

        // Antes de la solicitud AJAX, restablecer estilos
        $('#mensaje-error').hide();
        $('#login-form input').removeClass('error');

        $.ajax({
            type: 'POST',
            url: '/login',
            data: formData,
            dataType: 'json',
            success: function (response) {
                console.log(response);

                if (response.redirect) {
                    window.location.href = response.redirect;
                } else if (response.error) {
                    var decodedError = decodeURIComponent(response.error);
                    $('#mensaje-error').text(decodedError).show();
                    $('#login-form input').addClass('error');
                } else {
                    console.log('Respuesta del servidor inesperada:', response);
                }
            },
            error: function (xhr, status, error) {
                console.log('Error:', xhr.responseText);
            }
        });
    });
});


    function solicitarAlquiler(idBicicleta) {
        fetch('/alquilar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ id_bicicleta: idBicicleta }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Alquiler registrado exitosamente.');
                // Opcional: Actualizar la UI o eliminar la bicicleta del listado
            } else {
                alert('Error al registrar el alquiler: ' + data.message);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error al registrar el alquiler.');
        });
    }

/* ventana container emergente */
function desplegable1() {
    var emergentes = document.getElementsByClassName("container1");
    for (var i = 0; i < emergentes.length; i++) {
      emergentes[i].style.display = "flex";
    }
  }
  function cerrarEmergentes1() {
    var emergentes = document.getElementsByClassName("container1");
    for (var i = 0; i < emergentes.length; i++) {
      emergentes[i].style.display = "none";
    }
  }
  /* ventana container emergente2 */
  function desplegable2() {
    var emergentes = document.getElementsByClassName("container2");
    for (var i = 0; i < emergentes.length; i++) {
      emergentes[i].style.display = "flex";
    }
  }
  function cerrarEmergentes2() {
    var emergentes = document.getElementsByClassName("container2");
    for (var i = 0; i < emergentes.length; i++) {
      emergentes[i].style.display = "none";
    }
  }
  
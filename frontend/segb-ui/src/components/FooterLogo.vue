<template>
  <footer class="footer-bar">


    <div class="links">
            <a class="info" href="https://segb.readthedocs.io/en/latest/index.html" target="_blank">𝒊</a>
            <a class="info" href="https://www.gsi.upm.es/es/component/jresearch/?view=member&task=show&id=347"
                target="_blank">✆</a>
    </div>
   
    <div class="footer-text">
        <p>
          Developed by <strong>GSI – Grupo de Sistemas Inteligentes</strong>
        </p>
        <p>
          José Luis Benítez Santana · Álvaro Carrera Barroso · Gloria Cumia
          Espinosa de los Monteros
        </p>
      </div>

       <div class="footer-left">
      <img
        class="footer-logo"
        src="https://www.gsi.upm.es/images/logos/gsi.png"
        alt="GSI logo"
        />
    </div>
  </footer>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500&display=swap');

.footer-bar {
  bottom: 0;
  left: 0;
  width: 100%;
  background: #cacaca;
  color: #000000;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  font-family: 'Montserrat', sans-serif;
  font-size: 1rem;
  height: 7rem;
}

.footer-left {
  display: flex;
  align-items: center;
  text-align: left;
  flex-wrap: wrap;
  gap: 16px;
}

.footer-logo {
  max-height: 4rem;
}

.footer-text p {
  margin: 2px 0;
  line-height: 1.4;
}

.links {
    display: flex;
    gap: 20px;
}

.info {
    padding: .4rem;
    border-radius: 8px;
    text-decoration: none;
    color: #000;
    font-weight: 700;
    font-size: 30px;
    background-color: #8a8a8a;
    box-shadow: 2px 2px 8px rgba(0, 0, 0, .2);
    width: 40px;
    height: 40px;
    display: flex;
    justify-content: center;
}


</style>

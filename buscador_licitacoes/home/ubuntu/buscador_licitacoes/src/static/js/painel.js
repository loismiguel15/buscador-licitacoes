// Abre / fecha dropdown
function toggleDropdown(id) {
  const menu = document.getElementById(id);
  if (!menu) return;

  const aberto = menu.style.display === "block";
  menu.style.display = aberto ? "none" : "block";

  if (aberto) {
    atualizarTextoUFs(); // mantém como está
    atualizarTextoModalidades(); // novo para modalidades
  }
}

// Pega valores marcados
function getCheckedValues(name) {
  return Array.from(
    document.querySelectorAll(`input[name="${name}"]:checked`)
  ).map(el => el.value);
}

// ===== NÃO ALTERADO =====
function atualizarTextoUFs() {
  const selecionados = getCheckedValues("ufs");
  const botao = document.getElementById("ufsBtn");

  if (!botao) return;

  if (selecionados.length === 0) {
    botao.textContent = "Selecionar estados";
  } 
  else if (selecionados.length <= 3) {
    botao.textContent = selecionados.join(", ");
  } 
  else {
    botao.textContent = selecionados.length + " estados";
  }
}

// ===== NOVO PARA MODALIDADES =====
function atualizarTextoModalidades() {
  const selecionados = getCheckedValues("modalidades");
  const botao = document.getElementById("modalidadesBtn");

  if (!botao) return;

  if (selecionados.length === 0) {
    botao.textContent = "Selecionar modalidades";
  } 
  else if (selecionados.length <= 3) {
    botao.textContent = selecionados.join(", ");
  } 
  else {
    botao.textContent = selecionados.length + " modalidades";
  }
}

// Eventos quando carregar página
document.addEventListener("DOMContentLoaded", function () {

  // UF (mantido igual)
  document.querySelectorAll('input[name="ufs"]').forEach(input => {
    input.addEventListener("change", atualizarTextoUFs);
  });

  // Modalidades (novo)
  document.querySelectorAll('input[name="modalidades"]').forEach(input => {
    input.addEventListener("change", atualizarTextoModalidades);
  });

  atualizarTextoUFs();
  atualizarTextoModalidades();
});

// Fecha dropdown ao clicar fora
document.addEventListener("click", function (event) {

  document.querySelectorAll(".dropdown").forEach(dropdown => {

    if (!dropdown.contains(event.target)) {

      const menu = dropdown.querySelector(".dropdown-content");

      if (menu) menu.style.display = "none";

      atualizarTextoUFs();
      atualizarTextoModalidades();
    }

  });

});
// =========================
// DROPDOWNS
// =========================
function toggleDropdown(id) {
  const menu = document.getElementById(id);
  if (!menu) return;

  const aberto = menu.style.display === "block";
  menu.style.display = aberto ? "none" : "block";

  if (aberto) {
    atualizarTextoUFs();
    atualizarTextoModalidades();
  }
}

function getCheckedValues(name) {
  return Array.from(
    document.querySelectorAll(`input[name="${name}"]:checked`)
  ).map(el => el.value);
}

function atualizarTextoUFs() {
  const selecionados = getCheckedValues("ufs");
  const botao = document.getElementById("ufsBtn");

  if (!botao) return;

  if (selecionados.length === 0) {
    botao.textContent = "Selecionar estados";
  } else if (selecionados.length <= 3) {
    botao.textContent = selecionados.join(", ");
  } else {
    botao.textContent = selecionados.length + " estados";
  }
}

function atualizarTextoModalidades() {
  const selecionados = getCheckedValues("modalidades");
  const botao = document.getElementById("modalidadesBtn");

  if (!botao) return;

  if (selecionados.length === 0) {
    botao.textContent = "Selecionar modalidades";
  } else if (selecionados.length <= 3) {
    botao.textContent = selecionados.join(", ");
  } else {
    botao.textContent = selecionados.length + " modalidades";
  }
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('input[name="ufs"]').forEach(input => {
    input.addEventListener("change", atualizarTextoUFs);
  });

  document.querySelectorAll('input[name="modalidades"]').forEach(input => {
    input.addEventListener("change", atualizarTextoModalidades);
  });

  atualizarTextoUFs();
  atualizarTextoModalidades();
});

document.addEventListener("click", function (event) {
  document.querySelectorAll(".dropdown").forEach(dropdown => {
    if (!dropdown.contains(event.target)) {
      const menu = dropdown.querySelector(".dropdown-content");
      if (menu) menu.style.display = "none";

      atualizarTextoUFs();
      atualizarTextoModalidades();
    }
  });
});


// =========================
// TRATAMENTO DE BLOQUEIO
// =========================
async function tratarRespostaApi(response) {
  if (response.status === 401) {
    window.location.href = "/login.html";
    return null;
  }

  if (response.status === 403) {
    const data = await response.json().catch(() => ({}));

    if (data.redirect) {
      window.location.href = data.redirect;
      return null;
    }

    alert(data.message || "Seu acesso foi bloqueado.");
    return null;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || data.message || "Erro na requisição.");
  }

  return data;
}
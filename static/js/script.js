const form = document.getElementById("search-form");
const resultsList = document.getElementById("results-list");
const resultsEmpty = document.getElementById("results-empty");
const resultsNone = document.getElementById("results-none");
const resultsError = document.getElementById("results-error");
const resultsCount = document.getElementById("results-count");

const FORMAT_LABELS = {
  presentiel: "Présentiel",
  en_ligne: "En ligne",
  les_deux: "Présentiel / En ligne",
};

function hideAllStates() {
  resultsEmpty.hidden = true;
  resultsNone.hidden = true;
  resultsError.hidden = true;
  resultsList.hidden = true;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = String(str ?? "");
  return div.innerHTML;
}

function showError(messages) {
  hideAllStates();
  resultsError.hidden = false;
  resultsCount.hidden = true;
  const list = messages.map((m) => `<li>${escapeHtml(m)}</li>`).join("");
  resultsError.innerHTML = `<strong>Impossible de lancer la recherche :</strong><ul>${list}</ul>`;
}

function formatDispo(d) {
  return `${escapeHtml(d.jour)} ${escapeHtml(d.heure_debut)}–${escapeHtml(d.heure_fin)}`;
}

function buildCard(mentor) {
  const li = document.createElement("li");
  li.className = "mentor-card";

  const formatLabel = FORMAT_LABELS[mentor.format_mentorat] || mentor.format_mentorat;
  const nomSur = escapeHtml(mentor.nom);
  const premierPrenom = escapeHtml((mentor.nom || "").split(" ")[0]);

  const autresDispos = (mentor.disponibilites || []).map(formatDispo).join(" · ");

  const tags = (mentor.matieres_communes || [])
    .map((m) => `<span class="tag tag-match">${escapeHtml(m)}</span>`)
    .join("");

  const filiereTag = mentor.filiere_compatible
    ? `<span class="filiere-match">✓ Filière</span>`
    : "";

  li.innerHTML = `
    <div class="card-top">
      <div>
        <h3>${nomSur}</h3>
        <p class="card-meta">${escapeHtml(mentor.filiere)} · <span class="format-badge">${escapeHtml(formatLabel)}</span></p>
      </div>
      <div class="score-chip">${mentor.score}%</div>
    </div>

    <div class="link-bar">
      <span class="node">Vous</span>
      <span class="bar-track"><span class="bar-fill" style="width:${mentor.score}%"></span></span>
      <span class="node">${premierPrenom}</span>
    </div>

    <div class="tags">${tags}</div>

    <div class="card-details">
      <p><span class="detail-label">Créneau correspondant</span>${formatDispo(mentor.creneau_correspondant)}</p>
      <p><span class="detail-label">Toutes ses disponibilités</span>${autresDispos}</p>
    </div>

    <div class="score-breakdown">
      <span>Compétences ${mentor.score_matieres}%</span>
      <span>Horaire ${mentor.score_horaire}%</span>
      ${filiereTag}
    </div>
  `;

  return li;
}

function renderResults(resultats) {
  hideAllStates();

  if (resultats.length === 0) {
    resultsNone.hidden = false;
    resultsCount.hidden = true;
    return;
  }

  resultsList.innerHTML = "";
  resultats.forEach((mentor) => resultsList.appendChild(buildCard(mentor)));
  resultsList.hidden = false;

  resultsCount.hidden = false;
  resultsCount.textContent = `${resultats.length} résultat${resultats.length > 1 ? "s" : ""}`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const matieres = document.getElementById("matieres").value
    .split(",")
    .map((m) => m.trim())
    .filter(Boolean);

  const jour = document.getElementById("jour").value;
  const heure = document.getElementById("heure").value;
  const filiere = document.getElementById("filiere").value;

  const submitBtn = form.querySelector(".btn-search");
  submitBtn.disabled = true;
  submitBtn.querySelector("span").textContent = "Recherche…";

  try {
    const response = await fetch("/api/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ matieres, jour, heure, filiere }),
    });

    const data = await response.json();

    if (!response.ok) {
      showError(data.erreurs || ["Une erreur est survenue."]);
      return;
    }

    renderResults(data.resultats);
  } catch (err) {
    showError(["Impossible de contacter le serveur. Vérifiez que l'application Flask est bien lancée."]);
  } finally {
    submitBtn.disabled = false;
    submitBtn.querySelector("span").textContent = "Rechercher";
  }
});

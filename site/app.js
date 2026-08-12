const state = { stories: [], filter: "All", query: "" };
const $ = (selector) => document.querySelector(selector);
const esc = (value = "") => String(value).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[ch]));
const formatDate = (value) => {
  if (!value) return "Date unknown";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unknown" : new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(date);
};
function renderFilters() {
  const sources = ["All", ...new Set(state.stories.map(s => s.source).filter(Boolean))];
  $("#filters").innerHTML = sources.map(source => `<button class="filter ${state.filter === source ? "active" : ""}" data-filter="${esc(source)}">${esc(source)}</button>`).join("");
  document.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click", () => { state.filter = button.dataset.filter; render(); }));
}
function visibleStories() {
  const needle = state.query.trim().toLowerCase();
  return state.stories.filter(story => {
    const inSource = state.filter === "All" || story.source === state.filter;
    const text = [story.title, story.dek, story.why, story.takeaway, ...(story.tags || [])].join(" ").toLowerCase();
    return inSource && (!needle || text.includes(needle));
  });
}
function storyCard(story, index) {
  const tags = (story.tags || []).map(tag => `<span class="tag">${esc(tag)}</span>`).join("");
  const discussion = story.discussion_url ? `<a href="${esc(story.discussion_url)}" target="_blank" rel="noreferrer">Discuss ↗</a>` : "";
  const sourceLabel = story.source === "GitHub Trending" ? "GitHub" : (story.source || "Other");
  return `<article class="card">
    <div class="card-index" aria-hidden="true">${String(index + 1).padStart(2, "0")}</div>
    <div class="card-body">
      <div class="card-top"><span class="source">${esc(sourceLabel)}</span><span>${formatDate(story.published_at || story.discovered_at)}</span></div>
      <h2><a href="${esc(story.source_url)}" target="_blank" rel="noreferrer">${esc(story.title)}</a></h2>
      <p class="dek">${esc(story.dek)}</p>
      <p class="why"><strong>Why read</strong>${esc(story.why)}</p>
      <div class="takeaway"><strong>Try this idea</strong>${esc(story.takeaway)}</div>
      <div class="card-bottom"><div class="tags">${tags}</div><div class="card-links"><a href="${esc(story.source_url)}" target="_blank" rel="noreferrer">Read ↗</a>${discussion}</div></div>
    </div>
  </article>`;
}
function render() {
  renderFilters();
  const stories = visibleStories();
  $("#stories").innerHTML = stories.map(storyCard).join("");
  $("#empty").hidden = stories.length !== 0;
}
async function init() {
  try {
    const edition = await fetch("data/stories.json", { cache: "no-store" }).then(response => response.json());
    state.stories = Array.isArray(edition.stories) ? edition.stories : [];
    $("#edition-label").textContent = edition.edition_date ? `Edition · ${formatDate(edition.edition_date)}` : "First edition soon";
    render();
  } catch (error) {
    $("#edition-label").textContent = "Edition unavailable";
    $("#empty").hidden = false;
    $("#empty").textContent = "The edition could not be loaded.";
  }
}
$("#search").addEventListener("input", event => { state.query = event.target.value; render(); });
init();

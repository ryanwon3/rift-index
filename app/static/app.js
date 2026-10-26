(() => {
  "use strict";

  const page = document.body.dataset.page;

  const create = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };

  const fetchJson = async (url) => {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) {
      const detail = typeof payload.detail === "string" ? payload.detail : "The archive could not respond.";
      throw new Error(detail);
    }
    return payload;
  };

  const initExplore = async () => {
    const form = document.getElementById("search-form");
    const input = document.getElementById("query-input");
    const championSelect = document.getElementById("champion-select");
    const limitSelect = document.getElementById("limit-select");
    const status = document.getElementById("status-region");
    const grid = document.getElementById("results-grid");
    const count = document.getElementById("result-count");
    const submit = form.querySelector('button[type="submit"]');
    const params = new URLSearchParams(window.location.search);

    const showStatus = (title, message, kind = "idle") => {
      status.replaceChildren();
      status.hidden = false;
      status.classList.toggle("error", kind === "error");
      const glyph = create("span", "status-glyph", kind === "error" ? "!" : "✦");
      glyph.setAttribute("aria-hidden", "true");
      const copy = create("div");
      copy.append(create("strong", "", title), create("p", "", message));
      status.append(glyph, copy);
    };

    const restoreControls = () => {
      input.value = params.get("q") || "";
      championSelect.value = params.get("champion") || "";
      limitSelect.value = params.get("limit") || "12";
      const lineType = params.get("line_type") || "spoken";
      const radio = form.querySelector(`input[name="line_type"][value="${CSS.escape(lineType)}"]`);
      if (radio) radio.checked = true;
    };

    const loadChampions = async () => {
      const payload = await fetchJson("/api/champions");
      payload.champions.forEach((item) => {
        const option = create("option", "", item.champion);
        option.value = item.champion;
        championSelect.append(option);
      });
      restoreControls();
    };

    const renderResults = (payload) => {
      grid.replaceChildren();
      count.textContent = `${payload.count} ${payload.count === 1 ? "match" : "matches"}`;
      if (payload.results.length === 0) {
        showStatus("No lines found", "Try broadening the champion or line-type filters.");
        return;
      }
      status.hidden = true;

      payload.results.forEach((item) => {
        const card = create("article", "result-card");
        card.dataset.monogram = item.champion.slice(0, 1).toUpperCase();
        const meta = create("div", "card-meta");
        meta.append(
          create("span", "champion-name", item.champion),
          create("span", "", item.is_spoken ? "Spoken line" : "Action"),
        );
        const quote = create("blockquote", "", `“${item.text}”`);
        const percentage = Math.round(item.similarity * 100);
        const score = create("span", "similarity", `${percentage}% similarity`);
        score.setAttribute("aria-label", `${percentage} percent cosine similarity ranking signal, not confidence`);
        card.append(meta, quote, score);
        grid.append(card);
      });
    };

    const runSearch = async () => {
      const query = input.value.trim();
      if (query.length < 2) {
        showStatus("Add a little more detail", "Your search needs at least two characters.", "error");
        input.focus();
        return;
      }

      const selectedType = form.querySelector('input[name="line_type"]:checked').value;
      const next = new URLSearchParams({ q: query, line_type: selectedType, limit: limitSelect.value });
      if (championSelect.value) next.set("champion", championSelect.value);
      window.history.replaceState({}, "", `/?${next.toString()}`);

      submit.disabled = true;
      count.textContent = "Searching…";
      grid.replaceChildren();
      showStatus("Searching the archive", "Comparing your idea with every indexed line.");
      try {
        const payload = await fetchJson(`/api/search?${next.toString()}`);
        renderResults(payload);
      } catch (error) {
        count.textContent = "Search unavailable";
        showStatus("Archive unavailable", error.message, "error");
      } finally {
        submit.disabled = false;
      }
    };

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      runSearch();
    });

    document.querySelectorAll("[data-query]").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.dataset.query;
        runSearch();
      });
    });

    try {
      await loadChampions();
      if (input.value.trim().length >= 2) await runSearch();
    } catch (error) {
      count.textContent = "Setup required";
      showStatus("Index not ready", error.message, "error");
    }
  };

  const initChampions = async () => {
    const filter = document.getElementById("champion-filter");
    const directory = document.getElementById("champion-directory");
    const count = document.getElementById("champion-count");
    let champions = [];

    const render = () => {
      const needle = filter.value.trim().toLowerCase();
      const visible = champions.filter((item) => item.champion.toLowerCase().includes(needle));
      directory.replaceChildren();
      visible.forEach((item) => {
        const link = create("a", "champion-card");
        link.href = `/?champion=${encodeURIComponent(item.champion)}`;
        link.append(
          create("strong", "", item.champion),
          create("span", "", `${item.spoken_count.toLocaleString()} spoken · ${item.action_count.toLocaleString()} actions`),
        );
        directory.append(link);
      });
      count.textContent = `${visible.length} of ${champions.length} champions`;
    };

    filter.addEventListener("input", render);
    try {
      const payload = await fetchJson("/api/champions");
      champions = payload.champions;
      render();
    } catch (error) {
      count.textContent = error.message;
      count.setAttribute("role", "alert");
    }
  };

  if (page === "explore") initExplore();
  if (page === "champions") initChampions();
})();


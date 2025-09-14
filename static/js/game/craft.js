(function () {
    // ===== State =====
    let ENT_INDEX = 0;
    let STATION = "Станция";
    let recipes = [];
    let filtered = [];
    let selectedId = null;
    let maxCraftsForSelected = 0;

    // ===== DOM =====
    const q = (sel) => document.querySelector(sel);
    const stationTitle = q("#stationTitle");
    const search = q("#search");
    const listContainer = q("#listContainer");
    const listEmpty = q("#listEmpty");
    const qtyRange = q("#qtyRange");
    const qtyVal = q("#qtyVal");
    const qtyHint = q("#qtyHint");
    const btnCraft = q("#btnCraft");

    // ===== Utils =====
    function reqString(pairs) {
        const t = [];
        for (const p of (pairs || [])) {
            const id = String(p[0]);
            const n = String(p[1] || 1);
            t.push(`${id} x${n}`);
        }
        return t.join(", ");
    }

    function recipeDisplayName(r) {
        if (r.displayName) return r.displayName;
        const outs = r.outputs || [];
        if (!outs.length) return r.id || "Рецепт";
        const first = outs[0];
        let base = `${String(first[0])} x${String(first[1] || 1)}`;
        if (outs.length > 1) base = `${base} (и ещё ${outs.length - 1})`;
        return base;
    }

    function renderList() {
        listContainer.innerHTML = "";
        const qStr = (search.value || "").toLowerCase();

        filtered = recipes.filter((r) => {
            if (!qStr) return true;
            const name = (r.displayName || recipeDisplayName(r)).toLowerCase();
            const ins = (r.inputsStr || reqString(r.inputs)).toLowerCase();
            const outs = (r.outputsStr || reqString(r.outputs)).toLowerCase();
            return name.includes(qStr) || ins.includes(qStr) || outs.includes(qStr);
        });

        if (!filtered.length) {
            listEmpty.style.display = "";
            return;
        }
        listEmpty.style.display = "none";

        for (const r of filtered) {
            const div = document.createElement("div");
            div.className = "recipe row";
            if ((r.maxCrafts || 0) <= 0) div.classList.add("unavail");
            if (r.id === selectedId) div.classList.add("selected");

            const title = recipeDisplayName(r);
            const meta = `Время: ${Number(r.time || 0).toFixed(1)} c   •   Доступно: ${Math.max(r.maxCrafts || 0, 0)}`;
            const inputs = `Требуется: ${r.inputsStr || reqString(r.inputs)}`;
            const outputs = `Результат: ${r.outputsStr || reqString(r.outputs)}`;

            div.innerHTML = `
        <div class="recipe-head">
          <div class="title">${escapeHtml(title)}</div>
        </div>
        <div class="meta">${escapeHtml(meta)}</div>
        <div class="line">${escapeHtml(inputs)}</div>
        <div class="line">${escapeHtml(outputs)}</div>
      `;

            div.addEventListener("click", () => selectRecipe(r.id));
            listContainer.appendChild(div);
        }
    }

    function selectRecipe(id) {
        selectedId = id;
        const r = recipes.find(x => x.id === id);
        const maxN = Math.max(r?.maxCrafts || 0, 0);
        maxCraftsForSelected = maxN;
        const realMax = Math.max(1, Math.min(64, maxN));

        if (maxN <= 0) {
            qtyRange.value = "1";
            qtyRange.max = "1";
            qtyVal.textContent = "1";
            qtyHint.textContent = `Доступно: 0`;
            btnCraft.disabled = true;
        } else {
            const cur = clamp(toInt(qtyRange.value, 1), 1, realMax);
            qtyRange.max = String(realMax);
            qtyRange.value = String(cur);
            qtyVal.textContent = String(cur);
            qtyHint.textContent = `Доступно: ${maxN}`;
            btnCraft.disabled = false;
        }

        renderList();
    }

    function onQtyInput() {
        const cur = clamp(toInt(qtyRange.value, 1), 1, toInt(qtyRange.max, 1));
        qtyRange.value = String(cur);
        qtyVal.textContent = String(cur);
    }

    function craft() {
        if (!selectedId) return;
        const count = clamp(toInt(qtyRange.value, 1), 1, 4095);
        try {
            gmod.startCraft(String(ENT_INDEX || 0), String(selectedId), String(count));
        } catch (e) {
            console.error("startCraft failed", e);
        }
    }

    function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
    function toInt(v, d = 0) { const n = parseInt(v, 10); return Number.isFinite(n) ? n : d; }
    function escapeHtml(s) {
        return String(s)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll("\"", "&quot;");
    }

    // ===== Wire with GMod =====
    window.onCraftInit = function (payload) {
        ENT_INDEX = toInt(payload?.entIndex, 0);
        STATION = String(payload?.station || "Станция");
        stationTitle.textContent = STATION;
    };

    window.onCraftList = function (arr) {
        recipes = Array.isArray(arr) ? arr.slice() : [];
        const firstAvail = recipes.find(r => (r.maxCrafts || 0) > 0) || recipes[0] || null;
        selectedId = firstAvail?.id || null;
        renderList();
        if (selectedId) selectRecipe(selectedId);
    };

    window.onCraftError = function (msg) {
        console.error("[CraftError]", msg);
    };

    window.GMOD_READY = function () {
        for (const a of document.querySelectorAll("[data-gmod-link]")) {
            a.addEventListener("click", (e) => {
                e.preventDefault();
                try { gmod.openURL(a.href); } catch (_) { }
            });
        }

        setTimeout(() => search?.focus(), 10);
    };

    // ===== UI events =====
    search.addEventListener("input", renderList);
    qtyRange.addEventListener("input", onQtyInput);
    btnCraft.addEventListener("click", craft);

    // Клавиши: стрелки — выбор, Enter — крафт
    window.addEventListener("keydown", (e) => {
        if (!filtered.length) return;
        if (e.key === "Enter") { craft(); return; }
        const curIdx = filtered.findIndex(r => r.id === selectedId);
        if (e.key === "ArrowDown") {
            const nx = Math.min(filtered.length - 1, (curIdx < 0 ? 0 : curIdx + 1));
            if (filtered[nx]) selectRecipe(filtered[nx].id);
        } else if (e.key === "ArrowUp") {
            const nx = Math.max(0, (curIdx < 0 ? 0 : curIdx - 1));
            if (filtered[nx]) selectRecipe(filtered[nx].id);
        }
    });
})();

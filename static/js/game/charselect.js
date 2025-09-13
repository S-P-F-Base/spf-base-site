// gmod bridge (safe stubs)
const gmod = window.gmod || {
    requestBackstories() { console.log("[stub] requestBackstories"); },
    createCharacter(n, g, b) { console.log("[stub] createCharacter", n, g, b); },
    selectCharacter(id) { console.log("[stub] selectCharacter", id); },
    ensureSpawnicon(m) { console.log("[stub] ensureSpawnicon", m); },
    openURL(u) { console.log("[stub] openURL", u); window.open(u, "_blank"); }
};

/* ================== State ================== */
let state = {
    screen: "list",
    chars: [],
    gender: 0,
    name: "",
    backstoryId: null,
    hasNameGenerator: false,
    genderModels: null,
    backstories: [],
    previewModel: null
};

/* ================== DOM ================== */
const $ = s => document.querySelector(s);
const titleEl = $('#title');
const btnPrimary = $('#btnPrimary');
const listContainer = $('#listContainer'), listEmpty = $('#listEmpty');
const backstoriesEl = $('#backstories'), bsEmpty = $('#bsEmpty');
let nameInput = $('#name'), nameHint = $('#nameHint');
const genderHint = $('#genderHint');
const previewImg = $('#previewImg'), previewHint = $('#previewHint');
const btnCreate = $('#btnCreate');
const btnMale = $('#btnMale'), btnFemale = $('#btnFemale');
const projectLink = $('#projectLink');

/* ================== Utils ================== */
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])); }
function genderName(g) { return g === 0 ? "Мужской" : "Женский"; }
function raceName(r) { return (["Человек", "Полу-человек", "Кукла"][r || 0]) || "?"; }
function spawniconUrl(m) { return "asset://garrysmod/materials/spawnicons/models/" + m.toLowerCase().replace(/^models\//, '').replace(/\.mdl$/, '') + ".png"; }
function normalizeList(list) { return Array.isArray(list) ? list : Object.values(list || {}); }
function setDisabled(el, v) { el.toggleAttribute('disabled', !!v); }

/* spawnicon helpers */
function attachSpawnicon(img, mdl) {
    if (!mdl) { img.removeAttribute('src'); img.parentElement?.classList.add('skeleton'); return; }
    img.parentElement?.classList.remove('skeleton');
    img.dataset.model = mdl;
    img.src = spawniconUrl(mdl);
    img.onerror = () => { try { gmod.ensureSpawnicon(mdl); } catch (e) { } };
}
window.__onSpawniconReady = mdl => {
    const imgs = document.querySelectorAll(`img[data-model="${CSS.escape(mdl)}"]`);
    imgs.forEach(img => img.src = spawniconUrl(mdl) + "?v=" + Date.now());
};

/* ================== Navigation ================== */
function showScreen(name) {
    state.screen = name;
    const isCreate = name === "create";
    $('#screen-list').style.display = isCreate ? "none" : "block";
    $('#screen-create').style.display = isCreate ? "block" : "none";
    titleEl.textContent = isCreate ? "Создание персонажа" : "Выбор персонажа";
    btnPrimary.innerHTML = isCreate
        ? '<span class="btn-icon" aria-hidden="true">☰</span> Выбрать существующего'
        : '<span class="btn-icon" aria-hidden="true">+</span> Создать нового';
    btnPrimary.onclick = isCreate
        ? () => showScreen('list')
        : () => {
            showScreen('create');
            if (!state.backstories.length) { try { gmod.requestBackstories(); } catch (e) { } }
        };
}

/* ================== Validation ================== */
function validateName(name) {
    if (state.hasNameGenerator) return { ok: true, msg: "" };
    const n = (name || "").trim();
    if (n.length < 2) return { ok: false, msg: "Имя слишком короткое" };
    if (n.length > 32) return { ok: false, msg: "Слишком длинное имя" };
    return { ok: true, msg: "" };
}
function refreshCreateButton() {
    const valid = state.backstoryId && (state.hasNameGenerator || validateName(state.name).ok);
    setDisabled(btnCreate, !valid);
}

/* ================== Preview ================== */
function updatePreview(mdl) {
    state.previewModel = mdl || null;
    attachSpawnicon(previewImg, state.previewModel);
    previewHint.textContent = mdl ? "" : "Выбери предысторию — появится иконка модели";
}

/* ================== Rendering ================== */
function renderChars(chars) {
    state.chars = normalizeList(chars);
    listContainer.innerHTML = '';
    listEmpty.style.display = state.chars.length ? 'none' : 'block';

    state.chars.forEach(c => {
        const card = document.createElement('div'); card.className = 'card';
        const thumb = document.createElement('div'); thumb.className = 'thumb';
        const img = document.createElement('img'); img.alt = ''; attachSpawnicon(img, c.model || ''); thumb.appendChild(img);

        const info = document.createElement('div');
        info.innerHTML = `
      <div class="title">${escapeHtml(c.name || "Без имени")}</div>
      <div class="meta">Пол: ${genderName(c.gender)} · Раса: ${raceName(c.race)}</div>
    `;

        const right = document.createElement('div'); right.className = 'right';
        const pick = document.createElement('button'); pick.className = 'btn btn-primary'; pick.textContent = 'Выбрать';
        pick.onclick = () => gmod.selectCharacter(String(c.id || 0));
        right.appendChild(pick);

        card.append(thumb, info, right);
        listContainer.appendChild(card);
    });
}

function renderBackstories(list) {
    state.backstories = normalizeList(list);
    backstoriesEl.innerHTML = '';
    bsEmpty.style.display = state.backstories.length ? 'none' : 'block';

    state.backstories.forEach(bs => {
        const chosen = state.backstoryId === bs.id;
        const row = document.createElement('div'); row.className = 'row' + (chosen ? ' selected' : '');
        row.innerHTML = `
      <div class="row-head">
        <div>
          <div class="title">${escapeHtml(bs.title || bs.id || "?")}</div>
          <div class="small">${escapeHtml(bs.description || "")}</div>
        </div>
        <button class="btn ${chosen ? 'btn-primary' : 'btn-ghost'}">${chosen ? 'Выбрано' : 'Выбрать'}</button>
      </div>
    `;
        const btn = row.querySelector('button');
        btn.onclick = () => {
            state.backstoryId = bs.id;
            state.hasNameGenerator = !!bs.has_name_generator;
            state.genderModels = bs.gender_models || null;

            // toggle name field
            $('#nameField').style.display = state.hasNameGenerator ? 'none' : 'block';
            if (!state.hasNameGenerator) { nameHint.textContent = ""; }

            // preview
            const mdl = (state.genderModels && (state.genderModels[state.gender] ?? state.genderModels[0])) || null;
            updatePreview(mdl);

            // re-render to flip selected visual
            renderBackstories(state.backstories);
            refreshCreateButton();
        };
        backstoriesEl.appendChild(row);
    });
}

/* ================== Events ================== */
/* gender buttons */
function setGender(g) {
    state.gender = g;
    genderHint.textContent = g === 0 ? "Мужской" : "Женский";
    btnMale.classList.toggle('is-active', g === 0);
    btnFemale.classList.toggle('is-active', g === 1);
    const mdl = (state.genderModels && (state.genderModels[g] ?? state.genderModels[0])) || null;
    updatePreview(mdl);
}
btnMale.onclick = () => { setGender(0); refreshCreateButton(); };
btnFemale.onclick = () => { setGender(1); refreshCreateButton(); };

/* name input */
if (nameInput) {
    nameInput.oninput = () => {
        state.name = nameInput.value;
        const v = validateName(state.name);
        nameHint.textContent = v.msg;
        refreshCreateButton();
    };
}

/* create */
btnCreate.onclick = () => {
    if (!state.backstoryId) { alert("Выбери предысторию"); return; }
    if (!state.hasNameGenerator) {
        const v = validateName(state.name);
        if (!v.ok) { nameHint.textContent = v.msg; return; }
    }
    const finalName = state.hasNameGenerator ? "" : (state.name || "");
    gmod.createCharacter(finalName, String(state.gender), state.backstoryId);
};

/* header primary */
btnPrimary.onclick = () => {
    // initial binding; showScreen will rebind as needed
    showScreen('create');
    if (!state.backstories.length) { try { gmod.requestBackstories(); } catch (e) { } }
};

/* footer link — guaranteed open via gmod */
if (projectLink) {
    projectLink.addEventListener('click', (e) => {
        e.preventDefault();
        try { gmod.openURL('https://spf-base.ru'); }
        catch (_) { window.open('https://spf-base.ru', '_blank'); }
    });
}

/* shortcuts */
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && state.screen === 'create') { showScreen('list'); }
    if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'n') && state.screen !== 'create') {
        e.preventDefault(); showScreen('create');
    }
});

/* ================== Lua entrypoints ================== */
window.onCharacterList = (chars) => {
    try { renderChars(chars); } catch (e) { (gmod.log || console.log)(e); }
};
window.onBackstories = (list) => {
    try {
        renderBackstories(list);
        refreshCreateButton();
    } catch (e) { (gmod.log || console.log)(e); }
};
window.onCharError = (msg) => alert(msg || "Error");
window.GMOD_READY = () => { try { gmod.requestBackstories(); } catch (e) { } };

/* ================== Init ================== */
showScreen('list');
setGender(0);
refreshCreateButton();

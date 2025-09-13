const gmod = window.gmod || {
    requestBackstories() { console.log("[stub] requestBackstories"); },
    createCharacter(n, g, b) { console.log("[stub] createCharacter", n, g, b); },
    selectCharacter(id) { console.log("[stub] selectCharacter", id); },
    ensureSpawnicon(m) { console.log("[stub] ensureSpawnicon", m); }
};

/* ---- state ---- */
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

/* ---- dom ---- */
const $ = s => document.querySelector(s);
const titleEl = $('#title');
const btnPrimary = $('#btnPrimary');
const listContainer = $('#listContainer'), listEmpty = $('#listEmpty');
const backstoriesEl = $('#backstories'), bsEmpty = $('#bsEmpty');
let nameInput = $('#name'), nameHint = $('#nameHint');
const genderHint = $('#genderHint');
const previewImg = $('#previewImg'), previewHint = $('#previewHint');
const nameFieldId = 'nameField';
const createLeft = document.querySelector('.create-left');
const btnCreate = $('#btnCreate');

/* ---- utils ---- */
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])); }
function genderName(g) { return g === 0 ? "Мужской" : "Женский"; }
function raceName(r) { return (["Человек", "Полу-человек", "Кукла"][r || 0]) || "?"; }
function spawniconUrl(m) { return "asset://garrysmod/materials/spawnicons/models/" + m.toLowerCase().replace(/^models\//, '').replace(/\.mdl$/, '') + ".png"; }
function normalizeList(list) { return Array.isArray(list) ? list : Object.values(list || {}); }

/* ---- spawnicon helpers ---- */
function attachSpawnicon(img, mdl) {
    if (!mdl) { img.removeAttribute('src'); return; }
    img.dataset.model = mdl;
    img.src = spawniconUrl(mdl);
    img.onerror = () => { try { gmod.ensureSpawnicon(mdl); } catch (e) { } };
}
window.__onSpawniconReady = mdl => {
    const imgs = document.querySelectorAll(`img[data-model="${CSS.escape(mdl)}"]`);
    imgs.forEach(img => img.src = spawniconUrl(mdl) + "?v=" + Date.now());
};

/* ---- screen switch + header button ---- */
function showScreen(n) {
    state.screen = n;
    const isCreate = n === "create";
    $('#screen-list').style.display = isCreate ? "none" : "block";
    $('#screen-create').style.display = isCreate ? "block" : "none";
    titleEl.textContent = isCreate ? "Создание персонажа" : "Выбор персонажа";
    btnPrimary.textContent = isCreate ? "Выбрать существующего" : "Создать нового";
    btnPrimary.onclick = isCreate
        ? () => showScreen('list')
        : () => {
            showScreen('create');
            if (!state.backstories.length) { try { gmod.requestBackstories(); } catch (e) { } }
        };
}

/* ---- dynamic name field ---- */
function ensureNameFieldVisible(visible) {
    const existing = document.getElementById(nameFieldId);
    if (visible) {
        if (!existing) {
            const nf = document.createElement('div');
            nf.className = 'field';
            nf.id = nameFieldId;
            nf.innerHTML = `
        <label>Имя персонажа</label>
        <input id="name" placeholder="Введите имя"/>
        <div class="small" id="nameHint"></div>`;
            createLeft.insertBefore(nf, btnCreate);
            nameInput = $('#name'); nameHint = $('#nameHint');
            nameInput.value = state.name || "";
            nameInput.oninput = () => state.name = nameInput.value;
        }
    } else if (existing) {
        existing.remove();
        nameInput = null; nameHint = null;
    }
}

/* ---- preview ---- */
function updatePreview(mdl) {
    state.previewModel = mdl || null;
    attachSpawnicon(previewImg, state.previewModel);
    previewHint.textContent = mdl ? "" : "Выбери предысторию — появится иконка модели";
}

/* ---- renderers ---- */
function renderChars(chars) {
    state.chars = normalizeList(chars);
    listContainer.innerHTML = '';
    listEmpty.style.display = state.chars.length ? 'none' : 'block';
    state.chars.forEach(c => {
        const card = document.createElement('div'); card.className = 'card';
        const thumb = document.createElement('div'); thumb.className = 'thumb';
        const img = document.createElement('img'); img.alt = ''; attachSpawnicon(img, c.model || ''); thumb.appendChild(img);
        const info = document.createElement('div');
        info.innerHTML = `<div class="title">${escapeHtml(c.name || "Без имени")}</div>
                    <div class="meta">Пол: ${genderName(c.gender)} · Раса: ${raceName(c.race)}</div>`;
        const actions = document.createElement('div'); actions.className = 'actions';
        const pick = document.createElement('button'); pick.className = 'btn'; pick.textContent = 'Выбрать';
        pick.onclick = () => gmod.selectCharacter(String(c.id || 0));
        actions.appendChild(pick);
        card.append(thumb, info, actions); listContainer.appendChild(card);
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
        <button class="btn">${chosen ? 'Выбрано' : 'Выбрать'}</button>
      </div>`;
        const btn = row.querySelector('button');
        btn.onclick = () => {
            state.backstoryId = bs.id;
            state.hasNameGenerator = !!bs.has_name_generator;
            state.genderModels = bs.gender_models || null;
            ensureNameFieldVisible(!state.hasNameGenerator);
            if (nameHint) nameHint.textContent = "";
            const mdl = (state.genderModels && (state.genderModels[state.gender] || state.genderModels[0])) || null;
            updatePreview(mdl);
            renderBackstories(state.backstories);
        };
        backstoriesEl.appendChild(row);
    });
}

/* ---- lua entrypoints ---- */
window.onCharacterList = chars => { try { renderChars(chars); } catch (e) { (gmod.log || console.log)(e); } };
window.onBackstories = list => { try { renderBackstories(list); } catch (e) { (gmod.log || console.log)(e); } };
window.onCharError = msg => alert(msg || "Ошибка");
window.GMOD_READY = () => { try { gmod.requestBackstories(); } catch (e) { } };

/* ---- UI events ---- */
document.getElementById('btnMale').onclick = () => {
    state.gender = 0; genderHint.textContent = "Мужской";
    const mdl = (state.genderModels && (state.genderModels[0] || state.genderModels[0])) || null; updatePreview(mdl);
};
document.getElementById('btnFemale').onclick = () => {
    state.gender = 1; genderHint.textContent = "Женский";
    const mdl = (state.genderModels && (state.genderModels[1] || state.genderModels[0])) || null; updatePreview(mdl);
};
if (nameInput) { nameInput.oninput = () => state.name = nameInput.value; }
document.getElementById('btnCreate').onclick = () => {
    if (!state.backstoryId) { alert("Выбери предысторию"); return; }
    const finalName = state.hasNameGenerator ? "" : (state.name || "");
    gmod.createCharacter(finalName, String(state.gender), state.backstoryId);
};

/* ---- init ---- */
showScreen('list');
(function () {
    // ===== State =====
    const S = {
        mode: "self",
        targetName: "",
        containerEnt: 0,
        frisk: false,
        friskActionDelay: 0,
        friskForceExtra: 0,

        hasAdmin: null,

        invLoad: 0, invMaxLoad: 0,
        myInvLoad: 0, myInvMaxLoad: 0,

        progress: {},

        inv: { items: [] },
        myInv: { items: [] },
        container: { items: [] },

        players: [],
        allItems: []
    };

    // ===== DOM =====
    const root = sel("#root");
    const tabSelf = sel("#tabSelf");
    const tabAdmin = sel("#tabAdmin");
    const tabs = sel("#tabs");

    // ===== Utils =====
    function sel(s) { return document.querySelector(s); }
    function el(tag, cls, text) {
        const n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text != null) n.textContent = text;
        return n;
    }
    const fmtKg = (x) => {
        x = Number(x) || 0;
        return Math.abs(x - Math.floor(x)) < 0.001 ? String(Math.floor(x)) : x.toFixed(1);
    };
    const fmtSecLeft = (endT) => {
        const left = Math.max(0, Number(endT || 0) - (performance.timeOrigin / 1000 + performance.now() / 1000));
        if (left >= 10) return `${Math.ceil(left)}s`;
        return `${left.toFixed(1)}s`;
    };

    const RU_LOWER = Object.fromEntries("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ".split("").map((c, i) => [c, "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"[i]]));
    function casefold(s = "") {
        let out = "";
        for (const ch of String(s)) out += RU_LOWER[ch] || ch.toLowerCase();
        return out;
    }
    function matches(it, q) {
        if (!q) return true;
        const cf = casefold(q);
        const n = casefold(it.name || "");
        const id = casefold(it.id || "");
        return n.includes(cf) || id.includes(cf);
    }

    function weightOf(it) { return Number(it.w || 1) * Number(it.count || 1); }

    function button(txt, fn) {
        const b = el("button", "action", txt);
        b.type = "button";
        b.addEventListener("click", fn);
        return b;
    }

    function setTabsActive(key) {
        for (const b of tabs.querySelectorAll(".btn")) b.classList.remove("is-active");
        if (key === "adminPanel") tabAdmin.classList.add("is-active"); else tabSelf.classList.add("is-active");
    }

    // ===== Renders =====

    function render() {
        root.innerHTML = "";
        if (S.mode === "container") return renderContainer();
        if (S.mode === "frisk") return renderFrisk();
        if (S.mode === "admin") return renderAdmin();
        return renderSelf();
    }

    function renderSelf() {
        setTabsActive("self");
        const wrap = el("div", "cols-2");

        // LEFT — экипировка
        const left = el("div", "");
        left.append(equipBlock("Экипировка", S.inv.items, { readonly: false, force: false }));
        // RIGHT — инвентарь
        const right = el("div", "");
        right.append(invBlock("Твой инвентарь", S.inv.items, {
            loadLine: loadLine(S.invLoad, S.invMaxLoad),
            allowEquip: true, allowUse: true, allowStack: true, allowDrop: true,
            progress: S.progress
        }));

        wrap.append(left, right);
        root.append(wrap);
    }

    function renderContainer() {
        setTabsActive("self");
        const wrap = el("div", "cols-3");

        const left = el("div", "");
        left.append(equipBlock("Экипировка", S.inv.items, { readonly: false, force: false }));

        const mid = el("div", "");
        mid.append(invBlock("Твой инвентарь", S.inv.items, {
            loadLine: loadLine(S.invLoad, S.invMaxLoad),
            allowEquip: true, allowUse: true, allowStack: true, allowDrop: true,
            progress: S.progress,
            toContainer: S.containerEnt
        }));

        const right = el("div", "");
        right.append(listBlock(
            headerSearch("Контейнер", null),
            S.container.items,
            (it) => ({
                title: itemTitle(it),
                sub: "",
                right: fmtKg(weightOf(it)) + " кг",
                actions: [
                    ["Забрать x1", () => action("move_from_container", { ent: S.containerEnt, uid: it.uid, n: 1 })],
                    ["Забрать всё", () => action("move_from_container", { ent: S.containerEnt, uid: it.uid, n: it.count || 1 })],
                    ["Забрать N…", () => promptN("Сколько забрать?", (n) => action("move_from_container", { ent: S.containerEnt, uid: it.uid, n }))],
                ]
            }),
            (it) => action("move_from_container", { ent: S.containerEnt, uid: it.uid, n: 1 })
        ));

        wrap.append(left, mid, right);
        root.append(wrap);
    }

    function renderFrisk() {
        setTabsActive("self");
        const wrap = el("div", "cols-3");

        const left = el("div", "");
        left.append(equipBlock(`Экипировка цели: ${S.targetName || ""}`, S.inv.items, { readonly: false, force: true }));

        const mid = el("div", "");
        mid.append(invBlock("Инвентарь цели", S.inv.items, {
            loadLine: loadLine(S.invLoad, S.invMaxLoad),
            allowEquip: true, allowUse: true, allowStack: true,
            progress: S.progress,
            frisk: true
        }));

        const right = el("div", "");
        right.append(listBlock(
            headerSearch(`Твой инвентарь → ${S.targetName || ""}`, loadLine(S.myInvLoad, S.myInvMaxLoad)),
            S.myInv.items,
            (it) => ({
                title: itemTitle(it),
                sub: "",
                right: fmtKg(weightOf(it)) + " кг",
                actions: [
                    ["Передать x1", () => action("frisk_give", { uid: it.uid, n: 1 })],
                    ["Передать всё", () => action("frisk_give", { uid: it.uid, n: it.count || 1 })],
                    ["Передать N…", () => promptN("Сколько передать?", (n) => action("frisk_give", { uid: it.uid, n }))],
                ]
            }),
            (it) => action("frisk_give", { uid: it.uid, n: 1 })
        ));

        wrap.append(left, mid, right);
        root.append(wrap);
    }

    function renderAdmin() {
        setTabsActive("adminPanel");
        const wrap = el("div", "cols-2");

        const left = el("div", "");
        left.append(el("div", "side-title", "Экипировка игрока"));
        left.append(equipBlock("", S.inv.items, { readonly: true, force: false }));

        const right = el("div", "");
        right.append(invBlock(`Инвентарь: ${S.targetName || ""}`, S.inv.items, {
            loadLine: loadLine(S.invLoad, S.invMaxLoad),
            allowEquip: false, allowUse: false, allowStack: false, allowDrop: false,
            progress: {}
        }));

        root.append(wrap);
    }

    // ===== Компоненты =====

    function loadLine(load, max) {
        const d = el("div", "load-line", "");
        if ((Number(max) || 0) > 0) d.textContent = `Нагрузка: ${fmtKg(load)} / ${fmtKg(max)} кг`;
        else d.textContent = `Нагрузка: ${fmtKg(load)} кг`;
        return d;
    }

    function headerSearch(title, rightNode) {
        const head = el("div", "sticky-head", "");
        const bar = el("div", "header-row", "");
        bar.append(el("div", "title", title));
        if (rightNode) bar.append(rightNode);
        head.append(bar);

        const inp = el("input", "search");
        inp.placeholder = "Поиск... (имя/ID)";
        head.append(inp);
        return { node: head, input: inp };
    }

    function listBlock(header, items, mapToRow, onDouble) {
        const wrap = el("div", "panel", "");
        let headerInfo;

        if (header && header.node && header.input) {
            headerInfo = header;
        } else {
            headerInfo = headerSearch(String(header || ""), null);
        }

        const { node, input } = headerInfo;
        wrap.append(node);

        const list = el("div", "list");
        wrap.append(list);

        function rebuild() {
            list.innerHTML = "";
            const q = input.value || "";
            const arr = items
                .filter(it => !it.equipped && matches(it, q))
                .slice()
                .sort((a, b) => {
                    const na = casefold(a.name), nb = casefold(b.name);
                    if (na !== nb) return na < nb ? -1 : 1;
                    return String(a.uid).localeCompare(String(b.uid));
                });

            if (!arr.length) { list.append(el("div", "empty", "Пусто")); return; }

            for (const it of arr) {
                const conf = mapToRow(it);
                const row = el("div", "row", "");
                const head = el("div", "row-head", "");
                head.append(el("div", "title", conf.title || ""), el("div", "weight", conf.right || ""));
                row.append(head);
                if (conf.sub) row.append(el("div", "sub", conf.sub));
                const actions = el("div", "actions", "");
                for (const [txt, fn] of (conf.actions || [])) actions.append(button(txt, fn));
                if (actions.children.length) row.append(actions);
                if (onDouble) row.addEventListener("dblclick", () => onDouble(it));
                list.append(row);
            }
        }

        input.addEventListener("input", rebuild);
        rebuild();
        return wrap;
    }

    function equipBlock(title, items, opts) {
        const wrap = el("div", "panel", "");
        wrap.append(el("div", "side-title", title || "Экипировка"));
        const list = el("div", "list");
        wrap.append(list);

        const eq = [];
        for (const it of items) if (it.equipped) eq.push(it);
        eq.sort((a, b) => {
            const na = casefold(a.name), nb = casefold(b.name);
            if (na !== nb) return na < nb ? -1 : 1;
            return String(a.uid).localeCompare(String(b.uid));
        });

        if (!eq.length) {
            list.append(el("div", "row", "Ничего не надето"));
            return wrap;
        }

        for (const it of eq) {
            const slots = Array.isArray(it.equipped) ? it.equipped.slice()
                : typeof it.equipped === "string" && it.equipped !== "" ? [it.equipped] : ["?"];
            for (const s of slots) {
                const row = el("div", "row", "");
                const head = el("div", "row-head", "");
                head.append(el("div", "title", `[${s}] ${it.name}`));
                row.append(head);

                const actions = el("div", "actions", "");
                if (!opts.readonly) {
                    if (opts.force) {
                        const extra = S.friskForceExtra > 0 ? ` (+${Math.floor(S.friskForceExtra)}с)` : "";
                        actions.append(button("Снять (принуд.)" + extra, () => action("frisk_force_unequip", { uid: it.uid })));
                    } else {
                        actions.append(button("Снять", () => action("unequip", { uid: it.uid })));
                    }
                    row.append(actions);
                    row.addEventListener("dblclick", () => {
                        if (opts.force) action("frisk_force_unequip", { uid: it.uid });
                        else action("unequip", { uid: it.uid });
                    });
                }
                list.append(row);
            }
        }

        return wrap;
    }

    function invBlock(title, items, opts) {
        const headRight = el("div", "kv", "");
        if (opts.loadLine) headRight.append(opts.loadLine);
        const hdr = headerSearch(title, headRight);

        return listBlock(hdr, items, (it) => {
            const pr = S.progress && S.progress[it.uid];
            let subtitle = "";
            let disabled = false;

            if (opts.progress && pr && pr.kind === "equip") {
                subtitle = `Экипировка: ${fmtSecLeft(pr.endT)}`;
                disabled = true;
            }
            const acts = [];

            if (!disabled) {
                if (opts.toContainer) {
                    acts.push(["→ Контейнер x1", () => action("move_to_container", { ent: opts.toContainer, uid: it.uid, n: 1 })]);
                    acts.push(["→ Контейнер всё", () => action("move_to_container", { ent: opts.toContainer, uid: it.uid, n: it.count || 1 })]);
                    acts.push(["→ Контейнер N…", () => promptN("Сколько переложить?", (n) => action("move_to_container", { ent: opts.toContainer, uid: it.uid, n }))]);
                } else if (opts.frisk) {
                    acts.push(["Надеть (силой)", () => action("frisk_force_equip", { uid: it.uid })]);
                    acts.push(["Использовать", () => action("frisk_use", { uid: it.uid })]);
                    acts.push(["Изъять x1", () => action("frisk_steal", { uid: it.uid, n: 1 })]);
                    acts.push(["Изъять всё", () => action("frisk_steal", { uid: it.uid, n: it.count || 1 })]);
                    acts.push(["Изъять N…", () => promptN("Сколько изъять?", (n) => action("frisk_steal", { uid: it.uid, n }))]);
                } else {
                    if (opts.allowEquip) acts.push(["Экипировать", () => action("equip", { uid: it.uid })]);
                    if (opts.allowUse) acts.push(["Использовать", () => action("use", { uid: it.uid })]);
                    if (opts.allowStack) acts.push(["Объединить", () => action("stack_compact", { uid: it.uid })]);
                    if (opts.allowDrop) {
                        acts.push(["Выбросить x1", () => action("drop", { uid: it.uid, n: 1 })]);
                        acts.push(["Выбросить всё", () => action("drop", { uid: it.uid, n: it.count || 1 })]);
                        acts.push(["Выбросить N…", () => promptN("Сколько выбросить?", (n) => action("drop", { uid: it.uid, n }))]);
                    }
                }
            }

            return {
                title: itemTitle(it),
                sub: subtitle,
                right: fmtKg(weightOf(it)) + " кг",
                actions: acts
            };
        }, (it) => {
            if (opts.toContainer) action("move_to_container", { ent: opts.toContainer, uid: it.uid, n: 1 });
            else if (opts.frisk) action("frisk_steal", { uid: it.uid, n: 1 });
            else if (opts.allowEquip) action("equip", { uid: it.uid });
            else if (opts.allowUse) action("use", { uid: it.uid });
        });
    }

    function itemTitle(it) {
        const cnt = Number(it.count || 1);
        return cnt > 1 ? `${it.name} x${cnt}` : it.name;
    }

    function promptN(title, cb) {
        const n = prompt(title || "Сколько?", "1");
        const v = parseInt(n || "1", 10);
        if (Number.isFinite(v) && v > 0) cb(v);
    }

    // ===== Actions =====
    function action(op, data) {
        try { gmod.invAction(String(op || ""), JSON.stringify(data || {})); }
        catch (e) { console.error("invAction failed", e); }
    }

    // ===== Tabs =====
    tabSelf.addEventListener("click", () => {
        setTabsActive("self");
        render();
    });

    tabAdmin.addEventListener("click", () => {
        setTabsActive("adminPanel");
        invShowAdminPanel();
    });

    // ===== Admin panel =====
    function invShowAdminPanel() {
        if (S.hasAdmin === false) return;
        root.innerHTML = "";
        const wrap = el("div", "cols-2");

        // LEFT — игроки
        const left = el("div", "");
        const head = headerSearch("Игроки (двойной клик — открыть)", null);
        left.append(head.node);
        const list = el("div", "players");
        left.append(list);

        function rebuild() {
            list.innerHTML = "";
            const q = head.input.value || "";
            const arr = (S.players || []).filter(p => {
                const nm = casefold(p.name || "");
                const sid = casefold(p.steamid || "");
                const cf = casefold(q);
                return !q || nm.includes(cf) || sid.includes(cf);
            }).sort((a, b) => casefold(a.name).localeCompare(casefold(b.name)));
            if (!arr.length) { list.append(el("div", "empty", "Пусто")); return; }

            for (const p of arr) {
                const row = el("div", "row", "");
                const rh = el("div", "row-head", "");
                rh.append(el("div", "title", p.name || ""), el("div", "sub", p.alive ? "alive" : "dead"));
                row.append(rh);
                row.append(el("div", "sub", (p.steamid || "") + ` · ent:${p.ent}`));

                const actions = el("div", "actions", "");
                actions.append(button("Открыть (RO)", () => gmod.invOpen(String(2), String(p.ent))));
                actions.append(button("Выбрать", () => { S._selectedEnt = p.ent; rebuild(); }));
                row.append(actions);

                if (S._selectedEnt === p.ent) row.classList.add("row", "selected");
                row.addEventListener("dblclick", () => gmod.invOpen(String(2), String(p.ent)));
                list.append(row);
            }
        }
        head.input.addEventListener("input", rebuild);
        rebuild();

        const refresh = el("button", "btn", "Обновить список");
        refresh.type = "button";
        refresh.addEventListener("click", () => { try { gmod.requestPlayers(); } catch (_) { } });
        const refreshWrap = el("div", "");
        refreshWrap.appendChild(refresh);
        left.append(refreshWrap);

        // RIGHT — спавн предметов
        const right = el("div", "");
        const panel = el("div", "panel", "");
        panel.append(el("div", "title", "Спавн предметов"));
        const r1 = el("div", "row head", "");
        const idInput = el("input", "");
        idInput.placeholder = "Предмет: начни вводить или выбери справа";
        idInput.autocomplete = "off";
        r1.append(idInput);
        panel.append(r1);

        const r2 = el("div", "row head", "");
        const cntInput = el("input", "");
        cntInput.type = "number"; cntInput.value = "1"; cntInput.min = "1";
        cntInput.style.width = "120px";
        r2.append(el("div", "muted", "Количество:"), cntInput);
        panel.append(r2);

        const r3 = el("div", "row head", "");
        const dstSel = el("select", "");
        for (const [v, txt] of [["self", "Себе"], ["player", "Выбранный игрок"], ["container", "Контейнер под прицелом"], ["world", "В мир перед собой"]]) {
            const o = el("option", "", txt); o.value = v; dstSel.append(o);
        }
        r3.append(el("div", "muted", "Куда:"), dstSel);
        panel.append(r3);

        const spawn = el("button", "btn btn-primary", "Спавн");
        spawn.addEventListener("click", () => {
            const count = parseInt(cntInput.value || "1", 10) || 1;
            let ref = 0;
            const dst = dstSel.value;
            if (dst === "player") ref = Number(S._selectedEnt || 0) || 0;
            if (dst === "player" && ref === 0) { alert("Выбери игрока слева"); return; }
            gmod.invAdmin("spawn_item", JSON.stringify({ id: idInput.value.trim(), count, dst, ref }));
        });
        panel.append(spawn);
        right.append(panel);

        // Каталог предметов
        const catWrap = el("div", "panel", "");
        const catHead = headerSearch("Каталог предметов", null);
        catWrap.append(catHead.node);
        const catList = el("div", "catalog");
        catWrap.append(catList);

        function rebuildCatalog() {
            catList.innerHTML = "";
            const q = catHead.input.value || "";
            const cf = casefold(q);
            const arr = (S.allItems || []).filter(r => {
                return !q || casefold(r.name || "").includes(cf) || casefold(r.id || "").includes(cf);
            }).sort((a, b) => {
                const na = casefold(a.name || a.id), nb = casefold(b.name || b.id);
                if (na !== nb) return na < nb ? -1 : 1;
                return casefold(a.id).localeCompare(casefold(b.id));
            });
            if (!arr.length) { catList.append(el("div", "empty", "Пусто")); return; }

            for (const rec of arr) {
                const row = el("div", "row", "");
                row.append(el("div", "title", rec.name || rec.id));
                row.append(el("div", "cat-row-id", `ID: ${rec.id}${rec.weight != null ? ` · ${fmtKg(rec.weight)} кг` : ""}`));
                const actions = el("div", "actions", "");
                actions.append(button("Выбрать", () => { idInput.value = rec.id; }));
                actions.append(button("Спавн x1", () => gmod.invAdmin("spawn_item", JSON.stringify({ id: rec.id, count: 1, dst: "self", ref: 0 }))));
                row.append(actions);
                row.addEventListener("dblclick", () => { idInput.value = rec.id; spawn.click(); });
                catList.append(row);
            }
        }
        catHead.input.addEventListener("input", rebuildCatalog);

        const mid = el("div", "");
        wrap.append(left, mid);
        mid.append(panel, catWrap);
        root.append(wrap);

        try { gmod.requestPlayers(); } catch (_) { }
        if (!S.allItems || !S.allItems.length) { try { gmod.requestItemsCatalog(); } catch (_) { } }
        rebuildCatalog();
    }
    window.invShowAdminPanel = invShowAdminPanel;

    // ===== Bridge in =====
    window.onInvState = function (vm) {
        Object.assign(S, {
            mode: vm.mode || S.mode,
            targetName: vm.targetName || "",
            containerEnt: vm.containerEnt || 0,
            frisk: !!vm.frisk,
            friskActionDelay: Number(vm.friskActionDelay || 0),
            friskForceExtra: Number(vm.friskForceExtra || 0),

            hasAdmin: vm.hasAdmin === undefined ? S.hasAdmin : vm.hasAdmin,

            invLoad: Number(vm.invLoad || 0),
            invMaxLoad: Number(vm.invMaxLoad || 0),
            myInvLoad: Number(vm.myInvLoad || 0),
            myInvMaxLoad: Number(vm.myInvMaxLoad || 0),

            progress: vm.progress || {},
            inv: vm.inv || { items: [] },
            myInv: vm.myInv || { items: [] },
            container: vm.container || { items: [] }
        });

        if (S.hasAdmin === true) tabAdmin.style.display = "";
        else if (S.hasAdmin === false) tabAdmin.style.display = "none";

        render();
    };

    window.onInvAdmin = function (msg) {
        if (!msg || !msg.kind) return;
        if (msg.kind === "players") {
            S.players = msg.players || [];
            if (tabAdmin.classList.contains("is-active")) invShowAdminPanel();
        } else if (msg.kind === "spawn_result") {
            console.log("[INV] spawn_result:", msg.ok);
        } else if (msg.kind === "admin_perm") {
            S.hasAdmin = !!msg.ok;
            tabAdmin.style.display = S.hasAdmin ? "" : "none";
        } else if (msg.kind === "items_catalog") {
            S.allItems = msg.items || [];
            if (tabAdmin.classList.contains("is-active")) invShowAdminPanel();
        }
    };

    // ===== GMOD Ready =====
    window.GMOD_READY = function () {
        for (const a of document.querySelectorAll("[data-gmod-link]")) {
            a.addEventListener("click", (e) => { e.preventDefault(); try { gmod.openURL(a.href); } catch (_) { } });
        }
        try { gmod.checkAdminPerm(); } catch (_) { }
    };

})();

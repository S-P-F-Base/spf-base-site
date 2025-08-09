"use strict";

let isGmod = false;
let isTest = false;
let totalFiles = 0;
let totalCalled = false;
let downloadingFileCalled = false;
let percentage = 0;
let allowIncrement = true;

function setLoad(percent) {
    percentage = Math.min(Math.round(percent), 100);

    const bar = document.getElementById("progress-bar-fill");
    const text = document.getElementById("progress-bar-text");

    if (bar) bar.style.width = `${percentage}%`;
    if (text) text.textContent = `Загрузка: ${percentage}%`;
}

function addToHistory(text) {
    const historyEl = document.getElementById("history");
    const item = document.createElement("div");

    item.className = "history-item";
    item.textContent = text;

    historyEl.prepend(item);

    const items = historyEl.querySelectorAll(".history-item");
    items.forEach((el, i) => {
        el.style.opacity = `${1 - i * 0.1}`;
        if (i > 9) el.remove();
    });
}

function GameDetails(servername, serverurl, mapname, maxplayers, steamid, gamemode) {
    isGmod = true;
    const mapEl = document.getElementById("mapname");
    if (mapEl) mapEl.textContent = mapname;
}

function SetFilesTotal(total) {
    totalFiles = total;
    totalCalled = true;

    const el = document.getElementById("total-files");
    if (el) el.textContent = `Всего файлов: ${total}`;
}

function SetFilesNeeded(needed) {
    const el = document.getElementById("needed-files");
    if (el) el.textContent = `Осталось: ${needed}`;

    if (totalCalled && totalFiles > 0) {
        const p = 100 - Math.round((needed / totalFiles) * 100);
        setLoad(p);
    }
}

function DownloadingFile(filename) {
    filename = filename.replace(/['"?]/g, "");
    downloadingFileCalled = true;
    addToHistory(`Файл: ${filename}`);
}

function SetStatusChanged(status) {
    addToHistory(`Статус: ${status}`);

    switch (status) {
        case "Workshop Complete":
            allowIncrement = false;
            setLoad(80);
            break;

        case "Client info sent!":
            allowIncrement = false;
            setLoad(95);
            break;

        case "Starting Lua...":
            setLoad(100);
            break;

        default:
            if (allowIncrement) {
                setLoad(percentage + 0.1);
            }
    }
}

window.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => {
        if (!isGmod) {
            isTest = true;

            GameDetails("SPF Base", "", "rp_downtown", 64, "76561198000000000", "militaryrp");
            SetFilesTotal(25);

            let needed = 25;

            const interval = setInterval(() => {
                if (needed > 0) {
                    needed -= 1;
                    SetFilesNeeded(needed);
                    DownloadingFile(`materials/example_${needed}.vtf`);
                } else {
                    clearInterval(interval);
                    SetStatusChanged("Starting Lua...");
                }
            }, 300);

            SetStatusChanged("Connecting...");
        }
    }, 1000);
});

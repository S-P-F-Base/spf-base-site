Title: Как создать страницу вики
Author: Cain
Date: 2025-07-10

# Как создать страницу вики

[TOC]

---

## Структура папок
Все `.md`-файлы вики находятся в папке `wiki` в корне проекта. Допустимы вложенные подпапки - структура может выглядеть так:

```
/wiki
├── main.md
├── how_to_create_wiki.md
├── example.md
└── inventory/
    └── weapons.md
```

Для ссылок внутри вики используется `WikiLink`: Путь указывается относительно папки `wiki`, без расширения `.md`

Пример:
```
[[/wiki/inventory/weapons|Оружие]]
```

---

## Структура файла
Каждая страница начинается с трёх специальных строк - мета-заголовков. Они помогают системе понять, что это за страница и кто её сделал.
Вот эти строки:

```
Title: Название страницы
Author: Cain
Date: 2025-07-10
```

Что это значит:
- Title - это заголовок страницы. Он будет отображаться вверху страницы и в списках. Например, если написать `Title: Главная`, то на странице будет большой заголовок "Главная".
- Author - это автор страницы. Если создаёшь новую страницу, ставьте своё имя. Если обновляете уже существующую, добавляй сюда своё имя, чтобы было видно, кто последний редактировал. 
- Date - дата последнего обновления страницы. Она помогает понять, когда в последний раз меняли содержимое. Формат - Год-Месяц-День, например, `2025-07-10`.

---

### Блоки кода
Используй тройные кавычки (\`\`\`) для выделения кода:

```
print("Hello, world!")
```

---

### Таблицы
Markdown поддерживает таблицы, пример:

```
| Имя     | Класс       | Ранг |
|:--------|------------:|:----:|
| M4A1    | AR Team     | A    |
| UMP45   | 404 Squad   | B    |
```

Важно: не вставляй текст сразу после или перед таблицы без пустой строки - может поломаться отображение.

---

### Картинки
Все изображения, используемые на страницах вики, должны находиться в папке
`/static/wiki/images` или её подпапках.

Формат вставки изображения:
```
![Описание](/static/wiki/images/название.jpg "Подсказка при наведении")
```

Примеры:
```
![Мандаринка](/static/wiki/images/hehe.jpg "Мандаринка")
![Портрет](/static/wiki/images/characters/ump45.png "UMP45")
```

Важно: путь должен начинаться с `/static/wiki/images`, чтобы картинка корректно отображалась.
Так же картинку обязательно закидывать в этот же путь. Можно использовать подпапки

---

### WikiLink
Ссылки на другие страницы делаются через двойные квадратные скобки:
`[[/wiki/main|Главная]]` - ссылка на `wiki/main.md` с названием "Главная"
`[[/wiki/inventory/weapons]]` - ссылка на `wiki/inventory/weapons.md`, текст будет "weapons"

---

## Пример страницы
Смотри файл [`example.md`](example.md), чтобы увидеть всё в действии.

---

## Как проверить, что страница работает
Запустить код через F5 через vscode

Открыть вики в браузере
Зайди в браузере на сайт: `http://localhost:8000/`

Перейди по ссылке на новую страницу
Если добавил ссылку вроде:
```
[[/wiki/inventory/weapons|Оружие]]
```

То её можно будет найти по адрессу `http://localhost:8000/wiki/inventory/weapons`
Однако файл обязан быть
```
/wiki
├── ...
└── inventory/
    └── weapons.md
```

---

---

# Что нужно скачать и как

Необходимо скачать следующее:
- [Git](https://git-scm.com/downloads)
- [Python 3.12](https://www.python.org/downloads/release/python-3123/) - смотрите в самом низу
- [VSCode](https://code.visualstudio.com/)

Далее необходимо зайти на [гитхаб сайта](https://github.com/S-P-F-Base/spf-base-site) и сделать форк

![make fork 1](/static/wiki/images/how_to_create_wiki/make_fork_1.png "make fork 1")
![make fork 2](/static/wiki/images/how_to_create_wiki/make_fork_2.png "make fork 2")

Нажимаете на create fork
![make fork 3](/static/wiki/images/how_to_create_wiki/make_fork_3.png "make fork 3")
Ждёте пару минут

---

Далее вам необходимо скопировать репозиторий локально
Копируете ссылку на ваш репозиторий
К примеру `https://github.com/themanyfaceddemon/spf-base-site`

открываете `cmd`
вводите следующие команды
```
git clone https://github.com/ВАШ_НИК/spf-base-site.git
cd spf-base-site
python3 -m venv .venv

# Если windows
(
echo YOOMONEY_ACCOUNT=
echo YOOMONEY_NOTIFICATION=
echo BOT_TOKEN=
echo JWT_KEY=
) > .env
.venv\Scripts\activate

# Если linux
echo -e "YOOMONEY_ACCOUNT=\nYOOMONEY_NOTIFICATION=\nBOT_TOKEN=\nJWT_KEY=" > .env
source .venv/bin/activate

# Далее для всех
pip install -r requirements.txt
```

После чего можете спокойно открывать vscode и работать над репозиторием


ОСТАЛЬНОЕ КАК СОЗДАВАТЬ ПУЛ РЕКВЕСТ МОЖНО ПОСМОТРЕТЬ [ТУТ](https://bestprogrammer.ru/programmirovanie-i-razrabotka/kak-sdelat-pulrekvest-na-github-poshagovoe-rukovodstvo-dlya-nachinayushix)
Да. Мне лень писать. Что вы мне сделаете?

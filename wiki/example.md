<!-- Блок meta -->
Title: Пример страницы                   <!-- Название которое будет отображатья. Обязательно указывать -->
Author: Cain                             <!-- Кто сделал данную страницу. Не используется, но указывать обязательно -->
Date: 2025-07-17                         <!-- Последняя дата изменения. Обязательно указывать -->
Background: /static/wiki/images/hehe.jpg <!-- Смена заднего изображения. Не обязательно указывать. Если не указать будет использоваться "/static/images/wallpaper.jpeg"-->

# Добро пожаловать
Это пример страницы для **вики**. Ниже - демонстрация подключённых расширений.

!!! red "ВНИМАНИЕ"
    Все `.md` файлы динамически подгружаются. Так что сервер для этого постоянно перезапускать не нужно

---

[TOC]

---

## Таблицы
Просто по умолчанию

| Имя     | Класс       | Ранг |
|---------|-------------|------|
| M4A1    | AR Team     | A    |
| UMP45   | 404 Squad   | B    |
| G11     | Experimental| S    |


Немного по другому центруем

| Имя     | Класс       | Ранг |
|:--------|------------:|:----:|
| M4A1    | AR Team     | A    |
| UMP45   | 404 Squad   | B    |
| G11     | Experimental| S    |

НЕ ВСТАВЛЯТЬ ТЕКСТ ВПРИТЫК К ТАБЛИЦЕ, ИНАЧЕ ТАБЛИЦА СКОНЧАЕТСЯ

Немного по другому центруем

| Имя                                      | Класс        | Ранг |
|:-----------------------------------------|-------------:|:----:|
| !tblimg[/static/wiki/images/hehe.jpg|30] | AR Team      | A    |
| UMP45                                    | 404 Squad    | B    |
| G11                                      | Experimental | S    |

| Имя   | Класс                                          | Ранг |
|:------|-----------------------------------------------:|:----:|
| M4A1  | AR Team                                        | A    |
| UMP45 | !tblimg[/static/wiki/images/hehe.jpg|30]       | B    |
| G11   | Experimental                                   | S    |


| Имя   | Класс        | Ранг                                     |
|:------|-------------:|:----------------------------------------:|
| M4A1  | AR Team      | A                                        |
| UMP45 | 404 Squad    | B                                        |
| G11   | Experimental | !tblimg[/static/wiki/images/hehe.jpg|10] |


---

## WikiLink
Можно сослаться так [[/wiki|Глав. стр]].

---

## Блок кода
```
Тут мог быть ваш хуй
Хуй длиииииииииииииииииииииииииииииииииный чтобы показать что блоки кода имеют встроенный wrap чтобы не делать скрол влево или в право
```

---

## Блоки цветные

!!! orange
    Цвет

!!! red
    Цвет

!!! green "Цветной с кастомным заголовком"
    Цвет

!!! blue ""
    Цветной без заголовка

---

## Сноски

Вот текст со сноской.[^1]

[^1]: Текст сноски.

---

## Разделилители

`---`

---

В упор так же нельзься писать

---

## Картиночка порнушная

!imgblock[/static/wiki/images/hehe.jpg|left|70]
Данный текст показывает что я ненавижу как css, так и ебучий html. Мне пришлось долго ебаться чтобы блядский длинный текст помещался в пределы блядской страницы
!endimgblock

!imgblock[/static/wiki/images/hehe.jpg|right|10]
Аналогичная хуйня
!endimgblock

!imgblock[/static/wiki/images/hehe.jpg|middle|20]
Аналогичная хуйня но по центру
!endimgblock

Есть ещё сокращённое написание как макросс

!img[/static/wiki/images/hehe.jpg]

!!! blue ""
    По умолчанию для `left`, `right` и `middle` идёт 40%. Просьба учитывать что значения могут быть в разбросе от 10 до 100.
    Ставить 100 только если уверены что делаете. Или у вас `middle` ¯\\\_(ツ)\_/¯

!!! red "Внимание!"
    НЕ ПИШИТЕ ДЛИННЫЙ ТЕКСТ В `!imgblock[]`!
    Он сделает хуйню некрасивую, в виде того что текст уйдёт колонкой вниз

---

## Кнопочка

!btn[https://youtu.be/E4WlUXrJgy4?si=5kLpaTltJ7F2-Eqh|OwO]

---

## Константы
Для чего вообще константы? Для того чтобы инфу которая может легко поменяться вынести отдельно и менять централизованно, чтобы не ебаться и не искать по всей вики где же вы умудрились вписать ссылку на старый дискорд или ещё подобное.

Константа просто как текст - !const[discord_link]

Константа в кнопке к примеру
!btn[!const[discord_link]|Тык]

Константы можно экранировать через `\` если необходимо: `\!const[discord_link]`

---

## Блядушная замена номер раз

Ковычки на "типографические"


## Фолдеры

Есть нативная поддержка автоматического создания фолдеров
!folder[
    /root/kill_all.py
    /example.md
    /wiki/ten_codes.md
]

Или если всё под одним рутом
!folder[
    /god/root/kill_all.py
    /god/example.md
    /god/wiki/ten_codes.md
]

## Мелкий текст
Текст маленький очень
-# Да. Очень

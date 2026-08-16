# Парсер открытого банка ФИПИ

`fipi_scraper.py` — скрипт на **Playwright** (настоящий headless-браузер
Chromium) + BeautifulSoup, который должен скачивать задания с
`ege.fipi.ru/bank/` и сохранять их в JSON, готовый для
`python manage.py import_fipi`.

Playwright используется вместо обычного `requests`, потому что сайт,
похоже, отличает программные HTTP-запросы от настоящего браузера (защита
от ботов по TLS/JS-отпечатку) и не отвечает на них — при этом в обычном
браузере страница открывается нормально. Headless Chromium сайт не
отличает от обычного посетителя.

**Статус: черновик, требует донастройки под реальную разметку сайта.**
Подробности и пошаговая инструкция — в docstring в начале
`fipi_scraper.py`. Коротко: сайт был недоступен из среды, где писался
скрипт, поэтому селекторы (`parse_task_list`, `parse_task_detail`) — это
предположение по структуре, а не проверенный код. Запустите с
`--debug-dump`, посмотрите на сохранённый HTML в `fipi_dump/` и поправьте
селекторы (или пришлите HTML для правки).

## Быстрый старт (Windows: используйте `py` вместо `python`, если `python`
## у вас указывает на заглушку Microsoft Store)

```bash
pip install -r requirements.txt
playwright install chromium   # скачивает сам браузер, ~150-300 МБ, один раз

# 1. Откройте https://ege.fipi.ru/bank/, выберите предмет, скопируйте proj из URL
# 2. Запустите с отладочным дампом на 1 странице
python fipi_scraper.py --proj <GUID> --subject rus --out tasks_rus.json --max-pages 1 --debug-dump

# Если хотите своими глазами увидеть, что происходит в браузере — добавьте --show-browser

# 3. Если задания не нашлись — откройте fipi_dump/list_page_1.html,
#    найдите в нём блок одного задания и поправьте parse_task_list()/
#    parse_task_detail() по месту (или пришлите файл для правки)

# 4. Когда парсер заработает — загрузите результат в базу
cd .. && python manage.py import_fipi scripts/tasks_rus.json --subject rus
```

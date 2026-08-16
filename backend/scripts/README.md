# Парсер открытого банка ФИПИ

`fipi_scraper.py` — скрипт на requests + BeautifulSoup, который должен
скачивать задания с `ege.fipi.ru/bank/` и сохранять их в JSON, готовый для
`python manage.py import_fipi`.

**Статус: черновик, требует донастройки под реальную разметку сайта.**
Подробности и пошаговая инструкция — в docstring в начале
`fipi_scraper.py`. Коротко: сайт был недоступен из среды, где писался
скрипт, поэтому селекторы (`parse_task_list`, `parse_task_detail`) — это
предположение по структуре, а не проверенный код. Запустите с
`--debug-dump`, посмотрите на сохранённый HTML в `fipi_dump/` и поправьте
селекторы (или пришлите HTML для правки).

## Быстрый старт

```bash
pip install -r requirements.txt

# 1. Откройте https://ege.fipi.ru/bank/, выберите предмет, скопируйте proj из URL
# 2. Запустите с отладочным дампом на 1-2 страницах
python fipi_scraper.py --proj <GUID> --subject rus --out tasks_rus.json --max-pages 1 --debug-dump

# 3. Если задания не нашлись — откройте fipi_dump/list_page_1.html,
#    найдите в нём блок одного задания и поправьте parse_task_list()/
#    parse_task_detail() по месту (или пришлите файл для правки)

# 4. Когда парсер заработает — загрузите результат в базу
cd .. && python manage.py import_fipi scripts/tasks_rus.json --subject rus
```

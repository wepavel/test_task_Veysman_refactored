# Файловое хранилище

---

## Установка

___

###  docker-compose.yml

```yaml
services:
  backend:
    container_name: '${DOCKER_IMAGE_BACKEND}'
    image: '${DOCKER_IMAGE_BACKEND}:${TAG-latest}'
    environment:
      - BASE_STORAGE_DIR=/file_storage
      - HOST=0.0.0.0
      - PORT=8023
      - DOCKER_IMAGE_BACKEND=test_backend
      - PROJECT_NAME="Test Task Veysman Refactored"
      - PROJECT_DESK="New refactored version of test task"
    volumes:
      - .:/src/
      - /etc/localtime:/etc/localtime:ro
      - ./file_storage:/file_storage
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/healthcheck/healthcheck"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

  db:
    container_name: test_db
    image: postgres:17-bookworm
    volumes:
      - pgdata:/var/lib/postgresql/data/pgdata
      - /etc/localtime:/etc/localtime:ro
    environment:
      - PGDATA=/var/lib/postgresql/data/pgdata
      - POSTGRES_USER=postgres
      - POSTGRES_DB=postgres
      - POSTGRES_PASSWORD=postgres
    restart: always
    healthcheck:
      test: [ "CMD-SHELL", "sh -c 'pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}'" ]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  pgdata:
```
Параметры базы были прописаны в `docker-compose.yml`, при необходимости их можно задать через .env файл


###  docker-compose.override.yml

```yaml
services:
  backend:

    environment:
      - TERM=`xterm-256color`
    ports:
      - "${HOST}:${PORT}:8001"
    build:
      context: ./
      args:
        INSTALL_DEV: ${INSTALL_DEV-true}
    depends_on:
      - db
    tty: true
    command: ["/src/root/start-reload.sh"]

  db:
    expose:
      - 5432
    ports:
      - "5434:5432"
```



1. `chmode +x ./root/start-reload.sh`
2. `docker compose up -d`

### Пояснение к акхитектуре

Приложение представляет из себя файловое хранилище, имеющее публичный API для взаимодействия.

### config.yaml

```yaml
pg:
  host: test_db
  port: 5432
  user: postgres
  password: postgres
  database: postgres_123

timezone: 'Europe/Moscow'
```

### Переменные окружения (опциональные)

- YAML_PATH=/config.yaml
- HOST=0.0.0.0
- PORT=8023
- DOCKER_IMAGE_BACKEND=test_backend
- PROJECT_NAME="Test Task Veysman Refactored"
- PROJECT_DESK="New refactored version of test task"

## API

---


### Загрузка файла
**Описание:** Позволяет загрузить файл в файловое хранилище по указанному пути.

`POST /api/file-manager/upload-file/{file_dest_dir}`

**Запрос** `multipart/form-data`
- **Path-параметр**
  - `file_dest_dir` — относительный путь к папке внутри файлового хранилища, например: `images/profile`. 
- **Form-data:**

| Поле       | Тип  | Описание          |
|------------|------|-------------------|
| input_file | файл | Файл для загрузки |


**Ответ** `application/json` `200 OK`

```json5
{
  // Имя файла
  "name": "README",
  // Расширение файла
  "extension": ".md",
  // Относительный путь файла внутри файловой системы
  "path": "",
  // Размер файла
  "size": 12439,
  // Дата добавления файла в хранилище
  "created_at": "2025-06-30T16:13:47.120937+03:00",
  // Дата последнего изменения файла
  "updated_at": "2025-06-30T16:13:47.120940+03:00",
  // Комментарий к файлу
  "comment": ""
}
```

**Ошибки**:

- `4416` - указанный путь ведёт за пределы базовой директории хранилища;
- `4082` - файл с таким именем уже существует;
- `4083` - ошибка при загрузке файла в хранилище;
- `500` - прочие ошибки.


### Изменение файла
**Описание:** Позволяет произвести изменение разрешённых параметров файла в хранилище.

`PATCH /api/file-manager/update-file/{old_file_path}`

**Запрос** `application/json`
- **Path-параметр**
  - `old_file_path` — относительный путь к файлу внутри файлового хранилища, например `images/img.png`. Для указания корневой папки нужно использовать ".", "/" или "./"
- **JSON тело запроса (`FileUpdate`):**

```json5
{
  "name": "new_name",
  "new_dir_path": "images/updated",
  "comment": "Новое описание изображения"
}
```
Каждое из полей является опциональным для того, чтобы каждый из этих параметров можно было изменить отдельно.

**Ответ** `application/json` `200 OK`

Аналогичен ответу при загрузке файла в хранилище

**Ошибки**:

- `4416` - указанный путь ведёт за пределы базовой директории хранилища;
- `4081` - файла с таким именем не существует;
- `4082` - ошибка с таким именем уже существует;
- `4086` - ошибка при перемещении файла;
- `500` - прочие ошибки.


### Получение файла
**Описание:** Позволяет выполнить загрузку существующего файла из хранилища.

`GET /api/file-manager/download-file/{file_path}`

**Запрос** `application/json`
- **Path-параметр**
  - `file_path` — относительный путь к файлу внутри файлового хранилища, например `images/img.png`

**Ответ** `application/octet-stream` `200 OK`

Файл сохраняется клиентом под оригинальным именем.


**Ошибки**:

- `4416` - указанный путь ведёт за пределы базовой директории хранилища;
- `4081` - файла с таким именем не существует;
- `4085` - ошибка при загрузке файла;
- `500` - прочие ошибки.


### Удаление файла

`DELETE /api/file-manager/remove-file/{file_path}`

**Запрос** `application/json`
- **Path-параметр**
  - `file_path` — относительный путь к файлу внутри файлового хранилища, например `images/img.png`


**Ответ** `application/json` `200 OK`

Аналогичен ответу при загрузке файла в хранилище

**Ошибки**:

- `4416` - указанный путь ведёт за пределы базовой директории хранилища;
- `4081` - файла с таким именем не существует;
- `500` - прочие ошибки.


### Получение сведений о файле
**Описание:** Возвращает сведения о файле, путь к которому был указан в запросе.

`GET /api/file-info/get-file-info/{file_path}`

**Запрос** `application/json`
- **Path-параметр**
  - `file_path` — относительный путь к файлу внутри файлового хранилища, например `images/img.png`

**Ответ** `application/json` `200 OK`

Аналогичен ответу при загрузке файла в хранилище

**Ошибки**:

- `4416` - указанный путь ведёт за пределы базовой директории хранилища;
- `4081` - файла с таким именем не существует;
- `500` - прочие ошибки.


### Получение сведений о файлах, лежащих в заданной папке
**Описание:** Возвращает сведения о файлах, которые лежат в папке, указанной в запросе.

`GET /api/file-info/list-dir/{dir_path}`

**Запрос** `application/json`
- **Path-параметр**
  - `file_dest_dir` — относительный путь к папке внутри файлового хранилища, например: `images/profile`. Для указания корневой папки нужно использовать ".", "/" или "./"

**Ответ** `application/json` `200 OK`

```json5
[
  {
    // Имя файла
    "name": "README",
    // Расширение файла
    "extension": ".md",
    // Относительный путь файла внутри файловой системы
    "path": "",
    // Размер файла
    "size": 12439,
    // Дата добавления файла в хранилище
    "created_at": "2025-06-30T16:13:47.120937+03:00",
    // Дата последнего изменения файла
    "updated_at": "2025-06-30T16:13:47.120940+03:00",
    // Комментарий к файлу
    "comment": ""
  }
]
```

**Ошибки**:

- `4416` - указанный путь ведёт за пределы базовой директории хранилища;
- `500` - прочие ошибки.

### Получение сведений обо всех файлах в файловой системе
**Описание:** Возвращает список всех файлов, хранящихся в базе данных, с постраничной пагинацией. 

`GET /api/file-info/get-all-files-info`

**Запрос** `application/json`
- **Path-параметр**
  - `skip` — Количество файлов, которые нужно пропустить `(offset)`
  - `limit` — Максимальное количество файлов в ответе

**Ответ** `application/json` `200 OK`

Аналогичен ответу при запросе сведений о файлах, лежащих в заданной папке

- `500` - прочие ошибки.
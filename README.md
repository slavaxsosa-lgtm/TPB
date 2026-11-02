# Бот управления выплатами репетиторов

Telegram бот для автоматизации управления выплатами репетиторов. Интегрируется с Google Sheets для хранения данных о занятиях, выплатах и тикетах.

## Требования

- Python 3.10 и выше
- Google Sheets API доступ (Service Account)
- Токен Telegram бота (от @BotFather)
- Интернет соединение
- Для деплоя на сервер: SSH доступ, PM2 или systemd

## Возможности

### Для репетиторов (статус 5)
- `/balance` - Проверить баланс и историю занятий
- `/payment_link` - Создать заявку на ссылку для оплаты
- `/ticket` - Создать тикет на выплату с указанием суммы
- `/confirm_payout` - Подтвердить получение выплаты
- `/cancel_ticket <ID>` - Отменить свой тикет
- `/history` - Посмотреть историю всех тикетов и заявок

### Для администраторов ссылок (статус 2)
- Все команды репетитора
- `/requests` - Список активных заявок на ссылки
- `/reply <ID> <ссылка>` - Отправить ссылку для оплаты репетитору
- Уведомления о новых заявках

### Для старших администраторов (статус 3)
- Все команды администратора ссылок
- `/tickets` - Список активных тикетов на выплату
- `/status` - Статус выплат всех пользователей
- `/approve <ID>` - Одобрить тикет на выплату
- `/reject <ID> <причина>` - Отклонить тикет
- `/open_payout` - Открыть форму для подтверждения выплат
- `/close_payout` - Закрыть форму и получить статистику
- `/notify_update` - Отправить уведомление об обновлении данных в группы

## Установка и локальный запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/tutor_payment_bot.git
cd tutor_payment_bot
```

### 2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Получение Telegram токена

1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания нового бота
4. Скопируйте полученный токен (выглядит как `123456789:ABCdefGHIjklmnoPQRstuvWXYZ1234567890`)

### 5. Настройка Google Sheets API

#### Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект (нажмите на выпадающий список проектов вверху)
3. Введите название проекта (например, "Tutor Payment Bot")

#### Шаг 2: Включение Google Sheets API

1. В левом меню нажмите на "API и сервисы" → "Библиотека"
2. Найдите "Google Sheets API"
3. Нажмите на нее и кликните "ВКЛЮЧИТЬ"

#### Шаг 3: Создание Service Account

1. В левом меню нажмите "API и сервисы" → "Учетные данные"
2. В верхней части нажмите "+ Создать учетные данные" → "Аккаунт сервиса"
3. Введите имя (например, "tutor-payment-bot")
4. Нажмите "Создать и продолжить"
5. На следующем экране нажмите "Создать ключ"
6. Выберите тип "JSON"
7. Нажмите "Создать"
8. Файл `tutor-platform-xxx-xxx.json` скачается автоматически

#### Шаг 4: Настройка файла учетных данных

1. Переименуйте скачанный JSON файл в `credentials.json`
2. Поместите его в корневую папку проекта

```bash
mv ~/Downloads/tutor-platform-*.json ./credentials.json
```

#### Шаг 5: Создание Google Sheet

1. Перейдите на [Google Sheets](https://sheets.google.com)
2. Создайте новую таблицу
3. Переименуйте ее в "Tutor Payment Bot"
4. Скопируйте ID из URL (часть после `/d/`)

Пример URL: `https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit`

ID: `YOUR_SPREADSHEET_ID`

#### Шаг 6: Предоставление доступа боту

1. Откройте свою Google Sheets таблицу
2. Нажмите "Поделиться"
3. Возьмите email из файла `credentials.json` (поле `client_email`)
4. Поделитесь таблицей с этим email
5. Дайте права "Редактор"

### 6. Создание структуры Google Sheet

Ваша таблица должна иметь 4 листа:

#### Лист "current_day" (данные по занятиям)
Столбцы A-M:
- A: Telegram юзернейм (@username)
- B: Полное имя
- C: Дата занятия
- D: Chat ID (ID урока)
- E: Сумма
- F: Статус

#### Лист "week" (сводка по неделе)
Столбцы A-E:
- A: Telegram юзернейм
- B: Полное имя
- C: Сумма за неделю
- D: Сумма в кармане
- E: Итого

#### Лист "admins" (администраторы)
Столбцы A-D:
- A: Telegram юзернейм (@testuser)
- B: Полное имя (Ivan Ivanov)
- C: Статус (5 = репетитор, 2 = админ ссылок, 3 = старший админ)
- D: TG_ID (Telegram ID пользователя)

Пример:
```
@testuser    | Test User    | 5 | 123456789
@testadmin   | Admin        | 2 | 987654321
@testowner   | Senior Admin | 3 | 111222333
```

#### Лист "tickets" (тикеты, создается автоматически)
Столбцы A-J:
- A: ID тикета
- B: TG_ID пользователя
- C: Telegram юзернейм
- D: Тип тикета (payment_link, payout_request, confirmation)
- E: Данные (JSON)
- F: Статус (ожидание, одобрено, отклонено)
- G: Ответственный админ
- H: Дата закрытия
- I: Комментарий
- J: Дата создания

### 7. Настройка файла .env

```bash
cp .env.example .env
```

Отредактируйте `.env` файл:

```env
# Токен бота от @BotFather
BOT_TOKEN=your_bot_token_here

# ID вашей Google Sheets таблицы
SPREADSHEET_ID=your_spreadsheet_id_here

# Список администраторов (Telegram ID через запятую) - опционально
ADMIN_IDS=123456789,987654321

# Список групп для рассылки (с минусом для приватных групп) - опционально
GROUP_IDS=-1001234567890
```

### 8. Локальный тест

Запустите бота в режиме тестирования:

```bash
python -m bot.main
```

Должны увидеть:
```
[timestamp] [INFO] [__main__] Bot starting...
[timestamp] [INFO] [__main__] Connected to Mock Sheets (for testing)
[timestamp] [INFO] [__main__] Bot started and ready
```

## Тестирование

### Использование Mock режима

По умолчанию бот использует `MockSheetsManager` для тестирования без реальных Google Sheets.

Тестовые пользователи:
- `@testuser` (статус 5 - репетитор)
- `@testadmin` (статус 2 - админ ссылок)
- `@testowner` (статус 3 - старший админ)

### Переключение на реальные Google Sheets

Для работы с реальными Google Sheets отредактируйте `bot/main.py`:

```python
# Измените эту строку:
from bot.mock_sheets import MockSheetsManager as SheetsManager

# На эту:
from bot.sheets import SheetsManager
```

## Архитектура проекта

```
bot/
├── main.py                # Точка входа, инициализация диспетчера
├── config.py              # Загрузка переменных окружения из .env
├── filters.py             # Фильтры для проверки ролей пользователей
├── keyboards.py           # Клавиатуры Telegram
├── states.py              # FSM состояния для диалогов
├── scheduler.py           # Планировщик рассылок уведомлений
├── sheets.py              # Интеграция с Google Sheets API
├── mock_sheets.py         # Mock база данных для тестирования
├── handlers/              # Обработчики команд
│   ├── common.py          # Общие команды (/start, /help)
│   ├── tutor.py           # Команды репетиторов
│   ├── admin.py           # Команды администраторов
│   ├── admin_lists.py     # Команды списков (заявки, тикеты)
│   └── buttons.py         # Обработчики нажатий на кнопки
└── utils/                 # Утилиты
    ├── validators.py      # Валидация входных данных
    ├── notifications.py   # Отправка уведомлений
    └── message_manager.py # Управление сообщениями для удаления
```

## Развертывание на сервер

### Способ 1: Через systemd (рекомендуется для Ubuntu/Debian)

#### 1. Подготовка сервера

```bash
ssh user@your_server_ip

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y python3.10 python3-pip python3-venv git

# Создание директории проекта
mkdir -p ~/projects
cd ~/projects

# Клонирование репозитория
git clone https://github.com/yourusername/tutor_payment_bot.git
cd tutor_payment_bot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

#### 2. Загрузка учетных данных и конфигурации

```bash
# Загрузите файлы на сервер через scp или используйте Git LFS
scp credentials.json user@your_server_ip:~/projects/tutor_payment_bot/
scp .env user@your_server_ip:~/projects/tutor_payment_bot/

# Или отредактируйте .env на сервере
nano .env
```

#### 3. Создание systemd сервиса

```bash
sudo nano /etc/systemd/system/tutor-payment-bot.service
```

Содержимое файла:

```ini
[Unit]
Description=Tutor Payment Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/projects/tutor_payment_bot
Environment="PATH=/home/ubuntu/projects/tutor_payment_bot/venv/bin"
ExecStart=/home/ubuntu/projects/tutor_payment_bot/venv/bin/python -m bot.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 4. Запуск сервиса

```bash
# Перезагрузка конфигурации systemd
sudo systemctl daemon-reload

# Включение сервиса при загрузке
sudo systemctl enable tutor-payment-bot

# Запуск сервиса
sudo systemctl start tutor-payment-bot

# Проверка статуса
sudo systemctl status tutor-payment-bot

# Просмотр логов
sudo journalctl -u tutor-payment-bot -f
```

### Способ 2: Через PM2 (Node.js like)

```bash
# Установка PM2
sudo npm install -g pm2

# Запуск бота
pm2 start --name tutor-bot --interpreter python3 bot/main.py

# Сохранение конфигурации
pm2 save

# Включение при загрузке
pm2 startup
```

### Проверка работы после деплоя

```bash
# Проверить логи
sudo journalctl -u tutor-payment-bot -n 50

# Перезагрузить бота (если необходимо)
sudo systemctl restart tutor-payment-bot

# Остановить бота
sudo systemctl stop tutor-payment-bot
```

## Обновление бота на сервере

```bash
ssh user@your_server_ip
cd ~/projects/tutor_payment_bot

# Остановить бота
sudo systemctl stop tutor-payment-bot

# Обновить код
git pull origin main

# Обновить зависимости (если добавили новые)
source venv/bin/activate
pip install -r requirements.txt

# Запустить бота
sudo systemctl start tutor-payment-bot

# Проверить статус
sudo systemctl status tutor-payment-bot
```

## Типы тикетов

- `payment_link` - Заявка на ссылку для оплаты от репетитора
- `payout_request` - Заявка на корректировку выплаты
- `confirmation` - Подтверждение получения выплаты

## Коды статусов пользователей

- `5` - Репетитор
- `2` - Администратор ссылок
- `3` - Старший администратор

## Коды статусов тикетов

- `ожидание` - Тикет создан, ожидает рассмотрения
- `одобрено` - Одобрено администратором
- `отклонено` - Отклонено администратором

## Переменные окружения

| Переменная | Обязательная | Описание |
|------------|-------------|---------|
| `BOT_TOKEN` | ✅ Да | Токен Telegram бота от @BotFather |
| `SPREADSHEET_ID` | ✅ Да | ID вашей Google Sheets таблицы |
| `ADMIN_IDS` | ❌ Нет | Список TG ID администраторов через запятую |
| `GROUP_IDS` | ❌ Нет | Список ID групп для рассылки через запятую |

## Логирование

Логи по умолчанию сохраняются в `logs/bot.log`

Для просмотра логов на сервере:

```bash
# Последние 50 строк
tail -50 logs/bot.log

# Отслеживание в реальном времени
tail -f logs/bot.log

# Поиск ошибок
grep ERROR logs/bot.log
```

## Решение проблем

### Бот не отвечает на команды

1. Проверьте токен в `.env`
2. Убедитесь, что у вас есть username в Telegram (Настройки → Username)
3. Проверьте статус в Google Sheets (должны быть в листе "admins")
4. Посмотрите логи: `sudo journalctl -u tutor-payment-bot -n 50`

### Ошибка "Вы не зарегистрированы в системе"

1. Откройте Google Sheets таблицу
2. Перейдите на лист "admins"
3. Добавьте строку:
   - A: @yourusername
   - B: Your Full Name
   - C: 5 (или нужный статус)
   - D: Your TG ID (узнать можно отправив `/id` боту @userinfobot)

### Google Sheets доступ запрещен (403)

1. Откройте `credentials.json` и найдите `client_email`
2. Откройте вашу Google Sheets таблицу
3. Нажмите "Поделиться"
4. Добавьте email с правами "Редактор"

### Проблемы с Python на сервере

```bash
# Убедитесь, что используется правильная версия Python
python3 --version  # Должна быть 3.10+

# Проверьте виртуальное окружение
source venv/bin/activate
python -m bot.main
```

## Лицензия

MIT - смотрите файл LICENSE для подробностей

## Автор

TG: @slava_sosa

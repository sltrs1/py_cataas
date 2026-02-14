import os
import json
import requests
from urllib.parse import quote
from datetime import datetime

# --- Конфигурация ---
FOLDER_NAME = "PY-140"  # Название папки на Яндекс.Диске
JSON_FILENAME = "files_info.json"  # Имя выходного JSON-файла
LOCAL_IMAGE_FILENAME = "temp_cat_image.jpg"  # Временное имя для локального сохранения
CATAAS_API_URL = "https://cataas.com/cat/says/{}"  # Шаблон URL для API
YANDEX_API_URL = "https://cloud-api.yandex.net/v1/disk/resources"


# -------------------

def main():
    # 1. Запрос данных у пользователя
    user_text = input("Введите текст для картинки: ").strip()
    if not user_text:
        print("Ошибка: Текст не может быть пустым.")
        return

    token_file = open('token.txt', 'r')
    yandex_token = token_file.read().strip()
    if not yandex_token:
        print("Ошибка: Токен не может быть пустым.")
        return

    print(f"\nПолучаем картинку с текстом: '{user_text}'...")

    try:
        # 2. Запрос картинки с cataas.com
        encoded_text = quote(user_text)
        api_url = CATAAS_API_URL.format(encoded_text)

        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # Проверка на ошибки HTTP

        # 3. Сохраняем картинку локально
        with open(LOCAL_IMAGE_FILENAME, 'wb') as f:
            f.write(response.content)

        # Получаем размер файла
        file_size = os.path.getsize(LOCAL_IMAGE_FILENAME)
        print(f"Картинка получена. Размер: {file_size} байт")

        # 4. Создаем папку на Яндекс.Диске, если её нет
        headers = {
            'Authorization': f'OAuth {yandex_token}',
            'Content-Type': 'application/json'
        }

        # Проверяем существование папки
        params = {'path': FOLDER_NAME}
        folder_check = requests.get(f"{YANDEX_API_URL}", headers=headers, params=params)

        if folder_check.status_code == 404:  # Папка не найдена
            print(f"Папка '{FOLDER_NAME}' не найдена. Создаём...")
            create_response = requests.put(f"{YANDEX_API_URL}", headers=headers, params=params)
            if create_response.status_code != 201:
                print(f"Ошибка создания папки: {create_response.status_code}")
                os.remove(LOCAL_IMAGE_FILENAME)
                return
            print("Папка создана успешно.")
        elif folder_check.status_code != 200:
            print(f"Ошибка проверки папки: {folder_check.status_code}")
            os.remove(LOCAL_IMAGE_FILENAME)
            return

        # 5. Загружаем файл на Яндекс.Диск
        remote_path = f"{FOLDER_NAME}/{user_text}.jpg"

        # Получаем URL для загрузки
        params = {'path': remote_path, 'overwrite': 'true'}
        upload_link_response = requests.get(f"{YANDEX_API_URL}/upload", headers=headers, params=params)
        upload_link_response.raise_for_status()
        href = upload_link_response.json().get('href')

        if not href:
            print("Ошибка: Не удалось получить ссылку для загрузки")
            os.remove(LOCAL_IMAGE_FILENAME)
            return

        # Загружаем файл
        with open(LOCAL_IMAGE_FILENAME, 'rb') as f:
            upload_response = requests.put(href, files={'file': f})
            upload_response.raise_for_status()

        print(f"Файл '{user_text}.jpg' успешно загружен на Яндекс.Диск")

        # 6. Сохраняем информацию в JSON-файл
        file_info = {
            'filename': f"{user_text}.jpg",
            'text': user_text,
            'size_bytes': file_size,
            'upload_date': datetime.now().isoformat(),
            'remote_path': f"disk:/{remote_path}"
        }

        with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(file_info, f, ensure_ascii=False, indent=2)

        print(f"Информация сохранена в файл '{JSON_FILENAME}'")

        # 7. Удаляем временный файл
        os.remove(LOCAL_IMAGE_FILENAME)
        print("Временный файл удален.")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
    except IOError as e:
        print(f"Ошибка при работе с файлом: {e}")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")


if __name__ == "__main__":
    main()
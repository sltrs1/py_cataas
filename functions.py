import os
import json
import requests

from config import *
from urllib.parse import quote
from datetime import datetime


def get_user_text():
    """
        Запрашивает у пользователя текст для изображения и выполняет его валидацию.

        Функция считывает ввод из стандартного потока (input),
        удаляет начальные и конечные пробелы и проверяет,
        что строка не пустая.

        Returns:
            str: Валидный непустой текст, введённый пользователем.

        Raises:
            ValueError: Если пользователь ввёл пустую строку.
    """
    user_text = input("Введите текст для картинки: ").strip()
    if not user_text:
        raise ValueError("Текст не может быть пустым.")
    return user_text


def get_yandex_token(filename="token.txt"):
    """
        Запрашивает у пользователя токен Яндекс.Диска.

        Функция считывает данные из файла (по умолчанию token.txt),
        удаляет начальные и конечные пробелы и проверяет,
        что строка не пустая.

        Params:
            filename: Путь к файлу с токеном, значение
                по умолчанию - token.txt

        Returns:
            str: Валидный непустой токен.

        Raises:
            ValueError: Если пользователь ввёл пустую строку.
    """
    with open(filename, 'r') as file:
        token = file.read().strip()
    if not token:
        raise ValueError("Токен не может быть пустым.")
    return token


def download_cat_image(user_text):
    """
    Функция скачивания изображения с пользовательским текстом

    Params:
        user_text: Пользовательский текст

    Returns:
        bytes: Изображение в виде массива байтов
    """
    encoded_text = quote(user_text)
    api_url = CATAAS_API_URL.format(encoded_text)
    response = requests.get(api_url, timeout=10)
    response.raise_for_status()

    return response.content


def save_image_locally(content, filename=LOCAL_IMAGE_FILENAME):
    """
    Функция для промежуточного сохранения файла
    на локальной машине пользователя перед
    загрузкой в облако

    Params:
        content: Изображение в виде массива байтов

        filename: имя временного файла,
            по умолчанию - константа LOCAL_IMAGE_FILENAME

    Returns:
        int: Размер сохраненного изображения в байтах
    """
    with open(filename, 'wb') as f:
        f.write(content)

    return os.path.getsize(filename)


def ensure_yandex_folder(headers):
    """
    Проверяет существование папки на Яндекс.Диске и создаёт её при необходимости.

    Функция отправляет запрос к API Яндекс.Диска для проверки
    существования папки, указанной в константе FOLDER_NAME.
    Если папка не существует (ошибка 404), выполняется попытка её создания.
    В случае ошибки проверки или создания возбуждается исключение.

    Params:
        headers (dict): Заголовки HTTP-запроса, содержащие OAuth-токен
            для авторизации в Яндекс.Диске.

    Raises:
        RuntimeError: Если произошла ошибка при проверке существования
            папки или при её создании.
        """
    params = {'path': FOLDER_NAME}
    response = requests.get(YANDEX_API_URL, headers=headers, params=params)

    if response.status_code == 404:
        create_response = requests.put(YANDEX_API_URL, headers=headers, params=params)
        if create_response.status_code != 201:
            raise RuntimeError("Ошибка создания папки.")
    elif response.status_code != 200:
        raise RuntimeError("Ошибка проверки папки.")


def upload_file_to_yandex(local_filename, user_text, headers):
    """
        Загружает локальный файл на Яндекс.Диск.

        Функция запрашивает у Яндекс.Диска ссылку для загрузки файла,
        после чего выполняет PUT-запрос для отправки файла.
        Имя файла формируется на основе пользовательского текста.

        Params:
            local_filename (str): Путь к локальному файлу для загрузки.
            user_text (str): Текст пользователя, используемый для формирования
                             имени файла на Яндекс.Диске.
            headers (dict): HTTP-заголовки с OAuth-токеном для авторизации.

        Returns:
            str: Путь к файлу на Яндекс.Диске.

        Raises:
            requests.exceptions.RequestException: При ошибке HTTP-запроса.
            RuntimeError: Если не удалось получить ссылку для загрузки.
            IOError: При ошибке чтения локального файла.
        """
    remote_path = f"{FOLDER_NAME}/{user_text}.jpg"

    params = {'path': remote_path, 'overwrite': 'true'}
    upload_link_response = requests.get(
        f"{YANDEX_API_URL}/upload",
        headers=headers,
        params=params
    )
    upload_link_response.raise_for_status()

    href = upload_link_response.json().get('href')
    if not href:
        raise RuntimeError("Не удалось получить ссылку для загрузки.")

    with open(local_filename, 'rb') as f:
        upload_response = requests.put(href, files={'file': f})
        upload_response.raise_for_status()

    return remote_path


def save_file_info_json(user_text, file_size, remote_path):
    """
        Сохраняет информацию о загруженном файле в JSON-файл.

        Формирует словарь с метаданными (имя файла, текст,
        размер, дата загрузки и путь на Яндекс.Диске)
        и записывает его в JSON-файл с кодировкой UTF-8.

        Params:
            user_text (str): Текст пользователя, использованный в имени файла.
            file_size (int): Размер файла в байтах.
            remote_path (str): Путь к файлу на Яндекс.Диске.

        Returns:
            str: Имя созданного JSON-файла.
    """
    file_info = {
        'filename': f"{user_text}.jpg",
        'text': user_text,
        'size_bytes': file_size,
        'upload_date': datetime.now().isoformat(),
        'remote_path': f"disk:/{remote_path}"
    }

    json_filename = f"{JSON_FILENAME_HEAD}{user_text}{JSON_FILENAME_TAIL}"

    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(file_info, f, ensure_ascii=False, indent=2)

    return json_filename


def cleanup_file(filename):
    """
    Удаляет файл из локальной файловой системы, если он существует.
    Params:
        filename (str): Путь к файлу для удаления.
    """
    if os.path.exists(filename):
        os.remove(filename)

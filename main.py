from functions import *


def main():
    try:
        user_text = get_user_text()
        yandex_token = get_yandex_token()

        print(f"\nПолучаем картинку с текстом: '{user_text}'...")

        image_content = download_cat_image(user_text)
        file_size = save_image_locally(image_content)

        print(f"Картинка получена. Размер: {file_size} байт")

        headers = {
            'Authorization': f'OAuth {yandex_token}',
            'Content-Type': 'application/json'
        }

        ensure_yandex_folder(headers)

        remote_path = upload_file_to_yandex(
            LOCAL_IMAGE_FILENAME,
            user_text,
            headers
        )

        print(f"Файл '{user_text}.jpg' успешно загружен на Яндекс.Диск")

        json_filename = save_file_info_json(
            user_text,
            file_size,
            remote_path
        )

        print(f"Информация сохранена в файл '{json_filename}'")

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
    except (IOError, ValueError, RuntimeError) as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
    finally:
        cleanup_file(LOCAL_IMAGE_FILENAME)
        print("Временный файл удалён.")


if __name__ == "__main__":
    main()

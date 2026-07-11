import requests
import json
import time
from typing import Dict, List, Optional


class Search4FacesAPI:
    def __init__(self):
        self.base_url = 'https://search4faces.com'
        self.session = requests.Session()
        
        # Устанавливаем общие заголовки для сессии
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://search4faces.com',
            'Referer': 'https://search4faces.com/search_vkwall.html',
            'Sec-Ch-Ua': '"Chromium";v="149", "Not)A;Brand";v="24"',
            'Sec-Ch-Ua-Platform': '"Linux"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Encoding': 'gzip, deflate, br',
            'Priority': 'u=1, i',
        })
    
    def get_cookies(self) -> bool:
        """Получает актуальные cookies, заходя на главную страницу"""
        try:
            response = self.session.get(f'{self.base_url}/search_vkwall.html')
            return response.status_code == 200
        except Exception as e:
            print(f"Ошибка получения cookies: {e}")
            return False
    
    def upload_image(self, image_path: str) -> Optional[Dict]:
        """
        Загружает изображение на сервер
        
        Args:
            image_path: Путь к файлу изображения
            
        Returns:
            Словарь с результатом или None при ошибке
        """
        url = f'{self.base_url}/assets/php/upload.php'
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Отправляем POST запрос с изображением
            response = self.session.post(
                url,
                data=image_data,
                headers={'Content-Type': 'image/jpeg'}
            )
            
            if response.status_code != 200:
                print(f"Ошибка загрузки: HTTP {response.status_code}")
                return None
            
            result = response.json()
            print(f"✓ Изображение загружено. Файл: {result.get('url')}")
            return result
            
        except FileNotFoundError:
            print(f"Файл не найден: {image_path}")
            return None
        except json.JSONDecodeError:
            print("Ошибка парсинга JSON ответа")
            return None
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return None
    
    def detect_faces(self, filename: str, boundings: List, 
                     query: str = 'vk01', results: int = 500, 
                     lang: str = 'ru') -> Optional[Dict]:
        """
        Выполняет поиск лиц по загруженному изображению
        
        Args:
            filename: Имя файла от upload.php
            boundings: Координаты обнаруженных лиц
            query: Тип поиска (vk01 - ВКонтакте)
            results: Количество результатов
            lang: Язык
            
        Returns:
            Словарь с результатами поиска или None при ошибке
        """
        url = f'{self.base_url}/assets/php/detect.php'
        
        payload = {
            'query': query,
            'results': results,
            'lang': lang,
            'filename': filename,
            'boundings': boundings
        }
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers={'Content-Type': 'text/plain;charset=UTF-8'}
            )
            
            if response.status_code != 200:
                print(f"Ошибка поиска: HTTP {response.status_code}")
                return None
            
            result = response.json()
            faces_found = result.get('faces_found', 0)
            print(f"✓ Найдено совпадений: {faces_found}")
            return result
            
        except Exception as e:
            print(f"Ошибка выполнения поиска: {e}")
            return None
    
    def search_face(self, image_path: str, max_results: int = 500) -> Optional[List[Dict]]:
        """
        Полный процесс поиска лица по изображению
        
        Args:
            image_path: Путь к файлу изображения
            max_results: Максимальное количество результатов
            
        Returns:
            Список найденных профилей или None при ошибке
        """
        print(f"\n🔍 Начинаем поиск по изображению: {image_path}")
        print("=" * 60)
        
        # Шаг 1: Получаем cookies
        print("\n[1/3] Получаем сессию...")
        if not self.get_cookies():
            print("❌ Не удалось получить cookies")
            return None
        
        # Шаг 2: Загружаем изображение
        print("\n[2/3] Загружаем изображение...")
        upload_result = self.upload_image(image_path)
        if not upload_result:
            print("❌ Ошибка загрузки изображения")
            return None
        
        # Извлекаем данные из результата загрузки
        filename = upload_result.get('url')
        boundings = upload_result.get('boundings', [])
        
        if not filename or not boundings:
            print("❌ Неверный ответ от сервера загрузки")
            return None
        
        # Преобразуем boundings в плоский список
        if isinstance(boundings, list) and len(boundings) > 0:
            if isinstance(boundings[0], list):
                boundings_flat = [item for sublist in boundings for item in sublist]
            else:
                boundings_flat = boundings
        else:
            boundings_flat = []
        
        # Небольшая задержка между запросами
        time.sleep(1)
        
        # Шаг 3: Выполняем поиск
        print("\n[3/3] Выполняем поиск совпадений...")
        detect_result = self.detect_faces(
            filename=filename,
            boundings=boundings_flat,
            results=max_results
        )
        
        if not detect_result:
            print("❌ Ошибка выполнения поиска")
            return None
        
        # Обрабатываем результаты
        faces = detect_result.get('faces', [])
        if not faces:
            print("⚠️ Совпадений не найдено")
            return []
        
        print(f"\n{'=' * 60}")
        print(f"✅ НАЙДЕНО {len(faces)} СОВПАДЕНИЙ")
        print(f"{'=' * 60}\n")
        
        profiles = []
        for i, face in enumerate(faces, 1):
            profile = self._parse_face_data(face, i)
            profiles.append(profile)
            self._print_profile(profile)
        
        return profiles
    
    def _parse_face_data(self, face: List, index: int) -> Dict:
        """Парсит данные о найденном лице"""
        # Структура массива face:
        # [source, vk_url, face_img_url, photo_url, photo_id, x1, y1, x2, y2, 
        #  full_photo_url, similarity, type, age, first_name, last_name, middle_name, 
        #  city, country, birthday, extra]
        
        return {
            'index': index,
            'source': face[0] if len(face) > 0 else '',
            'vk_url': face[1] if len(face) > 1 else '',
            'face_image_url': face[2] if len(face) > 2 else '',
            'photo_url': face[3] if len(face) > 3 else '',
            'photo_id': face[4] if len(face) > 4 else '',
            'coordinates': {
                'x1': face[5] if len(face) > 5 else 0,
                'y1': face[6] if len(face) > 6 else 0,
                'x2': face[7] if len(face) > 7 else 0,
                'y2': face[8] if len(face) > 8 else 0,
            },
            'full_photo_url': face[9] if len(face) > 9 else '',
            'similarity': float(face[10]) if len(face) > 10 and face[10] else 0,
            'type': face[11] if len(face) > 11 else '',
            'age': int(face[12]) if len(face) > 12 and face[12] != '' and face[12] != '-1' else None,
            'first_name': face[13] if len(face) > 13 else '',
            'last_name': face[14] if len(face) > 14 else '',
            'middle_name': face[15] if len(face) > 15 else '',
            'city': face[16] if len(face) > 16 else '',
            'country': face[17] if len(face) > 17 else '',
            'birthday': face[18] if len(face) > 18 and face[18] != '' else '',
            'extra': face[19] if len(face) > 19 else '',
        }
    
    def _print_profile(self, profile: Dict):
        """Выводит информацию о профиле"""
        print(f"📋 Профиль #{profile['index']}")
        print(f"   Имя: {profile['first_name']} {profile['last_name']}")
        if profile['middle_name']:
            print(f"   Отчество: {profile['middle_name']}")
        print(f"   Возраст: {profile['age'] if profile['age'] else 'не указан'}")
        if profile['birthday']:
            print(f"   Дата рождения: {profile['birthday']}")
        print(f"   Город: {profile['city']}, {profile['country']}")
        print(f"   Сходство: {profile['similarity']}%")
        print(f"   VK ID: {profile['vk_url']}")
        print(f"   Фото профиля: {profile['face_image_url']}")
        print(f"   Оригинальное фото: {profile['full_photo_url']}")
        print("-" * 60)
    
    def save_results_to_json(self, profiles: List[Dict], output_file: str = 'results.json'):
        """Сохраняет результаты в JSON файл"""
        if not profiles:
            print("Нет данных для сохранения")
            return
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Результаты сохранены в файл: {output_file}")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")


def main():
    """Пример использования"""
    # Создаем экземпляр API
    api = Search4FacesAPI()
    
    # Путь к вашему изображению
    image_path = 'test_image.jpg'  # ЗАМЕНИТЕ на путь к вашему файлу
    
    # Выполняем поиск
    profiles = api.search_face(image_path, max_results=500)
    
    if profiles:
        # Сохраняем результаты
        api.save_results_to_json(profiles, 'search_results.json')
        
        print(f"\n🎉 Поиск завершен! Найдено {len(profiles)} профилей")
    else:
        print("\n❌ Поиск не дал результатов")


if __name__ == '__main__':
    main()
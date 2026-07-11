# example_usage.py - Примеры использования

from search4faces import Search4FacesAPI

def example_basic_search():
    """Базовый пример поиска"""
    api = Search4FacesAPI()
    profiles = api.search_face('photo.jpg', max_results=100)
    
    if profiles:
        print(f"Найдено {len(profiles)} профилей")
        # Первый результат
        first = profiles[0]
        print(f"Лучшее совпадение: {first['first_name']} {first['last_name']}")
        print(f"Сходство: {first['similarity']}%")

def example_with_custom_params():
    """Поиск с кастомными параметрами"""
    api = Search4FacesAPI()
    
    # Можно вызвать шаги отдельно
    api.get_cookies()
    upload_result = api.upload_image('photo.jpg')
    
    if upload_result:
        filename = upload_result['url']
        boundings = upload_result['boundings']
        
        # Преобразуем boundings
        if isinstance(boundings[0], list):
            boundings_flat = [item for sublist in boundings for item in sublist]
        else:
            boundings_flat = boundings
        
        # Выполняем поиск с другими параметрами
        result = api.detect_faces(
            filename=filename,
            boundings=boundings_flat,
            query='vk01',      # ВКонтакте
            results=1000,       # Больше результатов
            lang='en'           # Английский язык
        )
        
        if result:
            print(f"Найдено {result['faces_found']} совпадений")

def example_batch_search():
    """Поиск по нескольким изображениям"""
    api = Search4FacesAPI()
    
    images = ['photo1.jpg', 'photo2.jpg', 'photo3.jpg']
    all_results = {}
    
    for image_path in images:
        print(f"\nОбработка: {image_path}")
        profiles = api.search_face(image_path, max_results=50)
        if profiles:
            all_results[image_path] = profiles
    
    # Сохраняем все результаты
    api.save_results_to_json(all_results, 'batch_results.json')

if __name__ == '__main__':
    example_basic_search()
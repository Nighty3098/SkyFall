from search4faces import Search4FacesAPI


def example_basic_search():
    print("=" * 60)
    print("EXAMPLE 1: Basic Search")
    print("=" * 60)

    api = Search4FacesAPI()
    profiles = api.search_face("photo.jpg", max_results=100)

    if profiles:
        print(f"\nFound {len(profiles)} profiles")
        first = profiles[0]
        print(f"Best match: {first['first_name']} {first['last_name']}")
        print(f"Similarity: {first['similarity']}%")
        print(f"VK: {first['vk_url']}")

        api.save_results_to_json(profiles, "basic_search_results.json")
    else:
        print("No profiles found")


def example_with_download():
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Search with Image Download")
    print("=" * 60)

    api = Search4FacesAPI()
    profiles = api.search_face("photo.jpg", max_results=50)

    if profiles:
        top_profiles = profiles[:10]
        downloaded = api.download_images(
            top_profiles, download_dir="top_faces", download_full=True
        )
        print(f"\nDownloaded {len(downloaded)} images to 'top_faces' directory")


def example_custom_params():
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Step-by-Step Search with Custom Parameters")
    print("=" * 60)

    api = Search4FacesAPI()

    print("\nStep 1: Getting cookies...")
    api.get_cookies()

    print("\nStep 2: Uploading image...")
    upload_result = api.upload_image("photo.jpg")

    if upload_result:
        filename = upload_result["url"]
        boundings = upload_result["boundings"]

        if isinstance(boundings[0], list):
            boundings_flat = [item for sublist in boundings for item in sublist]
        else:
            boundings_flat = boundings

        print("\nStep 3: Searching with custom parameters...")
        result = api.detect_faces(
            filename=filename,
            boundings=boundings_flat,
            query="vk01",
            results=1000,
            lang="ru",
        )

        if result:
            faces_found = result.get("faces_found", 0)
            print(f"Found {faces_found} matches")

            faces = result.get("faces", [])[:5]
            for i, face in enumerate(faces, 1):
                profile = api._parse_face_data(face, i)
                api._print_profile(profile)


def example_batch_search():
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Batch Search for Multiple Photos")
    print("=" * 60)

    api = Search4FacesAPI()

    images = ["photo1.jpg", "photo2.jpg", "photo3.jpg"]
    all_results = {}

    for image_path in images:
        print(f"\nProcessing: {image_path}")
        profiles = api.search_face(image_path, max_results=50)
        if profiles:
            all_results[image_path] = profiles

    if all_results:
        api.save_results_to_json(all_results, "batch_results.json")
        print(f"\nResults saved for {len(all_results)} images")


def example_filter_results():
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Filtering Results")
    print("=" * 60)

    api = Search4FacesAPI()
    profiles = api.search_face("photo.jpg", max_results=500)

    if profiles:
        photo_urls = [p["full_photo_url"] for p in profiles]
        print(f"\nTotal photos: {len(photo_urls)}")

        matches = [(p["first_name"], p["last_name"], p["similarity"]) for p in profiles]
        print(f"Total matches: {len(matches)}")

        sorted_profiles = sorted(profiles, key=lambda x: x["similarity"], reverse=True)
        print(f"\nTop 3 by similarity:")
        for p in sorted_profiles[:3]:
            print(f"  {p['first_name']} {p['last_name']}: {p['similarity']}%")

        high_quality = [p for p in profiles if p["similarity"] > 50]
        print(f"\nProfiles with similarity >50%: {len(high_quality)}")

        vk_links = [p["vk_url"] for p in profiles]
        print(f"VK links: {len(vk_links)}")


def example_save_specific_data():
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Saving Specific Data")
    print("=" * 60)

    api = Search4FacesAPI()
    profiles = api.search_face("photo.jpg", max_results=100)

    if profiles:
        simplified = []
        for p in profiles:
            simplified.append(
                {
                    "name": f"{p['first_name']} {p['last_name']}",
                    "vk_url": p["vk_url"],
                    "similarity": p["similarity"],
                    "city": p["city"],
                    "country": p["country"],
                    "age": p["age"],
                    "photo_url": p["full_photo_url"],
                }
            )

        api.save_results_to_json(simplified, "simplified_results.json")
        print("Simplified results saved to 'simplified_results.json'")


if __name__ == "__main__":
    example_basic_search()
    # example_with_download()
    # example_custom_params()
    # example_batch_search()
    # example_filter_results()
    # example_save_specific_data()

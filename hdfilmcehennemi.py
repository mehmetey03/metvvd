from bs4 import BeautifulSoup
import json

# HTML içeriğini ayrıştır
soup = BeautifulSoup(html_content, 'html.parser')

# Tüm film poster elemanlarını bul
film_elements = soup.find_all('a', class_='poster')

films = []

for film in film_elements:
    film_data = {}
    
    # Film başlığı
    title_element = film.find('strong', class_='poster-title')
    film_data['title'] = title_element.text.strip() if title_element else None
    
    # Film linki
    film_data['link'] = film.get('href')
    
    # Film yılı
    year_element = film.find('div', class_='poster-meta').find_all('span')[0]
    film_data['year'] = year_element.text.strip() if year_element else None
    
    # Yorum sayısı
    comment_element = film.find('div', class_='poster-meta').find_all('span')[1]
    film_data['comment_count'] = comment_element.text.strip() if comment_element else None
    
    # IMDB puanı
    imdb_element = film.find('span', class_='imdb')
    film_data['imdb_rating'] = imdb_element.text.strip() if imdb_element else None
    
    # Dil/altyazı bilgisi
    lang_element = film.find('span', class_='poster-lang')
    if lang_element:
        # Türkçe Dublaj/Altayazı durumunu kontrol et
        tr_flag = lang_element.find('i', class_='tr-flag')
        text_span = lang_element.find('span')
        
        if tr_flag:
            film_data['language'] = 'Türkçe Dublaj'
        elif text_span:
            film_data['language'] = text_span.text.strip()
        else:
            film_data['language'] = 'Bilinmiyor'
    
    # Resim URL'leri
    img_element = film.find('img', class_='lazyload')
    if img_element:
        film_data['image'] = img_element.get('data-src')
        film_data['image_2x'] = img_element.get('data-srcset', '').split(' ')[1] if 'data-srcset' in img_element.attrs else None
    
    # Popover içeriği (detaylı bilgiler)
    popover = film.find_next_sibling('div', class_='poster-popover')
    if popover and 'synced' in popover.get('class', []):
        # IMDB puanı ve oy sayısı
        rating_element = popover.find('div', class_='popover-rating')
        if rating_element:
            rating_text = rating_element.find('p')
            review_count = rating_element.find('span', class_='review-count')
            film_data['detailed_imdb'] = rating_text.text.strip() if rating_text else None
            film_data['review_count'] = review_count.text.strip() if review_count else None
        
        # Özet
        description = popover.find('p', class_='popover-description')
        if description:
            # "Özet" başlığını kaldır
            summary = description.text.replace('Özet', '').strip()
            film_data['summary'] = summary
        
        # Meta bilgileri (kanal, türler, kategori)
        meta_elements = popover.find_all('span')
        for meta in meta_elements:
            strong_tag = meta.find('strong')
            if strong_tag:
                key = strong_tag.text.strip().lower()
                strong_tag.extract()  # strong etiketini kaldır
                value = meta.text.strip()
                
                if 'kanal' in key:
                    film_data['channel'] = value
                elif 'türler' in key:
                    film_data['genres'] = [g.strip() for g in value.split(',')]
                elif 'kategori' in key:
                    film_data['category'] = value
    
    films.append(film_data)

# JSON olarak kaydet
with open('films.json', 'w', encoding='utf-8') as f:
    json.dump(films, f, ensure_ascii=False, indent=2)

print(f"Toplam {len(films)} film bulundu.")
print("Veriler 'films.json' dosyasına kaydedildi.")

# İlk filmi göster
if films:
    print("\nİlk film bilgisi:")
    print(json.dumps(films[0], ensure_ascii=False, indent=2))

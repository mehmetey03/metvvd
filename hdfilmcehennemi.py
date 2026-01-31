from bs4 import BeautifulSoup
import json
import re

def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    film_elements = soup.find_all('a', class_='poster')
    films = []

    for film in film_elements:
        film_data = {}
        
        try:
            # Temel Bilgiler
            title_element = film.find('strong', class_='poster-title')
            film_data['title'] = title_element.text.strip() if title_element else "Bilinmiyor"
            film_data['link'] = film.get('href')
            
            # Meta Bilgileri (Yıl ve Yorum)
            meta_div = film.find('div', class_='poster-meta')
            if meta_div:
                spans = meta_div.find_all('span')
                film_data['year'] = spans[0].text.strip() if len(spans) > 0 else None
                film_data['comment_count'] = spans[1].text.strip() if len(spans) > 1 else "0"
            
            # IMDB Puanı
            imdb_element = film.find('span', class_='imdb')
            film_data['imdb_rating'] = imdb_element.text.strip() if imdb_element else None
            
            # Dil Bilgisi (İkon Kontrolü)
            lang_element = film.find('span', class_='poster-lang')
            if lang_element:
                if lang_element.find('i', class_='tr-flag'):
                    film_data['language'] = 'Türkçe Dublaj'
                else:
                    film_data['language'] = lang_element.text.strip()
            
            # Görsel (Lazyload Desteği)
            img = film.find('img')
            if img:
                # data-src yoksa normal src'yi al
                film_data['image'] = img.get('data-src') or img.get('src')

            # Popover (Özet ve Detaylar)
            # find_next_sibling yerine bazen aynı kapsayıcı içinde aramak daha güvenlidir
            popover = film.find_next_sibling('div', class_='poster-popover')
            if popover:
                # Özet
                desc = popover.find('p', class_='popover-description')
                if desc:
                    film_data['summary'] = desc.text.replace('Özet', '').strip()
                
                # Dinamik Meta Verileri (Tür, Kategori vb.)
                for s in popover.find_all('span'):
                    strong = s.find('strong')
                    if strong:
                        key_text = strong.text.strip().lower()
                        # Strong etiketini temizleyip kalan metni değer olarak alıyoruz
                        val_text = s.text.replace(strong.text, "").strip(": ")
                        
                        if 'türler' in key_text:
                            film_data['genres'] = [g.strip() for g in val_text.split(',')]
                        elif 'kategori' in key_text:
                            film_data['category'] = val_text
                        elif 'kanal' in key_text:
                            film_data['channel'] = val_text

            films.append(film_data)
        except Exception as e:
            print(f"Bir film işlenirken hata oluştu: {e}")
            continue

    return films

# --- Kayıt ve Çıktı ---
extracted_films = parse_html(html_content) # html_content'in yukarıda tanımlı olduğunu varsayıyoruz

with open('films.json', 'w', encoding='utf-8') as f:
    json.dump(extracted_films, f, ensure_ascii=False, indent=2)

print(f"✅ Başarıyla {len(extracted_films)} film ayrıştırıldı.")

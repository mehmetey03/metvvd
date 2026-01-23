import json
from bs4 import BeautifulSoup
import re

# Senin paylaştığın ham HTML verisi (Burayı kısalttım ama kod hepsini işler)
raw_html = """
[<div class="list"><div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Sakincali/izle"><img src="/i/thumbnail/1823" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Sakincali/izle"><div class="program-name"><strong>Sakıncalı</strong></div> <div class="program-desc">
                                        Sakıncalı, çocuğunu kaybettikten sonra hayata tutunmaya çalışan Süreyya’nın (Özge Özpirinçci) adalet ve intikam mücadelesini konu alıyor. Kayıp, öfke ve dayanışma duygularının iç içe geçtiği bu yolculuk, güçlü bir kadının yeniden doğuşunu ekrana taşı...
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Ben-Onun-Annesiyim/izle"><img src="/i/thumbnail/1819" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Ben-Onun-Annesiyim/izle"><div class="program-name"><strong>Ben Onun Annesiyim</strong></div> <div class="program-desc">
                                        Ayşe (Funda Eryiğit), yıllar boyunca kocasını öldürmekle suçlanarak cezaevinde kalmıştır. Özgürlüğüne kavuştuğunda, tek amacı yıllar önce elinden alınan kızı Zeynep’e yeniden kavuşmaktır. Ancak kızı artık başka bir adam tarafından evlat edinilmiştir...
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Leyla-Hayat-Ask-Adalet/izle"><img src="/i/thumbnail/1780" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Leyla-Hayat-Ask-Adalet/izle"><div class="program-name"><strong>Leyla: Hayat… Aşk… Adalet...</strong></div> <div class="program-desc">
                                        Küçük yaşta annesini kaybeden ve babasından başka kimsesi olmayan Leyla’nın hayatı, babasının yeniden evlenmesiyle altüst olur. Üvey annesi Nur tarafından bir çöplüğe bırakılan Leyla, zorlu sınavlardan geçtikten yıllar sonra Nur’dan intikamını almak...
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Hudutsuz-Sevda/izle"><img src="/i/thumbnail/1693" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Hudutsuz-Sevda/izle"><div class="program-name"><strong>Hudutsuz Sevda</strong></div> <div class="program-desc">
                                        Küçük bir çocukken kan davası nedeniyle babasını kaybedip İstanbul’a sürülen Halil İbrahim, (Deniz Can Aktaş), 20 yıl sonra memleketi Karadeniz’e yakışıklı, güçlü bir delikanlı olarak geri döner. Burada sevdiği kız Yasemin (Biran Damla Yılmaz) ile ev...
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Sakir-Pasa-Ailesi-Mucizeler-ve-Skandallar/izle"><img src="/i/thumbnail/1786" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Sakir-Pasa-Ailesi-Mucizeler-ve-Skandallar/izle"><div class="program-name"><strong>Şakir Paşa Ailesi: Mucizeler ve Skandallar</strong></div> <div class="program-desc">
                                        Döneminin ilerisinde bir hayat sürdüren Şakir Paşa ailesinin entrika ve sırlarla dolu hayatlarını anlatan dizinin hikayesi 1912’de başlıyor. Halikarnas Balıkçısı adıyla Bodrum’u bugünkü ününe kavuşturan Cevat Şakir Kabaağaçlı’nın İtalyan eşiyle berab...
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Kizil-Goncalar/izle"><img src="/i/thumbnail/1721" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Kizil-Goncalar/izle"><div class="program-name"><strong>Kızıl Goncalar</strong></div> <div class="program-desc">
                                        Kızıl Goncalar, seküler bir Atatürkçü olan Levent (Özcan Deniz) ve mutaassıp bir tarikatın içinde yaşayan Meryem’in (Özgü Namal) kaderlerinin kesişmesini konu alırken, inanç ve fikir ayrılıklarına rağmen "evlat" söz konusu olduğunda anneliğin/babalığ...
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Yabani/izle"><img src="/i/thumbnail/1691" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Yabani/izle"><div class="program-name"><strong>Yabani</strong></div> <div class="program-desc">
                                        Köklü bir aileden kaçırılıp sokaklara düşen bir çocuğun, yıllar sonra evine dönmesi ile kendini yeniden var etme mücadelesini anlatıyor.
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Ask-Evlilik-Bosanma/izle"><img src="/i/thumbnail/1785" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Ask-Evlilik-Bosanma/izle"><div class="program-name"><strong>Aşk Evlilik Boşanma</strong></div> <div class="program-desc">
                                        Aynı iş yerinde çalışmaktan başka ortak noktası olmayan üç kadının, evliliklerinde kendilerine biçtikleri roller ellerinden alındıktan sonra, ayakta kalabilmek için birbirlerine tutunmalarının hikayesini ele alacak.
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Gizli-Bahce/izle"><img src="/i/thumbnail/1777" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Gizli-Bahce/izle"><div class="program-name"><strong>Gizli Bahçe</strong></div> <div class="program-desc">
                                        Nazlı, oğlu Memo’yla yaşayan yoksul, bekar ve genç bir annedir. Memo’nun güçlü ve zengin amcası Demir Akçınar, vefat eden abisinin bir oğlu olduğunu öğrenince Memo’ya sahip çıkmak için peşlerine düşer. Nazlı’nın mesleğini öğrendiği anda, yeğeninin bö...
                                    </div></a></div></div> <div class="list-item"><div class="list-item-image"><a href="https://www.nowtv.com.tr/Kirli-Sepeti/izle"><img src="/i/thumbnail/1694" alt=""></a></div> <div class="list-item-meta"><a href="https://www.nowtv.com.tr/Kirli-Sepeti/izle"><div class="program-name"><strong>Kirli Sepeti</strong></div> <div class="program-desc">
                                        İstanbul'un zengin muhitlerinden birinde, butik bir sitede çalışan hizmetliler ve onların iş verenlerinin iç içe geçmiş hayatlarını konu edinen dizide; yukarıdakiler ve aşağıdakiler arasındaki büyük uçuruma da tanıklık ediyoruz. Aşkın, sırların, yala...
                                    </div></a></div></div><section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-B8dLucYWca9oUowtrotGBQBYo1QK3DVf" data-google-query-id="CLPL96ftopIDFXfPDQkd3tALaw" style=""><div id="google_ads_iframe_/113421212/Nowtv_Desktop/Arsiv/Diger/Leaderboard_0__container__" style="border: 0pt none;"><iframe id="google_ads_iframe_/113421212/Nowtv_Desktop/Arsiv/Diger/Leaderboard_0" name="google_ads_iframe_/113421212/Nowtv_Desktop/Arsiv/Diger/Leaderboard_0" title="Üçüncü taraf reklam içeriği" width="728" height="90" scrolling="no" marginwidth="0" marginheight="0" frameborder="0" aria-label="Reklam" tabindex="0" allow="private-state-token-redemption;attribution-reporting" data-load-complete="true" data-google-container-id="4" style="border: 0px; vertical-align: bottom;"></iframe></div></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kotu-Kan/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1759" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kotu-Kan/izle">
                <div class="program-name">
                    <strong>Kötü Kan</strong>
                </div>
                <div class="program-desc">
                    "Kötü Kan”, bir gece kulübünün güvenlik müdürlüğünü yaparken tehlikeli bir mafya grubuyla başı derde giren eski polis memuru Kartal’ın yıllardır uzakta yaşayan çocuklarının yanına taşınmasıyla, bir yandan bulaştığı mafya batağından kurtulmaya çalışma...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Gaddar/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1719" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Gaddar/izle">
                <div class="program-name">
                    <strong>Gaddar</strong>
                </div>
                <div class="program-desc">
                    Uzun süren askerlik görevinden evine gelen Dağhan’ın (Çağatay Ulusoy) hayatı artık bıraktığı gibi değildir. Sevdiği kız Aydan (Sümeyye Aydoğan) ona haber vermeden çekmiş gitmiş, kardeşi Rüzgar (Fatih Berk Şahin) ise karanlık bir dünyanın içine düşmüş...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Sahane-Hayatim/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1708" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Sahane-Hayatim/izle">
                <div class="program-name">
                    <strong>Şahane Hayatım</strong>
                </div>
                <div class="program-desc">
                    Entrika, aşk, gerilim ve heyecan dolu dizi, hayata büyük haksızlıklarla gelmiş, bunları aşmak için çok çalışmış, bu yolda gerekenleri yapmış, şimdi ise şahane bir hayat yaşarken gelip onu bulan suç dolu geçmişinden kurtulmaya çalışan Şebnem’in sarsıc...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Korkma-Ben-Yanindayim/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1731" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Korkma-Ben-Yanindayim/izle">
                <div class="program-name">
                    <strong>Korkma Ben Yanındayım</strong>
                </div>
                <div class="program-desc">
                    Ailesinin gözbebeği İnci (Nilsu Berfin Aktaş), Ulusözler Koleji’nin burslu öğrencisidir. Sınıf arkadaşı ve aynı zamanda okul sahibinin oğlu Mert’ten (Eren Ören) hamile kalır. Üniversite sınavına hazırlanan ve hayallerine koşan iki gencin hayatı sonsu...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kopuk/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1723" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kopuk/izle">
                <div class="program-name">
                    <strong>Kopuk</strong>
                </div>
                <div class="program-desc">
                    Zenginden çalıp fakire vermek… Hala bir halk kahramanlığı hikayesi mi yoksa hepimizin- en fakirimizin bile kahramanı artık paranın ta kendisi mi?
Ferhan rüşvetçilerin, dolandırıcıların, hak edilmeden yapılan vurgunlarla zengin olan insanların parası...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Bambaska-Biri/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1698" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Bambaska-Biri/izle">
                <div class="program-name">
                    <strong>Bambaşka Biri</strong>
                </div>
                <div class="program-desc">
                    Ormanda vahşice işlenen Hamdi Atılbay cinayeti, karışık geçmişini arkada bırakarak artık yeni düzenini kurmak isteyen genç savcı Leyla ile düzenli ve şöhret dolu bir hayata sahip olan hırslı gazeteci Kenan’ın yollarını kesiştirir. Ne var ki bu cinaye...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Adim-Farah/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1661" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Adim-Farah/izle">
                <div class="program-name">
                    <strong>Adım Farah</strong>
                </div>
                <div class="program-desc">
                    Farah (Demet Özdemir), 28 yaşında İranlı bir kadındır. 6 sene evvel İran'dan Fransa'ya kaçarken İstanbul'da durmak zorunda kalır çünkü hamile olduğunu öğrenmiştir. Kaçak olarak burada yaşamaya başlar. Üstelik, oğlu Kerimşah' (Rastin Pakhana...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kader-Baglari/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1692" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kader-Baglari/izle">
                <div class="program-name">
                    <strong>Kader Bağları</strong>
                </div>
                <div class="program-desc">
                    Yolları bir üzüm bağında kesişen iki gencin tutkulu, delidolu sevdalarının öyküsünü; iki ayrı dünyanın insanı Sevda (Ayça Ayşin Turan) ve Kerem’in (Serkan Çayoğlu) aşk ve mücadele sınavını konu alıyor.
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Ruhun-Duymaz/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1686" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Ruhun-Duymaz/izle">
                <div class="program-name">
                    <strong>Ruhun Duymaz</strong>
                </div>
                <div class="program-desc">
                    Onur Karasu (Şükrü Özyıldız) genç yaşında daire başkanlığına terfi etmiş başarılı bir istihbarat ajanıdır ve bir süredir Türkiye'nin en büyük kuyumculuk şirketinin sahibi Civan Koral (Tuğrul Tülek)’in&nbsp; peşindedir. Koral Mücevherat'ı kirli...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Yaz-Sarkisi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1682" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Yaz-Sarkisi/izle">
                <div class="program-name">
                    <strong>Yaz Şarkısı</strong>
                </div>
                <div class="program-desc">
                    Okumak için geldiği İstanbul’da babasının hayaline tutunan ve o hayali annesinden gizlice gerçekleştirmeye çalışan Yaz’ın (Nilsu Berfin Aktaş) hikayesini konu alıyor.
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-GFN7bHB7U89qJKAv7xOwIiboJJtf8ZUM"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kismet/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1680" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kismet/izle">
                <div class="program-name">
                    <strong>Kısmet</strong>
                </div>
                <div class="program-desc">
                    Mahallenin gözbebeği Avukat Doğan ile güzeller güzeli komşusu Melike’nin 5 yaşından beri nasıl olup da kavuşamadıklarının hikayesi...&nbsp; Bazen kavuşmak için iki tarafın da çok sevmesi yeterli olmaz ama ayrılmak da "Kısmet" değildir.
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Gulcemal/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1666" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Gulcemal/izle">
                <div class="program-name">
                    <strong>Gülcemal</strong>
                </div>
                <div class="program-desc">
                    Annesinin küçükken terk edip karanlık bir canavara dönüştürdüğü Gülcemal (Murat Ünalmış) ile güzeller güzeli Deva'nın (Melis Sezen) nefretle başlayıp giderek ateş, tutku ve fırtınanın girdabına savrulan aşkını konu alıyor... Gülcemal'in annesiyle ola...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Tacsiz-Prenses/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1656" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Tacsiz-Prenses/izle">
                <div class="program-name">
                    <strong>Taçsız Prenses</strong>
                </div>
                <div class="program-desc">
                    Hayatı boyunca hayalperest annesi Şirin’in (Feride Çetin) masallarıyla büyüyen Masal (Elif Kurtaran), annesinin kalp hastalığı nedeniyle hastaneye kaldırılmasıyla soğuk ve gerçekçi bir dünyanın içine hapsolur ve alabildiğine yırtıcı, hırçın, her kötü...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Yalniz-Kalpler/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1660" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Yalniz-Kalpler/izle">
                <div class="program-name">
                    <strong>Yalnız Kalpler</strong>
                </div>
                <div class="program-desc">
                    Kapadokya’da geçirdikleri büyülü bir akşamdan sonra birbirlerinin izini kaybeden Ayda ve Teoman, üç yıl sonra Ankara’da yeniden karşılaşırlar ancak artık Ayda, Teoman’ın kuzeni Mehmet’le beraberdir. Annesinin baskıları altında ezilen Ayda ve ailesiyl...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Tetikcinin-Oglu/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1665" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Tetikcinin-Oglu/izle">
                <div class="program-name">
                    <strong>Tetikçinin Oğlu</strong>
                </div>
                <div class="program-desc">
                    Kırk yılın dostu; Korkmaz (Timuçin Esen) ve İskender (Şevket Çoruh).İskender’in oğlu bir kaza sonucu vefat eder. Suçlanan ise Korkmaz’ın 22 yıl önce kaybettiği ve yıllardır aradığı oğlu, Metin (Genco Özak). Artık iki dost karşı karşıyalar; biri oğlu...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Yasak-Elma/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1324" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Yasak-Elma/izle">
                <div class="program-name">
                    <strong>Yasak Elma</strong>
                </div>
                <div class="program-desc">
                    Hasan Ali’nin evinde yaşanan patlamanın üstünden altı ay geçmiştir. Patlama sonrasında Ender ve Yıldız yaralı kurtulurken, Hasan Ali vefat eder. Yapılan soruşturmanın ardından bombalamayı Hasan Ali’nin hasımlarının yaptığı anlaşılır ve dava kapanır....
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/EGO/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1657" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/EGO/izle">
                <div class="program-name">
                    <strong>EGO</strong>
                </div>
                <div class="program-desc">
                    Elif’le (Rüya Helin Demirbulut) Erhan (Alperen Duymaz) birbirlerini çok seven nişanlı bir çifttir ve hayattan en büyük beklentileri evlenip, mutlu bir yuva kurmaktır. Yaşantılarının rutini, Erhan’ın trajik aldanışı ile bozulur ve Erhan, ödenmesi çok...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Dokuz-Oguz/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1658" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Dokuz-Oguz/izle">
                <div class="program-name">
                    <strong>Dokuz Oğuz</strong>
                </div>
                <div class="program-desc">
                    Dokuz Oğuz; Türk’ün olduğu her yerde, Türk için savaşacak “Oğuz Timi” nin hikayesini anlatıyor…
Albay Tomris Toprak; “Türk Dünyası Acil Müdahale Timi”ni kurmak için titizlikle sürdürdüğü çalışmaların sonuna gelmiştir. Time seçtiği askerlerin en kısa...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Hayatimin-Sansi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1654" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Hayatimin-Sansi/izle">
                <div class="program-name">
                    <strong>Hayatımın Şansı</strong>
                </div>
                <div class="program-desc">
                    Yonca, küçük kızı Sare ile hayata tutunmaya çalışan yirmili yaşlarının ortasında genç bir annedir. Bir yandan hayatın zorlukları ile tek başına boğuşurken, bir yandan da Sare’nin biyolojik babasının açtığı velayet davası ile uğraşmaktadır. Her şeyin...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Iyilik/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1632" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Iyilik/izle">
                <div class="program-name">
                    <strong>İyilik</strong>
                </div>
                <div class="program-desc">
                    Neslihan’ın dışardan bakıldığında muhteşem, gıpta edilen bir hayatı vardır. Neslihan da bu illüzyona inanmış, kusursuz bir yaşam sürdüğünü zannederken hayatta en güvendiği insanın, kocasının onu uzun zamandır aldattığını öğrenir. Üstelik de kardeşi y...
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-Y6LiTxk2K2gpT3TitHwSo0SKRNp8SUJD"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Bir-Peri-Masali/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1649" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Bir-Peri-Masali/izle">
                <div class="program-name">
                    <strong>Bir Peri Masalı</strong>
                </div>
                <div class="program-desc">
                    Hayat neden Zeynep’in yüzüne gülmemiştir? Onun, yanında bakıcılık yaptığı insanlardan ne farkı vardır? O da rahat ve konforlu bir hayatı hak etmiyor mudur? Neden hayat ona gülmüyor, yalnızca zorluk çıkartıyordur?
Bu soruları tam da doğum gününde sor...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Tozluyaka/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1639" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Tozluyaka/izle">
                <div class="program-name">
                    <strong>Tozluyaka</strong>
                </div>
                <div class="program-desc">
                    Şans bile yolunu şaşırmadan uğramazdı Tozluyaka’ya ama bodoslama daldı birbirlerini kardeş seçenlerin arasına… Umudun yolculuğu başladı bu defa... Geçtikleri her sokağa, adını söyledikleri her insana, zulüme, adaletsizliğe, sevgiye aç olanlara dokunm...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Darmaduman/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1651" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Darmaduman/izle">
                <div class="program-name">
                    <strong>Darmaduman</strong>
                </div>
                <div class="program-desc">
                    Ailevi sebeplerle Eskişehir’den İstanbul’a taşınan Servet Ailesi bambaşka bir çevreye girerler. Başladıkları özel üniversitedeki ortama uyum sağlamaya çalışan ikizler Kerem ve Ece burada kendilerine hiç benzemeyen insanlarla tanışacak, bir yandan büy...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Mahkum/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1615" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Mahkum/izle">
                <div class="program-name">
                    <strong>Mahkum</strong>
                </div>
                <div class="program-desc">
                    Fırat Bulut, İstanbul Adliye'sinde görevli bir cumhuriyet savcısıdır. Başarılı bir savcı olan Fırat, eşi Zeynep ve beş yaşındaki kızı Nazlı'yla mutlu bir hayat yaşar. Ancak bir gün uyandığında son dört ayda olanları hiçbir şekilde hatırlamadan kendis...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kusursuz-Kiraci/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1646" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kusursuz-Kiraci/izle">
                <div class="program-name">
                    <strong>Kusursuz Kiracı</strong>
                </div>
                <div class="program-desc">
                    Mona bir sabah işe gitmek üzere evden çıkarken uzun süredir çekişmeli olduğu ev sahibiyle kavga eder. İşe vardığında, dün gece şehirde bir süredir olduğu gibi yine bir ev kundaklaması vakası yaşandığını öğrenir ve habere gönderilir. Olay yerinde raki...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Senden-Daha-Guzel/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1634" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Senden-Daha-Guzel/izle">
                <div class="program-name">
                    <strong>Senden Daha Güzel</strong>
                </div>
                <div class="program-desc">
                    
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Gizli-Sakli/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1635" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Gizli-Sakli/izle">
                <div class="program-name">
                    <strong>Gizli Saklı</strong>
                </div>
                <div class="program-desc">
                    Naz (Sinem Ünsal) polis akademisinden yeni mezun, korumacı bir karakter olan annesi ve dayısıyla birlikte yaşamaktadır. Tarık Koşuoğlu (Tardu Flordun) isimli bir mafya babasının peşinde olan polis teşkilatı, Naz’ı ve deli dolu polis memuru Pamir’i (H...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Evlilik-Hakkinda-Her-Sey/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1610" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Evlilik-Hakkinda-Her-Sey/izle">
                <div class="program-name">
                    <strong>Evlilik Hakkında Her Şey</strong>
                </div>
                <div class="program-desc">
                    Başarılı bir boşanma avukatı olan Azra Günay, işinin duayeni olan annesi Çolpan Cevher ve dik başlı kardeşi Sanem Cevher ile İstanbul’un tanınmış ve nüfuzlu insanlarının davalarına bakmaktadır. Küçük kız kardeşi Güneş ise anne ve ablalarının aksine h...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Gulumse-Kaderine/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1633" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Gulumse-Kaderine/izle">
                <div class="program-name">
                    <strong>Gülümse Kaderine</strong>
                </div>
                <div class="program-desc">
                    Eda ve Yaren Bursa'da yetiştirme yurdunda büyümüş, birbirlerini kardeş olarak kabul ederek kimsesizliklerini avutmaya çalışan iki genç kızdır. Yaren üniversite sınavına girip Tıp Fakültesini kazanarak doktor olmak istemektedir. Eda ise liseyi yarıda...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Ask-Mantik-Intikam/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1588" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Ask-Mantik-Intikam/izle">
                <div class="program-name">
                    <strong>Aşk Mantık İntikam</strong>
                </div>
                <div class="program-desc">
                    ‘…ayrılık da sevdaya dahil, çünkü ayrılanlar hala sevgili…’
Bitti dediğimizde biter mi sahiden aşk? Yoksa ikinci bir şansı hak eder mi?
Esra her zamanki sabahlardan birine uyandığını sanırken bir anda Ozan’ın haberleriyle, televizyondaki görüntüsüy...
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-yvF8a8YYPnCwTtSif3JzzJwtuRqxrKqw"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Son-Nefesime-Kadar/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1624" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Son-Nefesime-Kadar/izle">
                <div class="program-name">
                    <strong>Son Nefesime Kadar</strong>
                </div>
                <div class="program-desc">
                    Yıllar önce kızını büyük bir felaket sonrası kaybetmiş acılı bir annedir Mihri. Bu kayıp sonrası aldığı radikal bir karar yüzünden ailesi dağılmış, oğlu ve kocası tarafından terk edilmiş, tek başına kalmıştır. Ancak Mihri yılmamış, kızından geriye ka...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kanunsuz-Topraklar/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1609" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kanunsuz-Topraklar/izle">
                <div class="program-name">
                    <strong>Kanunsuz Topraklar</strong>
                </div>
                <div class="program-desc">
                    1939 yılında kömür şehri Zonguldak’ta bir kasabada madenci Davut (Uğur Güneş), kardeşleri ve ana-babasıyla mütevazı bir hayat sürmektedir. Madenin sahibi Paşazade Malik Bey (Murat Daltaban)adında zengin bir adamdır. Yağmurun çok yağdığı bir g...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Elkizi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1608" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Elkizi/izle">
                <div class="program-name">
                    <strong>Elkızı</strong>
                </div>
                <div class="program-desc">
                    "Gemi su almaya başladığı gün, ilk "Elkızı"nı attılar aşağı.."
Biz çok mutlu bir aileydik. Annem babamın gözünün bebeğiydi. Gelini değil kızıydı babaannemin. Bir tanesiydi bütün sülalenin. Sonra bir gün babam başka bir kadını sevdi. Doğurduğu çocuğa...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Elbet-Bir-Gun/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1601" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Elbet-Bir-Gun/izle">
                <div class="program-name">
                    <strong>Elbet Bir Gün</strong>
                </div>
                <div class="program-desc">
                    Kapadokya’nın bir kasabasında, metruk bir gecekondunun bodrumunda aynı aileye ait beş ceset bulunur. Bundan on beş yıl önce öldürülen ailenin geride kalan iki ferdi Feride (Sinem Ünsal) ve Nesime (Şebnem Bozoklu) ise kayıptırlar. Gazeteci Murat Güven...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Misafir/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1614" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Misafir/izle">
                <div class="program-name">
                    <strong>Misafir</strong>
                </div>
                <div class="program-desc">
                    Geçmişinden kaçan Gece’nin yeni hayatı, eskisini bitirmeye çalıştıktan sonra başlar. Gözlerini hastanede açtığında bunu bir fırsata çevirir ve doktorları hafızasını kaybettiğine inandırır.
Başarılı bir polis olan Erdem, kimliği belirlenemeyen bu zav...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Yalancilar-ve-Mumlari/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1611" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Yalancilar-ve-Mumlari/izle">
                <div class="program-name">
                    <strong>Yalancılar ve Mumları</strong>
                </div>
                <div class="program-desc">
                    Elif (Ceren Moray), kocasını bir tekne kazasında kaybetmiş ve bu kaybı halen kabullenememiştir. Gelen cevapsız aramalar kocasının hayatta olduğunu düşünmesine sebep oluyordur. Elif’e en yakın arkadaşları Ceyda (Elçin Sangu), Meliha (Şafak Pekdemir) v...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Son-Yaz/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1571" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Son-Yaz/izle">
                <div class="program-name">
                    <strong>Son Yaz</strong>
                </div>
                <div class="program-desc">
                    Canan’ın ölümünden sonra hiçbir şey eskisi gibi değildir. Kara ailesi ayrı yerlere savrulmuştur. Canan’ın ölümünü kaldıramayan Selim inzivaya çekilmiştir. Akgün ise kaçak durumdadır. Onları tekrar bir araya getirecek kişi ise Sare Akay olacaktır. Sar...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Uzak-Sehrin-Masali/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1602" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Uzak-Sehrin-Masali/izle">
                <div class="program-name">
                    <strong>Uzak Şehrin Masalı</strong>
                </div>
                <div class="program-desc">
                    “Hepimiz kendi masallarımızın kurbanıyız...”
O gece Demirkan Konağı’nda yaşanan deprem, Umay’ın hayatındaki bütün taşları yerinden oynattı. Yıllardır kocası Affan’ın zulmüne evlatları için katlanan Umay için bu olay, bardağı taşıran son damla olmuşt...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Sen-Cal-Kapimi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1536" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Sen-Cal-Kapimi/izle">
                <div class="program-name">
                    <strong>Sen Çal Kapımı</strong>
                </div>
                <div class="program-desc">
                    Serkan ve Eda, Serkan'ın kanser tedavisi sırasında zorlu günler yaşarlar. Zaten hastalık takıntısı olan Serkan, hastalığı atlattıktan sonra bambaşka bir adama dönüşür. Bağlanma korkusu gelişir, asla bir çocuk istemediğini söyler, evlilik tarihini sür...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kefaret/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1563" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kefaret/izle">
                <div class="program-name">
                    <strong>Kefaret</strong>
                </div>
                <div class="program-desc">
                    Müzik öğretmeni Zeynep (Nurgül Yeşilçay) beş yıl önce iki küçük çocuğu ve doktor kocası Ahmet( Yurdaer Okur) ile yeni tayin oldukları kasabadaki güzel evlerine taşınırken geleceklerinin o yaz sabahı gibi mükemmel olacağından emindi. Doğum gününde bir...
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-EF8hKGEDOzgaVEXdHw6zZ3D36nKR0do8"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Savasci/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1167" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Savasci/izle">
                <div class="program-name">
                    <strong>Savaşçı</strong>
                </div>
                <div class="program-desc">
                    Savaşçı, dünyanın en zor şartlarında görev yapan, akla gelebilecek tüm güçlüklere katlanan adanmış kahramanların, “Bordo Berelilerin” hikayesi.
“Söz konusu vatansa, gerisi teferruattır..!”
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Mucize-Doktor/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1495" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Mucize-Doktor/izle">
                <div class="program-name">
                    <strong>Mucize Doktor</strong>
                </div>
                <div class="program-desc">
                    Başrolünü Taner Ölmez’in üstlendiği, kadrosunda Onur Tuna, Sinem Ünsal, Seda Bakan, Hazal Türesan, Murat Aygen, Fırat Altunmeşe, Hakan Kurtaş, Hayal Köseoğlu, Bihter Dinçel, Korhan Herduran, Merve Bulut VE Reha Özcan gibi birbirinden başarılı oyuncul...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Masumiyet/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1574" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Masumiyet/izle">
                <div class="program-name">
                    <strong>Masumiyet</strong>
                </div>
                <div class="program-desc">
                    Evli ve iki çocuk annesi Bahar’ın (Deniz Çakır) hayatı, 19 yaşındaki kızının yanlış bir adama aşık olmasıyla değişir. Kızı Ela’nın (İlayda Alişan) ilk aşkı, yaşıtı bir üniversite öğrencisi değil babasının, başkasıyla evlenmek üzere olan 35 yaşındaki...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Baraj/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1511" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Baraj/izle">
                <div class="program-name">
                    <strong>Baraj</strong>
                </div>
                <div class="program-desc">
                    1977 yapımlı, başrollerinde Türkan Şoray ve Tarık Akan’ın oynadığı “Baraj” isimli filmin dizi uyarlaması olarak izleyici karşısına çıkacak olan yapımda Nazım’ın (Feyyaz Duman), internette bir arkadaşlık sitesinde Nehir’le (Biran Damla Yılmaz) tanışma...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Zumruduanka/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1508" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Zumruduanka/izle">
                <div class="program-name">
                    <strong>Zümrüdüanka</strong>
                </div>
                <div class="program-desc">
                    Başrollerini&nbsp;Alp Navruz&nbsp;ve&nbsp;Ceren Yılmaz’ın paylaştığı, “Zümrüdüanka”, imkansız bir aşkın duygu yüklü hikayesini izleyiciyle buluşturuyor.&nbsp;
Çekimleri Kapadokya’nın masalsı dünyasında yapılan “Zümrüdüanka” başarılı oyuncu kadrosu, güçlü aşk hikayesi v...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Cocukluk/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1568" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Cocukluk/izle">
                <div class="program-name">
                    <strong>Çocukluk</strong>
                </div>
                <div class="program-desc">
                    “Çocukluk” dizisinde; tüm hayatını geride bırakıp Ali Kaan Umut Evi’ni açan Mahir Boztepe (Erdal Beşikçioğlu), ilk günden beri evine gelen her çocuğun doğru aileyi bulmasını sağlamıştır. Ali Kaan Umut Evi’nde aynı odayı paylaşan Mavi (Beren Gökyıldız...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Ogretmen/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1449" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Ogretmen/izle">
                <div class="program-name">
                    <strong>Öğretmen</strong>
                </div>
                <div class="program-desc">
                    Hikayenin baş kahramanı olan fizik öğretmeni Akif Erdem; öğrencilerine bir “insanlık dersi” vermek istemektedir. Yalnız Akif Öğretmen; bildiğimiz, alıştığımız öğretmenlerden daha farklı bir ders anlatma yöntemi kullanmaktadır.Akif Erdem, bu son dersi...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Bay-Yanlis/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1533" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Bay-Yanlis/izle">
                <div class="program-name">
                    <strong>Bay Yanlış</strong>
                </div>
                <div class="program-desc">
                    Özgür (Can Yaman); zengin ancak salaş bir hayat süren, aşka inanmayan restoran-bar sahibidir. Ezgi (Özge Gürel) ise; artık yanlış ilişkilerden yorulmuş ve düzgün bir ilişki yaşayıp, evlenmeye kararlıdır. Ezgi’nin ilişki konularında başarılı olmadığın...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Ferhat-ile-Sirin/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1498" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Ferhat-ile-Sirin/izle">
                <div class="program-name">
                    <strong>Ferhat ile Şirin</strong>
                </div>
                <div class="program-desc">
                    Ahşap işleri yapan sıradan bir marangoz olan Ferhat’ın yolu, hiç ummadığı bir anda aşka, zengin ve karanlık bir dünyaya uzanır. Küçük atölyesinden Kapalı Çarşı’nın tarihi dükkanlarına adım atan Ferhat’ın yolu Karalı Köşk’üne çıkar. Hayatın onu sürükl...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Her-Yerde-Sen/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1476" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Her-Yerde-Sen/izle">
                <div class="program-name">
                    <strong>Her Yerde Sen</strong>
                </div>
                <div class="program-desc">
                    Adına ister kader deyin ister hayat, başınıza gelen en iyi şeyler çoğu zaman içinden çıkılmaz sorunların arkasına gizlenir. Aynı evde hak iddia eden ve keçi gibi inatçı olan Demir (Furkan Andıç) ile Selin (Aybüke Pusat) birlikte yaşamak zorunda kalır...
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-Z49KeAJPMaKb3P0aIc05Xf9uGJ9bDbQT"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Sana-Bir-Sir-Verecegim/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/38" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Sana-Bir-Sir-Verecegim/izle">
                <div class="program-name">
                    <strong>Sana Bir Sır Vereceğim</strong>
                </div>
                <div class="program-desc">
                    Hiçbir sır sonsuza kadar saklanamaz!Kızı esrarengiz adamlar tarafından kaçırılmış bir anne... Eşini kaybetmiş, oğlunu kötülüklerden korumayı kendine görev edinmiş bir baba... Ve birbirinden farklı olağanüstü güçlere sahip beş çocuk.Onlar bambaşka hay...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Vurgun/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1387" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Vurgun/izle">
                <div class="program-name">
                    <strong>Vurgun</strong>
                </div>
                <div class="program-desc">
                    Aşık olduğu karısı Reyhan ve oğluyla beraber çok mutlu bir hayat yaşayan Kemal Vardar, oğlunun ikinci yaş gününü kutladıkları gece aklına takılan bir iş için uyanır ve sahip olduğu fabrikaya gider. Ancak o andan itibaren onun ve etrafındaki herkesin...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Bir-Deli-Ruzgar/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1364" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Bir-Deli-Ruzgar/izle">
                <div class="program-name">
                    <strong>Bir Deli Rüzgar</strong>
                </div>
                <div class="program-desc">
                    Melike Candan, ağır bedeller ödeyerek en dipten en zirveye tırmanmış, 70’lerde ve 80’lerde assolistlik mertebesine ulaşmış bir yıldızdır. Melike’nin bugünkü yaşamı ise bambaşkadır. Bir gün tuvaletçi olarak çalıştığı barda tıpkı kendisinin ilk günleri...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/4N1K/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1325" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/4N1K/izle">
                <div class="program-name">
                    <strong>4N1K İlk Aşk</strong>
                </div>
                <div class="program-desc">
                    Yaprak, çocukluktan beri kızlar dünyasından uzak, yanı başındaki dört adamdan oluşan rengarenk bir dünya kurmuştur kendine. Bir gün bu dünya, gizemli bir biçimde hayatına giren Barış’ın oyunlarıyla değişir. Bu değişim, onu kendisine ve kızlar dünyası...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Adi-Zehra/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1310" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Adi-Zehra/izle">
                <div class="program-name">
                    <strong>Adı: Zehra</strong>
                </div>
                <div class="program-desc">
                    Berlin’de; tutucu bir Türk ailesinin kızı olarak dünyaya gelen 23 yaşındaki Zehra Şimşek’in yaşadıkları ne planlanabilir ne de yeryüzündeki herhangi biri, onun yaşadıklarını hayal edebilirdir! Dizi, Göçmen Türk kızı Zehra’nın Berlin’deki yoksul ve ba...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Bir-Mucize-Olsun/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1330" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Bir-Mucize-Olsun/izle">
                <div class="program-name">
                    <strong>Bir Mucize Olsun</strong>
                </div>
                <div class="program-desc">
                    Çukurdere'nin çamurlu sokaklarında büyüyen Damla onu yetiştiren Maksude'nin yanında evlatlık gibi değil hizmetçi gibi bir yaşam sürmektedir. Sefalet ve umutsuzluk içinde geçen günlerden bir gün kapılarını Yiğit adında genç bir avukat çalar. Gerçek an...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Sevkat-Yerimdar/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/75" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Sevkat-Yerimdar/izle">
                <div class="program-name">
                    <strong>Şevkat Yerimdar</strong>
                </div>
                <div class="program-desc">
                    Özgür bir insan nasıl yaşayacağını hiç düşünmez; çünkü nasıl yaşanmayacağını zaten bilir. Gerisi hikayedir.
Asi ruhlu bir mahalle delikanlısıdır Şevkat. Adaletsizliğe, haksızlığa ve ayırımcılığa zerre tahammülü yoktur. En büyük sorunu da öfke kontro...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kalbimdeki-Deniz/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/74" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kalbimdeki-Deniz/izle">
                <div class="program-name">
                    <strong>Kalbimdeki Deniz</strong>
                </div>
                <div class="program-desc">
                    
Deniz bir kadının isteyebileceği her şeye sahiptir. Fakat mutlu ve refah hayatı bir gün kocası hiçbir iz bırakmadan ortadan kaybolunca tepetaklak olur. İki çocuğu ve yaşlı babasıyla çaresiz bir halde ortada kalan Deniz ile ona gerçek aşkı tattıraca...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Nerdesin-Birader/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1293" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Nerdesin-Birader/izle">
                <div class="program-name">
                    <strong>Nerdesin Birader</strong>
                </div>
                <div class="program-desc">
                    "Şu hayatta isteyeceği en son şey ikizinin yerine polis olmaktı."
Yunus, Hollywood da tutunamayıp şansını Bollywood'da denemeye çalışan başarısız bir aktör, ikizi Yiğit ise büyük bir suç örgütünün peşinde başarılı bir komiserdir. Bir dizi talihsizli...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kayitdisi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1277" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kayitdisi/izle">
                <div class="program-name">
                    <strong>Kayıtdışı</strong>
                </div>
                <div class="program-desc">
                    İstanbul... 20 milyonluk bu şehirde suç da bitmez günah da. Birileri günah işler, birileri de o günahları örter. Başkalarının yalanlarını örtmekten kendi gerçeğini unutan Ali Kemal, aşık olunca kendi gerçeğiyle yüzleşecek.
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-fNgI6sblHzz0QWDKZ9E6BKParhW5J3Gb"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/No-309/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/68" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/No-309/izle">
                <div class="program-name">
                    <strong>No: 309</strong>
                </div>
                <div class="program-desc">
                    Dedesinden kalan mirası alabilmek ve şirketin başına geçebilmek için evlenmesi ve de çocuk sahibi olması gereken Onur, annesinin zoruyla bir randevuya gider. Lale de annesinin ayarladığı randevu için aynı mekandadır. Birbirlerini tanımayan Lale ve On...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Deli-Gonul/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1215" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Deli-Gonul/izle">
                <div class="program-name">
                    <strong>Deli Gönül</strong>
                </div>
                <div class="program-desc">
                    Senaryosu; Rahşan Çiğdem İnan, Barış Pirhasan ve Selim Demirdelen’e ait “Deli Gönül”ün yönetmen koltuğunda Selim Demirdelen ve Berat Özdoğan oturuyor. Başrollerini Murat Ünalmış ve Tuvana Türkay’ın paylaştığı, oyuncu kadrosunda Çiğdem Batur, Ogün Kap...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Bu-Sayilmaz/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1260" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Bu-Sayilmaz/izle">
                <div class="program-name">
                    <strong>Bu Sayılmaz</strong>
                </div>
                <div class="program-desc">
                    Ve karşınızda ekranların en traji komik ailesi: Sayılmazlar. Abla Melek Sayılmaz, abi Armağan Sayılmaz, ve kız kardeşler Biricik ve Cansın Sayılmaz’dan oluşan ailemiz İstanbul’da oldukça sıkıcı bir hayat sürdürmektedir. Melek Sayılmaz’ın hayattaki te...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Coban-Yildizi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1171" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Coban-Yildizi/izle">
                <div class="program-name">
                    <strong>Çoban Yıldızı</strong>
                </div>
                <div class="program-desc">
                    Çoban Yıldızı, Niğde’de doğmuş büyümüş, güzeller güzeli Zühre’nin istemediği halde Kapadokya’da yaşayan, bölgenin zengin ve güçlü adamlarından Fikret Karakaya ile evlendirilmek istemesi ile başlar. Zühre, gücü kudreti elinde tutan Fikret Karakaya’nın...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/O-Hayat-Benim/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/48" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/O-Hayat-Benim/izle">
                <div class="program-name">
                    <strong>O Hayat Benim</strong>
                </div>
                <div class="program-desc">
                    Konu hayatın ve aşkınsa, kadere asla teslim olma...
&nbsp;
O Hayat Benim'de küllerinden doğan aşklara ve hayata yenilmeden tutunma mücadelelerine hep birlikte tanık oluyoruz. Sırlar bir bir ortaya çıkmaya başlamıştır, artık işler kimsenin umduğu gibi gi...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Dayan-Yuregim/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/79" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Dayan-Yuregim/izle">
                <div class="program-name">
                    <strong>Dayan Yüreğim</strong>
                </div>
                <div class="program-desc">
                    “Bir gün gelir… Aslın gider, suretinle kalırsın ortada…”
Başrollerini Ece Uslu, Cansel Elçin, Berk Atan ve Nilay Deniz’in paylaştığı, yönetmenliğini Deniz Çelebi Dikilitaş’ın üstlendiği ‘Dayan Yüreğim’ Ece Uslu, Cansel Elçin, Berk Atan ve Nilay Deni...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kirlangic-Firtinasi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/80" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kirlangic-Firtinasi/izle">
                <div class="program-name">
                    <strong>Kırlangıç Fırtınası</strong>
                </div>
                <div class="program-desc">
                    Evlilik dışı hamile kalan Ülfet, doğum sırasında oğlunu ağabeyi Kudret’e vermek zorunda kalır. Bu sırada Kudret’in eşi Meryem de doğum yapar. Kudret, Ülfet’in oğlunu da kendi çocuğunun yanına koyar ve çocukların ikiz doğduğunu söyler. Aradan yıllar g...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Esaretim-Sensin/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1170" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Esaretim-Sensin/izle">
                <div class="program-name">
                    <strong>Esaretim Sensin</strong>
                </div>
                <div class="program-desc">
                    Ankara’nın ünlü ailesi Kırımlıların küçük kızı Yasemin, hastalıklı bir tutkuyla aşık olduğu sevgilisi tarafından terk edildikten sonra intihara teşebbüs eder. Geçirdiği kazanın ardından bir bitki gibi yaşamaya mahkum olan Yasemin çevreden gizli bir k...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Umuda-Kelepce-Vurulmaz/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/78" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Umuda-Kelepce-Vurulmaz/izle">
                <div class="program-name">
                    <strong>Umuda Kelepçe Vurulmaz</strong>
                </div>
                <div class="program-desc">
                    Başka şehirler, başka hayatlar ve farklı suçlar işlemiş lise çağındaki yedi mahkum gencin hayatları, kendilerine sunulan okuma hakkıyla bir anda tamamen değişir. Milletvekili bir baba ve çok zengin bir annenin oğlu olan Onur için başlatılan bir proje...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Nolur-Ayrilalim/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1165" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Nolur-Ayrilalim/izle">
                <div class="program-name">
                    <strong>N'olur Ayrılalım</strong>
                </div>
                <div class="program-desc">
                    Yapımcılığını Osman Sınav’ın, yönetmenliğini ise oğlu Yusuf Ömer Sınav’ın üstlendiği N'olur Ayrılalım'ın başrollerinde Gürgen Öz, Nilay Duru, Aras Aydın, Nilperi Şahinkaya gibi genç ve sevilen oyuncular bulunuyor. Birlikte olup ayrıldığı her kızın, h...
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-LuYRqDoiUpGSyHryBgBQIIZ87IBq24F1"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Familya/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/73" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Familya/izle">
                <div class="program-name">
                    <strong>Familya</strong>
                </div>
                <div class="program-desc">
                    “Familya”, 2002 yılında Dünya Kupası’daki Türkiye- Senegal maçında İlhan Mansız’ın attığı golle, herkes büyük bir sevinç yaşarken, parçalanan Beyoğlu ailesinin ve baba Yaşar Beyoğlu’nun (Uğur Yücel) yıllar sonra aldığı bir haberle yeniden ailesini bi...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kordugum/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/63" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kordugum/izle">
                <div class="program-name">
                    <strong>Kördüğüm</strong>
                </div>
                <div class="program-desc">
                    Araba takıntılı iki zengin işadamının yolları idealist bir çocuk doktoruyla kesişir. Denkleme aşk girer ve hayatları sonsuza dek değişir.
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Ruzgarin-Kalbi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/71" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Ruzgarin-Kalbi/izle">
                <div class="program-name">
                    <strong>Rüzgarın Kalbi</strong>
                </div>
                <div class="program-desc">
                    “Rüzgarın Kalbi” dizisi genç kadrosu ve aşkı yaşayan herkesin içini titretecek özgün hikayesi ile ekranların vazgeçilmezleri arasında yer aldı. Hikayenin senaryosu ile dalgalar taze bir rüzgarla kıyılara vurup, aşka yeniden hayat vermeye hazırlanıyor...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Karagul/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/35" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Karagul/izle">
                <div class="program-name">
                    <strong>Karagül</strong>
                </div>
                <div class="program-desc">
                    Baran’ın oğlu olduğunu gerçeğini öğrenen Ebru, oğlunu geri alabilmek için kıyasıya bir savaşa girer. Artık Ebru’nun tek bir hedefi vardır, dört çocuğunu da alıp Halfeti’den gidebilmek.&nbsp; Ancak başta Kendal ve Narin olmak üzere karşısına çıkan engeller...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Hayat-Sevince-Guzel/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/67" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Hayat-Sevince-Guzel/izle">
                <div class="program-name">
                    <strong>Hayat Sevince Güzel</strong>
                </div>
                <div class="program-desc">
                    Yaptıkları dolandırıcılıklar yüzünden İstanbul’dan apar topar kaçan Göçer ailesi, arkalarında bıraktıkları belalılardan olabildiğince uzaklaşmaya çalışırken, kendilerini Ege’de bulurlar. Köyün hırçın güzeli Zarife’nin otlattığı koyunlar yüzünden kaza...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Unutma-Beni/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/4" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Unutma-Beni/izle">
                <div class="program-name">
                    <strong>Unutma Beni</strong>
                </div>
                <div class="program-desc">
                    Masum gözyaşları, imkansız aşkları ıslatır.Türkiye'de bir ilke imza atarak, 7. sezonuna başlayacak günlük dizi Unutma Beni, hayatlarındaki insanlara yardım eli uzatmak uğruna, aşklarını bir türlü gönüllerince yaşayamayan Ali ve İlkay'ı, her zamankind...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Ask-Yeniden/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/57" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Ask-Yeniden/izle">
                <div class="program-name">
                    <strong>Aşk Yeniden</strong>
                </div>
                <div class="program-desc">
                    Sevdiklerini, tüm ailesini, hayatını geride bırakarak, aşık olduğu Ertan’ın peşinden Amerika’ya kaçan Zeynep, elinde hayal kırıklıkları ve bebeğiyle Türkiye’ye geri döner. Diğer tarafta Amerika’ya eğitim için giden Fatih’in de hayal kırıklıkları ile...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kalbim-Yangin-Yeri/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/66" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kalbim-Yangin-Yeri/izle">
                <div class="program-name">
                    <strong>Kalbim Yangın Yeri</strong>
                </div>
                <div class="program-desc">
                    Geçmiş, Geleceğin İzini Sürer...Leyla (Hande Soral), kız kardeşi Sevda’nın (Ece Çeşmioğlu) düğünü için bir süre önce ayrıldığı baba evine dönmüştür. Ertesi gün yapılacak düğün töreninden sonra ise evden temelli ayrılacak, tüm sırları ve hayatının erk...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Cifte-Saadet/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/64" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Cifte-Saadet/izle">
                <div class="program-name">
                    <strong>Çifte Saadet</strong>
                </div>
                <div class="program-desc">
                    Hikayesinin başlangıcı 2003 yılına uzanan Çifte Saadet, Konyalı mutlu bir çiftin hayatını ve büyük değişimlerini ele alıyor. Metin (Fikret Kuşkan) ve Perihan (Şebnem Bozoklu) genç yaştan beri arkadaş olan ve sonunda evlenip iki çocuk sahibi olan, iş...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Inadina-Ask/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/59" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Inadina-Ask/izle">
                <div class="program-name">
                    <strong>İnadına Aşk</strong>
                </div>
                <div class="program-desc">
                    Erkekler inatçı, kadınlar inatçı,aşk hepsinden inatçı.İnadına Aşk; içinde aşk, sevgi, nefret ve oyun dolu bir romantik komedi dizisi. Her şey Karadenizli bir ailenin kızı olan Defne’nin, Aras Teknoloji’nin yakışıklı ve çapkın patronu Yalın’ın yanında...
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-R8Slyen65HaKlLRgSzRntCnwusB8TeF2"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kiraz-Mevsimi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/50" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kiraz-Mevsimi/izle">
                <div class="program-name">
                    <strong>Kiraz Mevsimi</strong>
                </div>
                <div class="program-desc">
                    Öykü, tekstil ve moda tasarımı bölümü öğrencisi, akıllı ve güzel bir kızdır. En büyük hayali başarılı bir moda tasarımcısı olmaktır. Bu konuda kendisine örnek aldığı ünlü modacı Önem Dinçer’e çizimlerini ulaştırmak için çok uğraşır. Öykü, en sonunda...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Adi-Mutluluk/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/58" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Adi-Mutluluk/izle">
                <div class="program-name">
                    <strong>Adı Mutluluk</strong>
                </div>
                <div class="program-desc">
                    Kumsal’ın babasından gizli İstanbul’da bir üniversite kazanmasıyla İzmir’den İstanbul’a uzanan bir özgürlük yolculuğu hikayesi; Adı Mutluluk!Babasını karşısına aldığı gün tanıştığı Batu sayesinde mutluluğu aramak için İstanbul’a gitme kararı veren Ku...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Sen-Benimsin/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/60" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Sen-Benimsin/izle">
                <div class="program-name">
                    <strong>Sen Benimsin</strong>
                </div>
                <div class="program-desc">
                    Bursa’nın zengin ailelerinden bir olan Yenilmezler’in veliahdı Ejder (Gökhan Keser) ve annesinin baskısıyla yetişmiş, başarılı bir piyanist olan Nağme’nin (Rüveyda Öksüz) ilk görüşte başlayan aşklarının çiftliğe taşınmasıyla yaşanan kaosunu konu alan...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Sehrin-Melekleri/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/61" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Sehrin-Melekleri/izle">
                <div class="program-name">
                    <strong>Şehrin Melekleri</strong>
                </div>
                <div class="program-desc">
                    İstanbul’da halk arasında İstanbul emniyetinin başarısızlığına dair oluşan kanaat; emniyet mensuplarını, suçun kalbine inecek genç bir ekip kurmaya iter. Bunun için emniyetin efsane amirlerinden Fırtına Cemal görevlendirilir. Cemal, kural tanımaz ama...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Zengin-Kiz-Fakir-Oglan/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/62" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Zengin-Kiz-Fakir-Oglan/izle">
                <div class="program-name">
                    <strong>Zengin Kız Fakir Oğlan</strong>
                </div>
                <div class="program-desc">
                    Zengin Kız Fakir Oğlan, iyilik ve doğruluğun kazandığı, aile içi dayanışmanın ve yardımlaşmanın yüceltildiği bir dizi olarak, "iyilik yap iyilik bul" mottosuna sahip çıkacak. Sınıfsal farklılıkların insanları ayrıştıran bir şey olmadığının altını çiz...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Kadim-Dostum/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/53" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Kadim-Dostum/izle">
                <div class="program-name">
                    <strong>Kadim Dostum</strong>
                </div>
                <div class="program-desc">
                    Mahsun Kırmızıgül'ün yazdığı bir hikayeden uyarlanan Kadim Dostum'un, yapımcılığını Boyut Film, Mahsun Kırmızıgül üstlenmektedir. Zamanın durduğu şehir Mardin'den sıcak bir aile hikayesi geliyor. Masalsı şehrin efsane telkaricisi Sami Usta'nın çırakl...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Emanet/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/54" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Emanet/izle">
                <div class="program-name">
                    <strong>Emanet</strong>
                </div>
                <div class="program-desc">
                    Emanet unutulmaz Türk filmlerinden "Askerin Dönüşü" filminin televizyona uyarlamasıdır. Emanet, geleneğin, kanunun, askerin ve kan bağının kutsal olduğu Anadolu'dan imkansız bir aşkın hikayesini getiriyor ekranlara.Jandarma çevirmesinde masum bir ada...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Deniz-Yildizi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/2" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Deniz-Yildizi/izle">
                <div class="program-name">
                    <strong>Deniz Yıldızı</strong>
                </div>
                <div class="program-desc">
                    Sırlarla dolu hayatların hikayesi...Gerçeklerin ortaya çıkmasıyla hesaplaşmalar, intikam planları başlıyor ve yeni sırlar, yeni oyunlar katılıyor Deniz Yıldızı’na. Pişmanlıklar, kırgınlıklar, kıskançlıklar, çatışmalar ve her şeyi alt üst eden aşklar.
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Not-Defteri/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/49" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Not-Defteri/izle">
                <div class="program-name">
                    <strong>Not Defteri</strong>
                </div>
                <div class="program-desc">
                    Mahir Soysal, ilk ders günü için Dersaadet Lisesi’nin kapısından adımını atarken aynı zamanda içine sığınabileceği yeni bir hayat arayışındadır. Geçmişte bütün meslektaşlarının umutsuz vaka olarak gördükleri problemli öğrencilere yol gösterip onları...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Ruhumun-Aynasi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/52" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Ruhumun-Aynasi/izle">
                <div class="program-name">
                    <strong>Ruhumun Aynası</strong>
                </div>
                <div class="program-desc">
                    Güzel, akıllı, başarılı psikiyatrist Elçin Aksoy, 35. doğum gününde hayatını sil baştan kurmasını gerektirecek bir dizi olay yaşar. Tüm bunlar, cafcaflı ama içi boş hayatını sorgulamasına yol açar ve sekreteri Gülpare’nin yaşadığı&nbsp; mahallede yeni bir...
                </div>
            </a>
        </div>
    </div>    
<section class="ads"><div class="ad masthead"><div class="none-lazyload-ads" id="div-gpt-ad-ajax-masthead-cF7GUPgGi30aw1atr8cwI3IAjmQ6eqRY"></div></div></section>
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Benim-Hala-Umudum-Var/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/46" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Benim-Hala-Umudum-Var/izle">
                <div class="program-name">
                    <strong>Benim Hala Umudum Var</strong>
                </div>
                <div class="program-desc">
                    Umut, İstanbul'un kendine ancak yeten, gösterişsiz semtlerinden birinde, annesi, kız kardeşi, üvey babası ve üvey babasının 3 yetişkin çocuğuyla birlikte yaşayan, 23 yaşlarında bir kızdır. Umut, üvey kardeşleriyle birlikte büyümenin tüm sıkıntılarını...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Lale-Devri/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/1" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Lale-Devri/izle">
                <div class="program-name">
                    <strong>Lale Devri</strong>
                </div>
                <div class="program-desc">
                    Bazen mutluluk ve acının yolları kesişir!
Tüm engellere rağmen Çınar, Toprak'ın kalbini tekrar kazanmak, yeni bir sayfa açmak için tüm varlığıyla savaşacak. Necip, yaşanan kayıplar ve kaybedilen aşklarla dolu hayatında, ailesinin başında dimdik durm...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Fatih-Harbiye/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/40" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Fatih-Harbiye/izle">
                <div class="program-name">
                    <strong>Fatih Harbiye</strong>
                </div>
                <div class="program-desc">
                    Geleneksellikle modernlik arasına sıkışmış Fatihli genç bir kız, Neriman’ın ilginç hayat hikâyesi... Bir yanda Neriman’ın Fatih’te birlikte büyüdüğü, çocukluk aşkı Şinasi… Diğer yanda modern İstanbul’un varlıklı üst sınıfından yakışıklı Macit… Çok fa...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Babam-Sinifta-Kaldi/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/37" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Babam-Sinifta-Kaldi/izle">
                <div class="program-name">
                    <strong>Babam Sınıfta Kaldı</strong>
                </div>
                <div class="program-desc">
                    Liseyi yeni bitiren Yağmur kazandığı üniversite sayesinde özgürlüğe adım attığını sandığı anda, aftan yararlanan babası ile birlikte okuyacağını öğrenir ve bütün hayalleri suya düşer. Oysa babası Erman için durum farklıdır. Erman hem üniversite tahsi...
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Harem/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/27" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Harem/izle">
                <div class="program-name">
                    <strong>Harem</strong>
                </div>
                <div class="program-desc">
                    Gani Müjde ve Tükenmez Kalem ekibinden muhteşem komedi... Mezopotamya’da bir halk; Basurlular. Basur sarayında, halkın can-ı gönülden sevdiği Sultan Küçük Esat. Birbirinden değişik, renkli kişiliklere sahip kadınlardan oluşan Küçük Esat’ın Harem’i....
                </div>
            </a>
        </div>
    </div>    
    <div class="list-item">                           
        <div class="list-item-image">
            <a href="https://www.nowtv.com.tr/Yer-Gok-Ask/izle"><img class="" src="https://www.nowtv.com.tr/i/thumbnail/3" alt=""></a>                                
        </div>
        <div class="list-item-meta">
            <a href="https://www.nowtv.com.tr/Yer-Gok-Ask/izle">
                <div class="program-name">
                    <strong>Yer Gök Aşk</strong>
                </div>
                <div class="program-desc">
                    Farklı karakterlerdeki iki kız kardeş aynı adama sevdalanırlar. Biri uysal ve hüzünlü, diğeri ise gururlu ve hırçındır. Ne kardeşinden kaçabilir insan, ne de yüreğindeki aşktan...
"Tutkuyla yaşayan aşka seyirci kalamaz, kararsız kalan kendi kaderini...
                </div>
            </a>
        </div>
    </div>    
</div>]
"""

def extract_data_to_json():
    # Not: Sen yukarıdaki metni verdiğin için ben burada BeautifulSoup ile o metni işliyorum
    soup = BeautifulSoup(raw_html, 'html.parser')
    items = soup.select('.list-item')
    
    series_db = {}
    base_url = "https://www.nowtv.com.tr"

    for item in items:
        name_el = item.find('strong')
        link_el = item.find('a', href=True)
        img_el = item.find('img')
        desc_el = item.select_one('.program-desc')

        if name_el and link_el:
            title = name_el.get_text(strip=True)
            # URL Temizleme
            href = link_el['href']
            if not href.startswith('http'): href = base_url + href
            
            # Resim Temizleme
            img = img_el.get('src') or ""
            if img and not img.startswith('http'): img = base_url + img
            
            # ID Oluşturma
            slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            
            series_db[slug] = {
                "isim": title,
                "resim": img,
                "link": href,
                "aciklama": desc_el.get_text(strip=True) if desc_el else "",
                "bolumler": [] # Bölümler daha sonra tarayıcı tarafından çekilecek
            }

    # 1. JSON OLARAK KAYDET
    with open('nowtv_data.json', 'w', encoding='utf-8') as f:
        json.dump(series_db, f, ensure_ascii=False, indent=4)
    
    print(f"✅ {len(series_db)} dizi JSON dosyasına dönüştürüldü.")
    return series_db

def create_vod_interface(data):
    # 2. JSON'DAN BESLENEN HTML ARAYÜZÜ OLUŞTUR
    json_str = json.dumps(data, ensure_ascii=False)
    
    html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8"><title>NOW TV VOD - JSON DB</title>
    <style>
        body {{ background: #0a0a0a; color: white; font-family: 'Segoe UI', sans-serif; margin: 0; }}
        .header {{ padding: 20px; background: #1a1a1a; border-bottom: 2px solid red; text-align: center; position: sticky; top: 0; z-index: 100; }}
        .container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; padding: 20px; }}
        .card {{ background: #151515; border-radius: 10px; overflow: hidden; cursor: pointer; transition: 0.3s; border: 1px solid #222; }}
        .card:hover {{ transform: scale(1.05); border-color: red; }}
        .card img {{ width: 100%; aspect-ratio: 2/3; object-fit: cover; }}
        .card-info {{ padding: 10px; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="header"><h1>NOW TV ARŞİVİ</h1></div>
    <div class="container" id="gallery"></div>

    <script>
        const database = {json_str};
        const gallery = document.getElementById('gallery');

        Object.keys(database).forEach(id => {{
            const item = database[id];
            const div = document.createElement('div');
            div.className = 'card';
            div.innerHTML = `<img src="${{item.resim}}"><div class="card-info">${{item.isim}}</div>`;
            div.onclick = () => window.open(item.link, '_blank');
            gallery.appendChild(div);
        }});
    </script>
</body>
</html>'''

    with open('nowtv_vod.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    print("🚀 Arayüz 'nowtv_vod.html' olarak hazırlandı!")

if __name__ == "__main__":
    db = extract_data_to_json()
    create_vod_interface(db)

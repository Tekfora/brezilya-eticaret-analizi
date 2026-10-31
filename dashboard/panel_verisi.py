"""Dashboard verisini özetler ve dashboard/olist_panosu.html dosyasını üretir.

Çalıştırma (proje klasöründen):  python dashboard/panel_verisi.py

Veri, ay × eyalet × kategori küpü olarak özetlenir; tarayıcı filtreleri bu küp üzerinden hesaplar.
Her sipariş, en pahalı ürününün kategorisine atanır (sipariş sayıları iki kez sayılmasın diye).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KLASOR = Path(__file__).resolve().parent
sys.path.insert(0, str(KLASOR.parent))
import ortak  # noqa: E402

KATEGORI_TR = {
    "bed_bath_table": "Ev tekstili", "sports_leisure": "Spor ve outdoor", "furniture_decor": "Mobilya ve dekorasyon",
    "health_beauty": "Sağlık ve güzellik", "housewares": "Ev eşyaları", "auto": "Otomotiv",
    "computers_accessories": "Bilgisayar aksesuarları", "toys": "Oyuncak", "watches_gifts": "Saat ve hediyelik",
    "telephony": "Telefon ve aksesuar", "baby": "Bebek", "perfumery": "Parfüm", "stationery": "Kırtasiye",
    "fashion_bags_accessories": "Çanta ve aksesuar", "cool_stuff": "İlginç ürünler", "garden_tools": "Bahçe aletleri",
    "pet_shop": "Evcil hayvan", "unknown": "Kategorisiz", "electronics": "Elektronik",
    "construction_tools_construction": "Yapı malzemeleri", "home_appliances": "Ev aletleri",
    "luggage_accessories": "Valiz ve seyahat", "consoles_games": "Konsol ve oyun", "office_furniture": "Ofis mobilyası",
    "musical_instruments": "Müzik aletleri", "small_appliances": "Küçük ev aletleri", "home_construction": "Ev tadilatı",
    "books_general_interest": "Kitap (genel)", "fashion_shoes": "Ayakkabı", "furniture_living_room": "Oturma odası mobilyası",
    "air_conditioning": "Klima", "books_technical": "Kitap (teknik)", "fixed_telephony": "Sabit telefon",
    "home_confort": "Ev konforu", "market_place": "Pazar yeri", "food_drink": "Gıda ve içecek",
    "fashion_male_clothing": "Erkek giyim", "kitchen_dining_laundry_garden_furniture": "Mutfak ve bahçe mobilyası",
    "signaling_and_security": "Sinyalizasyon ve güvenlik", "construction_tools_safety": "İş güvenliği",
    "home_appliances_2": "Ev aletleri (2)", "costruction_tools_garden": "Bahçe yapı aletleri", "food": "Gıda",
    "drinks": "İçecek", "construction_tools_lights": "Aydınlatma", "agro_industry_and_commerce": "Tarım ve sanayi",
    "industry_commerce_and_business": "Sanayi ve ticaret", "christmas_supplies": "Yılbaşı ürünleri", "audio": "Ses sistemleri",
    "art": "Sanat", "fashion_underwear_beach": "İç giyim ve plaj", "dvds_blu_ray": "DVD ve Blu-ray",
    "furniture_bedroom": "Yatak odası mobilyası", "costruction_tools_tools": "El aletleri", "books_imported": "Kitap (ithal)",
    "small_appliances_home_oven_and_coffee": "Fırın ve kahve makinesi", "computers": "Bilgisayar", "cine_photo": "Foto ve video",
    "fashio_female_clothing": "Kadın giyim", "music": "Müzik", "party_supplies": "Parti malzemeleri",
    "arts_and_craftmanship": "El sanatları", "fashion_sport": "Spor giyim", "flowers": "Çiçek",
    "diapers_and_hygiene": "Bez ve hijyen", "la_cuisine": "Mutfak gereçleri", "furniture_mattress_and_upholstery": "Yatak ve döşeme",
    "portable_kitchen_food_processors": "Mutfak robotları", "tablets_printing_image": "Tablet ve baskı",
    "fashion_childrens_clothes": "Çocuk giyim", "home_comfort_2": "Ev konforu (2)", "pc_gamer": "Oyuncu bilgisayarı",
    "security_and_services": "Güvenlik hizmetleri", "cds_dvds_musicals": "CD ve DVD",
}
EYALET_AD = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}
ODEME = [("credit_card", "Kredi kartı"), ("boleto", "Boleto"), ("voucher", "Hediye çeki"), ("debit_card", "Banka kartı")]
KOVA_SINIR = [-np.inf, -10, -5, 0, 5, 10, 20, np.inf]
KOVA_AD = ["10+ gün erken", "5–9 gün erken", "0–4 gün erken", "1–5 gün geç", "6–10 gün geç", "11–20 gün geç", "20+ gün geç"]
KOVA_KISA = ["≤ −10", "−9…−5", "−4…0", "1–5", "6–10", "11–20", "20+"]
ILK_KATEGORI = 24


def veri_hazirla():
    t = ortak.tablolari_yukle()
    df = ortak.siparis_tablosu(t)
    koord = ortak.koordinatlar()

    ana_kat = (t["kalemler"].merge(t["urunler"][["product_id", "kategori"]], on="product_id")
               .sort_values("price", ascending=False).drop_duplicates("order_id").set_index("order_id")["kategori"])
    df["kategori"] = df["order_id"].map(ana_kat).fillna("unknown")
    odeme = (t["odemeler"].sort_values("payment_value").drop_duplicates("order_id", keep="last")
             .set_index("order_id")["payment_type"])
    df["odeme"] = df["order_id"].map(odeme)

    ciro_sira = df.groupby("kategori")["urun_tutari"].sum().sort_values(ascending=False)
    ilk = list(ciro_sira.index[:ILK_KATEGORI])
    df["kat"] = df["kategori"].where(df["kategori"].isin(ilk), "diger")
    kategoriler = ilk + ["diger"]

    aylar = sorted(df["ay"].dt.strftime("%Y-%m").unique())
    eyaletler = sorted(df["customer_state"].unique())
    df["ay_i"] = df["ay"].dt.strftime("%Y-%m").map({a: i for i, a in enumerate(aylar)})
    df["eyalet_i"] = df["customer_state"].map({e: i for i, e in enumerate(eyaletler)})
    df["kat_i"] = df["kat"].map({k: i for i, k in enumerate(kategoriler)})
    df["kova"] = pd.cut(df["gecikme_gun"], KOVA_SINIR, labels=False)
    puanli = df["review_score"].notna()
    df["puan"] = df["review_score"].fillna(0)
    df["puan_n"] = puanli.astype(int)

    sutunlar = {"n": ("order_id", "count"), "ciro": ("urun_tutari", "sum"), "kargo": ("kargo_ucreti", "sum"),
                "gec": ("gec", "sum"), "puan_t": ("puan", "sum"), "puan_n": ("puan_n", "sum"),
                "teslim_t": ("teslim_suresi", "sum")}
    for i, (kod, _) in enumerate(ODEME):
        df[f"o{i}"] = (df["odeme"] == kod).astype(int)
        sutunlar[f"o{i}"] = (f"o{i}", "sum")
    for i in range(len(KOVA_AD)):
        df[f"kn{i}"] = ((df["kova"] == i) & puanli).astype(int)
        df[f"kt{i}"] = df["puan"].where(df["kova"] == i, 0)
    for i in range(len(KOVA_AD)):
        sutunlar[f"kn{i}"] = (f"kn{i}", "sum")
    for i in range(len(KOVA_AD)):
        sutunlar[f"kt{i}"] = (f"kt{i}", "sum")

    kup = df.groupby(["ay_i", "eyalet_i", "kat_i"]).agg(**sutunlar).reset_index()
    kup["ciro"] = kup["ciro"].round(0)
    kup["kargo"] = kup["kargo"].round(0)
    kup["teslim_t"] = kup["teslim_t"].round(1)
    kolonlar = list(kup.columns)
    satirlar = [[int(x) if float(x).is_integer() else round(float(x), 1) for x in r] for r in kup.to_numpy()]

    m = df.join(koord, on="customer_zip_code_prefix").dropna(subset=["lat"])
    merkez = m.groupby("customer_state")[["lat", "lng"]].median()
    noktalar = (m.drop_duplicates("customer_zip_code_prefix")
                .assign(la=lambda d: (d["lat"] * 100).round().astype(int),
                        lo=lambda d: (d["lng"] * 100).round().astype(int))
                .drop_duplicates(["la", "lo"]))
    duz = noktalar[["la", "lo", "eyalet_i"]].to_numpy().ravel().tolist()

    return {
        "meta": {
            "aylar": aylar,
            "eyaletler": [{"kod": e, "ad": EYALET_AD.get(e, e), "lat": round(float(merkez.loc[e, "lat"]), 2),
                           "lng": round(float(merkez.loc[e, "lng"]), 2)} for e in eyaletler],
            "kategoriler": [{"kod": k, "ad": "Diğer kategoriler" if k == "diger" else KATEGORI_TR.get(k, k)}
                            for k in kategoriler],
            "odeme": [ad for _, ad in ODEME],
            "kovalar": [{"ad": a, "kisa": k, "gec": i >= 3} for i, (a, k) in enumerate(zip(KOVA_AD, KOVA_KISA))],
            "toplam_siparis": int(len(df)),
            "diger_kategori_sayisi": int(len(ciro_sira) - ILK_KATEGORI),
        },
        "kolonlar": kolonlar,
        "satirlar": satirlar,
        "noktalar": duz,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    veri = veri_hazirla()
    metin = json.dumps(veri, ensure_ascii=False, separators=(",", ":"))
    sablon = (KLASOR / "sablon.html").read_text(encoding="utf-8")
    cikti = KLASOR / "olist_panosu.html"
    cikti.write_text(sablon.replace("/*__VERI__*/null", metin), encoding="utf-8")
    print(f"{len(veri['satirlar'])} küp satırı, {len(veri['noktalar']) // 3} harita noktası, "
          f"{len(metin) / 1024:.0f} KB veri -> {cikti.name}")

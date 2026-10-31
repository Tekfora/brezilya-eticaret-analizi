"""Notebook'larda ortak kullanılan veri yükleme, temizleme ve grafik yardımcıları."""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

VERI = Path(__file__).resolve().parent
GORSEL = VERI / "gorseller"
BASLANGIC, BITIS = pd.Timestamp("2017-01-01"), pd.Timestamp("2018-09-01")

# Grafik stili: sade ızgara, tek eksen, sabit renk sırası
YUZEY, ACIK_GRI, ORTA_GRI, YAZI, SOLUK = "#fcfcfb", "#e1e0d9", "#c3c2b7", "#52514e", "#898781"
MAVI, TURUNCU, CAMGOBEGI = "#2a78d6", "#eb6834", "#1baf7a"
MAVI_RAMPA = LinearSegmentedColormap.from_list(
    "mavi", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)
# Ayrışan skala: ortalamanın altı kırmızı, üstü mavi, orta nokta nötr gri
AYRISAN = LinearSegmentedColormap.from_list(
    "ayrisan", ["#b3302f", "#e98a89", "#f0efec", "#86b6ef", "#1c5cab"]
)

YUZDE = mtick.FuncFormatter(lambda v, _: f"%{sayi(v)}")


def stil_uygula():
    GORSEL.mkdir(exist_ok=True)
    plt.rcParams.update({
        "figure.facecolor": YUZEY, "axes.facecolor": YUZEY, "savefig.facecolor": YUZEY,
        "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
        "font.size": 10, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.edgecolor": ORTA_GRI, "axes.labelcolor": YAZI, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True, "grid.color": ACIK_GRI, "grid.linewidth": 0.6,
        "xtick.color": SOLUK, "ytick.color": SOLUK, "lines.linewidth": 2, "figure.dpi": 110,
    })
    pd.set_option("display.max_columns", 50)
    pd.set_option("display.float_format", lambda v: f"{v:,.2f}")


def sayi(x, ondalik=0):
    """Sayıyı Türkçe biçimde yazar: 1234567.8 -> '1.234.568'."""
    s = f"{x:,.{ondalik}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def kaydet(fig, ad):
    fig.savefig(GORSEL / f"{ad}.png", bbox_inches="tight", dpi=150)


def tablolari_yukle():
    """Konum tablosu dışındaki tüm CSV'leri okur; ürünlere İngilizce `kategori` sütununu ekler."""
    tarih = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
             "order_delivered_customer_date", "order_estimated_delivery_date"]
    t = {
        "siparisler": pd.read_csv(VERI / "olist_orders_dataset.csv", parse_dates=tarih),
        "kalemler": pd.read_csv(VERI / "olist_order_items_dataset.csv", parse_dates=["shipping_limit_date"]),
        "urunler": pd.read_csv(VERI / "olist_products_dataset.csv"),
        "musteriler": pd.read_csv(VERI / "olist_customers_dataset.csv", dtype={"customer_zip_code_prefix": str}),
        "saticilar": pd.read_csv(VERI / "olist_sellers_dataset.csv", dtype={"seller_zip_code_prefix": str}),
        "odemeler": pd.read_csv(VERI / "olist_order_payments_dataset.csv"),
        "yorumlar": pd.read_csv(VERI / "olist_order_reviews_dataset.csv",
                                parse_dates=["review_creation_date", "review_answer_timestamp"]),
    }
    ceviri = pd.read_csv(VERI / "product_category_name_translation.csv", encoding="utf-8-sig")
    ceviri = dict(zip(ceviri["product_category_name"], ceviri["product_category_name_english"]))
    ceviri.update({"pc_gamer": "pc_gamer",
                   "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_processors"})
    t["urunler"]["kategori"] = t["urunler"]["product_category_name"].map(ceviri).fillna("unknown")
    return t


def son_yorumlar(t):
    """Her sipariş için en son yanıtlanan yorum."""
    return (t["yorumlar"].sort_values("review_answer_timestamp")
            .drop_duplicates("order_id", keep="last"))


def siparis_tablosu(t):
    """01 numaralı notebook'taki temizleme kurallarıyla teslim edilmiş siparişler tablosu."""
    s = t["siparisler"]
    donem = s[(s["order_purchase_timestamp"] >= BASLANGIC) & (s["order_purchase_timestamp"] < BITIS)]
    teslim = donem[(donem["order_status"] == "delivered") & donem["order_delivered_customer_date"].notna()]

    kalem_ozet = t["kalemler"].groupby("order_id").agg(
        urun_adedi=("order_item_id", "count"), urun_tutari=("price", "sum"), kargo_ucreti=("freight_value", "sum"))
    df = (teslim.merge(t["musteriler"], on="customer_id")
          .merge(kalem_ozet, on="order_id")
          .merge(son_yorumlar(t)[["order_id", "review_score"]], on="order_id", how="left"))

    df["ay"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    df["siparis_tutari"] = df["urun_tutari"] + df["kargo_ucreti"]
    df["teslim_suresi"] = (df["order_delivered_customer_date"] - df["order_purchase_timestamp"]).dt.total_seconds() / 86400
    df["gecikme_gun"] = (df["order_delivered_customer_date"].dt.normalize() - df["order_estimated_delivery_date"]).dt.days
    df["gec"] = df["gecikme_gun"] > 0
    return df


def koordinatlar():
    """Posta kodu öneki başına medyan enlem/boylam (Brezilya sınırları dışındaki hatalı noktalar atılır)."""
    g = pd.read_csv(VERI / "olist_geolocation_dataset.csv", dtype={"geolocation_zip_code_prefix": str})
    g = g[g["geolocation_lat"].between(-34, 5.5) & g["geolocation_lng"].between(-74, -34)]
    return (g.groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]].median()
            .rename(columns={"geolocation_lat": "lat", "geolocation_lng": "lng"}))


def haversine_km(lat1, lng1, lat2, lng2):
    """İki nokta arasındaki kuş uçuşu mesafe (km)."""
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def siparis_mesafesi(t, df, koord):
    """Her sipariş için satıcı ile müşteri arasındaki en uzak mesafe (km); birden çok satıcı varsa en uzağı."""
    musteri = df[["order_id", "customer_zip_code_prefix"]].join(koord, on="customer_zip_code_prefix")
    k = (t["kalemler"][["order_id", "seller_id"]].drop_duplicates()
         .merge(t["saticilar"][["seller_id", "seller_zip_code_prefix"]], on="seller_id")
         .join(koord.add_prefix("s_"), on="seller_zip_code_prefix")
         .merge(musteri, on="order_id"))
    k["mesafe_km"] = haversine_km(k["s_lat"], k["s_lng"], k["lat"], k["lng"])
    return k.groupby("order_id")["mesafe_km"].max()

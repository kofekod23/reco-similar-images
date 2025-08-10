"""
main.py — Script de démo BYO vectors (Weaviate)
- crée/recée une collection "Products" avec 2 vecteurs nommés : img_vec, txt_vec
- insère 2 objets avec des vecteurs jouets 4D
- effectue une recherche near_vector sur img_vec
"""

import os
from typing import List
from dotenv import load_dotenv

import weaviate
import weaviate.classes as wvc
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType

# ----- 0) Charger les variables d'environnement depuis .env -----
load_dotenv()
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
COLLECTION = os.getenv("COLLECTION", "Products")

if not WEAVIATE_API_KEY:
    raise SystemExit("❌ WEAVIATE_API_KEY manquante dans .env")

# ----- 1) Connexion -----
def connect():
    """
    Connexion locale. On considère /v1/.well-known/ready OK si status==200,
    même si le body est vide. En fallback, on ping /v1/meta.
    """
    import os, json
    from urllib.request import Request, urlopen
    from urllib.parse import urlparse
    from weaviate.classes.init import Auth

    url = os.getenv("WEAVIATE_URL", "http://localhost:8080").rstrip("/")
    api_key = os.getenv("WEAVIATE_API_KEY")
    if not api_key:
        raise SystemExit("❌ WEAVIATE_API_KEY manquante dans .env")

    # 1) Ping readiness
    try:
        req = Request(f"{url}/v1/.well-known/ready",
                      headers={"Authorization": f"Bearer {api_key}"})
        with urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ready non-200: {resp.status}")
        print(f"➡️ Ready 200 sur {url}")
    except Exception as e:
        # 2) Fallback: /v1/meta
        req = Request(f"{url}/v1/meta",
                      headers={"Authorization": f"Bearer {api_key}"})
        with urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Meta non-200: {resp.status}")
            _ = json.loads(resp.read().decode("utf-8", "ignore"))
        print(f"➡️ Meta 200 sur {url} (fallback readiness)")

    # 3) Connexion client
    p = urlparse(url)
    host = p.hostname or "localhost"
    port = p.port or (443 if p.scheme == "https" else 80)
    secure = (p.scheme == "https")

    client = weaviate.connect_to_custom(
        http_host=host, http_port=port, http_secure=secure,
        grpc_host=host, grpc_port=50051, grpc_secure=secure,
        auth_credentials=Auth.api_key(api_key)
    )
    print("✅ Connecté.")
    return client


# ----- 2) (Re)créer la collection avec 2 vecteurs nommés -----
def recreate_collection(client: weaviate.WeaviateClient):
    if client.collections.exists(COLLECTION):
        print(f"ℹ️ Suppression collection existante: {COLLECTION}")
        client.collections.delete(COLLECTION)

    print(f"➡️ Création collection: {COLLECTION}")
    client.collections.create(
        name=COLLECTION,
        properties=[
            Property(name="sku", data_type=DataType.TEXT),
            Property(name="title", data_type=DataType.TEXT),
            Property(name="brand", data_type=DataType.TEXT),
            Property(name="category", data_type=DataType.TEXT),
            Property(name="price", data_type=DataType.NUMBER),
            Property(name="image_url", data_type=DataType.TEXT),
            Property(name="caption", data_type=DataType.TEXT),
        ],
        # BYO vectors nommés : on enverra img_vec et txt_vec à l'insert
        vector_config=[
            Configure.Vectors.self_provided(name="img_vec"),
            Configure.Vectors.self_provided(name="txt_vec"),
        ],
    )
    print("✅ Collection créée.")

# ----- 3) Insérer quelques objets de test (vecteurs jouets 4D) -----
def insert_samples(client: weaviate.WeaviateClient):
    print("➡️ Insert d'objets de test ...")
    col = client.collections.get(COLLECTION)

    samples = [
        {
            "properties": {
                "sku": "SKU001",
                "title": "Pull col rond",
                "brand": "ACME",
                "category": "pulls",
                "price": 39.9,
                "image_url": "https://example.com/img1.jpg",
                "caption": "a round-neck sweater"
            },
            # 4D pour la démo ; dans la vraie vie: 512 ou 768 dims
            "img_vec": [0.10, 0.20, 0.30, 0.40],
            "txt_vec": [0.12, 0.21, 0.29, 0.41],
        },
        {
            "properties": {
                "sku": "SKU002",
                "title": "Pull zippé",
                "brand": "ACME",
                "category": "pulls",
                "price": 49.9,
                "image_url": "https://example.com/img2.jpg",
                "caption": "a zip-front sweater"
            },
            "img_vec": [0.11, 0.19, 0.31, 0.39],
            "txt_vec": [0.10, 0.22, 0.28, 0.42],
        },
    ]

    for s in samples:
        col.data.insert(
            properties=s["properties"],
            vector={"img_vec": s["img_vec"], "txt_vec": s["txt_vec"]},
        )
    total = col.aggregate.over_all(total_count=True).total_count
    print(f"✅ Insert OK. Total objets: {total}")

# ----- 4) Recherche: near_vector sur img_vec -----
def search_by_imgvec(client: weaviate.WeaviateClient, q: List[float], k: int = 5):
    print("➡️ Recherche near_vector (img_vec) ...")
    col = client.collections.get(COLLECTION)
    res = col.query.near_vector(
        near_vector=q,
        target_vector="img_vec",  # IMPORTANT quand il y a plusieurs vecteurs nommés
        limit=k,
        return_properties=["sku", "title", "brand", "price"],
        return_metadata=wvc.query.MetadataQuery(distance=True),
    )
    if not res.objects:
        print("⚠️ Aucun résultat")
        return
    for o in res.objects:
        d = round(o.metadata.distance, 4)
        p = o.properties
        print(f"• dist={d}  sku={p['sku']}  title={p['title']}  price={p['price']}")

# ----- 5) Recherche: near_vector sur txt_vec (facultatif) -----
def search_by_txtvec(client: weaviate.WeaviateClient, q: List[float], k: int = 5):
    print("➡️ Recherche near_vector (txt_vec) ...")
    col = client.collections.get(COLLECTION)
    res = col.query.near_vector(
        near_vector=q,
        target_vector="txt_vec",
        limit=k,
        return_properties=["sku", "title", "caption"],
        return_metadata=wvc.query.MetadataQuery(distance=True),
    )
    for o in res.objects:
        d = round(o.metadata.distance, 4)
        p = o.properties
        print(f"• dist={d}  sku={p['sku']}  title={p['title']}  caption={p['caption']}")

# ----- Main -----
if __name__ == "__main__":
    client = connect()
    try:
        recreate_collection(client)
        insert_samples(client)
        # Vecteur de requête 4D (proche de SKU001)
        q_img = [0.11, 0.20, 0.29, 0.41]
        search_by_imgvec(client, q_img, k=2)

        # Exemple txt_vec (facultatif)
        q_txt = [0.11, 0.21, 0.29, 0.41]
        search_by_txtvec(client, q_txt, k=2)
    finally:
        client.close()
        print("👋 Fin.")

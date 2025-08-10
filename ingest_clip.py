# ingest_clip.py — lit un CSV (sku,title,image_url,...) et insère img_vec
import os, io, csv, argparse, requests
from PIL import Image
import torch, open_clip
import weaviate, weaviate.classes as wvc
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType

parser = argparse.ArgumentParser()
parser.add_argument("--csv", required=True, help="CSV avec colonnes sku,title,image_url (min)")
parser.add_argument("--limit", type=int, default=50)
parser.add_argument("--arch", default="ViT-B-32")
parser.add_argument("--pretrain", default="laion2b_s34b_b79k")
args = parser.parse_args()

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
COLL = os.getenv("COLLECTION", "Products")

device = "cuda" if torch.cuda.is_available() else "cpu"
model, _, preprocess = open_clip.create_model_and_transforms(args.arch, pretrained=args.pretrain, device=device)
model.eval()

def fetch(url):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def embed_image(img: Image.Image):
    with torch.inference_mode(), torch.cuda.amp.autocast(enabled=(device=="cuda")):
        t = preprocess(img).unsqueeze(0).to(device)
        feat = model.encode_image(t)
        feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat.squeeze().float().cpu().tolist()

client = weaviate.connect_to_custom(
    http_host="localhost", http_port=8080, http_secure=False,
    grpc_host="localhost", grpc_port=50051, grpc_secure=False,
    auth_credentials=Auth.api_key(WEAVIATE_API_KEY)
)

# Crée la collection si absente (named vector img_vec)
if not client.collections.exists(COLL):
    client.collections.create(
        name=COLL,
        properties=[
            Property(name="sku", data_type=DataType.TEXT),
            Property(name="title", data_type=DataType.TEXT),
            Property(name="image_url", data_type=DataType.TEXT),
        ],
        vector_config=[Configure.Vectors.self_provided(name="img_vec")]
    )

col = client.collections.get(COLL)

with open(args.csv, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if args.limit and i >= args.limit: break
        sku = str(row.get("sku",""))
        title = str(row.get("title",""))
        url = str(row.get("image_url",""))
        if not (sku and title and url): continue
        vec = embed_image(fetch(url))
        col.data.insert(
            properties={"sku": sku, "title": title, "image_url": url},
            vector={"img_vec": vec}
        )
        if (i+1) % 10 == 0:
            print(f"Inserted {i+1}")

print("✅ Done.")
client.close()

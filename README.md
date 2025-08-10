
cat > README.md <<'MARKDOWN'
# Reco d’images similaires (Weaviate + CLIP)

Pipeline minimal “image → images similaires” :
- **Weaviate** local via Docker (API key).
- 2 vecteurs par objet : `img_vec` (embedding image CLIP) et `txt_vec` (embedding du caption BLIP, à venir).
- Scripts client Python pour ingestion / recherche.

## Démarrage rapide
1) **Weaviate** (Docker) : API key activée, RBAC off.
2) **Client Python** : installer `client/requirements.txt`, renseigner `.env` (voir `.env.example`).
3) **Tests** : exécuter `client/main.py` puis `client/search_by_image.py`.

## Variables d’environnement
Voir `.env.example`. Copie-le vers `.env` (ne pas committer) puis adapte les valeurs.

## CI Docker → GHCR
Le workflow `build-ghcr.yml` build/push une image **si `worker/Dockerfile` existe**.  
Image publiée sous : `ghcr.io/<OWNER>/reco-similar-images-worker:latest`.

### Étapes suivantes
- Ajouter **BLIP** pour générer des captions et alimenter `txt_vec`.
- Créer `worker/Dockerfile` + `worker.py` (pipeline BLIP+CLIP) → la CI poussera auto sur GHCR.
- (Option) UI **Streamlit** pour requêter Weaviate.


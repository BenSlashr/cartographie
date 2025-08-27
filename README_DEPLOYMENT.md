# Déploiement Cartographie Sémantique

## Configuration pour VPS

### Variables d'environnement nécessaires

Pour déploiement sur `ndd.fr/cartographie/`:

```bash
# Dans votre docker-compose.yml ou configuration:
ROOT_PATH=/cartographie
EMBEDDINGS_ENDPOINT=https://outils.agence-slashr.fr/embedding
EMBED_BATCH=250
DATA_DIR=/app/data
```

### Structure attendue sur le VPS

```
/seo-tools/
├── cartographie/              # Ce dossier
│   ├── Dockerfile
│   ├── app/
│   ├── static/
│   ├── data/                  # Persisté avec volume Docker
│   └── ...
└── docker-compose.yml        # Géré globalement
```

### Configuration Docker Compose (à ajouter dans /seo-tools/)

```yaml
services:
  cartographie:
    build: ./cartographie
    container_name: cartographie
    environment:
      - ROOT_PATH=/cartographie
      - EMBEDDINGS_ENDPOINT=https://outils.agence-slashr.fr/embedding
      - EMBED_BATCH=250
      - DATA_DIR=/app/data
    volumes:
      - ./cartographie/data:/app/data
    networks:
      - seo-tools
    restart: unless-stopped
```

### Configuration Caddy

Pour servir sur `ndd.fr/cartographie/`:

```caddyfile
ndd.fr {
    # Autres routes...
    
    handle_path /cartographie/* {
        reverse_proxy cartographie:8000
    }
}
```

### Base de données

- SQLite automatiquement créée dans `/app/data/cartographie.db`
- Volume Docker assure la persistance des données
- Pas de configuration supplémentaire nécessaire

### APIs nécessaires

L'outil utilise l'API d'embeddings:
- `https://outils.agence-slashr.fr/embedding/v1/embeddings`
- Modèle: `BAAI/bge-m3`
- Batch size optimisé: 250

### Fonctionnalités

✅ Upload de fichiers CSV (pages et liens)  
✅ Génération d'embeddings sémantiques  
✅ Clustering automatique optimisé  
✅ Visualisation interactive  
✅ Sauvegarde SQLite des analyses  
✅ Interface de chargement des analyses précédentes  
✅ Export CSV des résultats  
✅ Gestion des gros datasets (100k+ URLs)  

### Accès

- Interface: `https://ndd.fr/cartographie/`  
- API Docs: `https://ndd.fr/cartographie/docs`  
- Health: `https://ndd.fr/cartographie/api/v1/projects/`
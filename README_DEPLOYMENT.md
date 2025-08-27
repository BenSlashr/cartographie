# Déploiement Cartographie Sémantique

## Configuration pour VPS

### Variables d'environnement nécessaires

Pour déploiement sur `outils.agence-slashr.fr/cartographie/`:

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

Pour servir sur `outils.agence-slashr.fr/cartographie/`:

```caddyfile
outils.agence-slashr.fr {
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

- Interface: `https://outils.agence-slashr.fr/cartographie/`  
- API Docs: `https://outils.agence-slashr.fr/cartographie/docs`  
- Health: `https://outils.agence-slashr.fr/cartographie/api/v1/projects/`
- Debug: `https://outils.agence-slashr.fr/cartographie/debug/paths` (vérifier les chemins)

### Debug en cas de problème

Si JavaScript ne charge pas (erreur `Unexpected token '<'`):

1. **Vérifier les chemins**: `curl https://outils.agence-slashr.fr/cartographie/debug/paths`
2. **Tester l'accès statique**: `curl https://outils.agence-slashr.fr/cartographie/static/app.js`
3. **Vérifier les logs Docker**: `docker logs cartographie`

**Solutions courantes:**
- Vérifier que `ROOT_PATH=/cartographie` est bien défini
- Vérifier que Caddy redirige bien vers le container
- S'assurer que les fichiers statiques sont copiés dans l'image Docker
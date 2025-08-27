#!/bin/bash
echo "🔄 Rebuilding Docker image without cache..."

# Stop container
docker compose down cartographie

# Remove image to force rebuild
docker rmi seo-tools-cartographie 2>/dev/null || true

# Build without cache
docker compose build --no-cache cartographie

# Start container
docker compose up -d cartographie

echo "✅ Rebuild complete!"
echo "🔗 Test at: https://outils.agence-slashr.fr/cartographie/"
"""Main entry point for the Boxcatering Chatbot."""

import uvicorn
from h11 import PRODUCT_ID

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )
# python3 ./scripts/migrate_assortment.py
#
# sudo docker exec -it chatbot python ./scripts/migrate_assortment.py
#
# sudo git fetch
# sudo git pull origin 16.1-misha
# sudo docker compose -f Docker/docker-compose.yml down
# sudo docker build -t chatbot:latest .
# sudo docker compose -f Docker/docker-compose.yml up -d
# sudo docker logs chatbot -f
# sudo docker compose -f ../boxcatering-sales_chatbot/Docker/docker-compose.yml up -d postgres
# sudo docker exec -it chatbot python ./scripts/migrate_assortment.py


# sudo docker compose -f Docker/demo.yml -p demo up -d --build
# sudo docker exec -it demo_chatbot python ./scripts/migrate_assortment.py
# sudo docker exec -it demo_chatbot python ./scripts/init_db.py

# git fetch --all
# git reset --hard origin/16.10-misha

# PROD
#
# sudo git fetch
# sudo git pull prod
# sudo docker compose -f Docker/docker-compose.yml down
# sudo docker build -t chatbot:latest .
# sudo docker compose -f Docker/docker-compose.yml up -d
# sudo docker logs chatbot -f
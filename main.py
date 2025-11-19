"""Main entry point for the Boxcatering Chatbot."""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )
# python3 ./scripts/migrate_assortment.py
#
# sudo docker exec -it chatbot python ./scripts/migrate_assortment.py
#
# sudo docker compose -f Docker/docker-compose.yml down
# sudo docker build -t chatbot:latest .
# sudo docker compose -f Docker/docker-compose.yml up -d
# sudo docker compose -f ../boxcatering-sales_chatbot/Docker/docker-compose.yml up -d postgres
# sudo docker exec -it chatbot python ./scripts/migrate_assortment.py
# sudo docker logs chatbot -f

# sudo docker compose -f Docker/demo.yml -p demo up -d --build
# sudo docker exec -it demo_chatbot python ./scripts/migrate_assortment.py
# sudo docker exec -it demo_chatbot python ./scripts/init_db.py

# git fetch --all
# git reset --hard origin/16.10-misha

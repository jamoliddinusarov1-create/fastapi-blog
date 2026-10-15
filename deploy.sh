#!/bin/bash
set -e

echo "🚀 Yangilanish boshlandi..."

# 1. Virtual muhitni faollashtirish
source venv/bin/activate

# 2. Yangi kutubxonalarni o'rnatish
pip install -r requirements.txt

# 3. Bazaga o'zgarishlarni (migratsiyani) qo'llash
alembic upgrade head

# 4. FastAPI xizmatingizni qayta ishga tushirish (restart)
sudo systemctl restart fastapi.service

echo "✅ Loyiha muvaffaqiyatli yangilandi!"
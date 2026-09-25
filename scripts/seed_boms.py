#!/usr/bin/env python
"""Seed 6 BOM records with items."""
import os
import sys

# make sure this repo is importable cleanly
sys.path.insert(0, r"C:\Storage\Software\Antigravity\Django\Antigravity_MES")
os.environ.setdefault("PYTHONPATH", "")
os.environ["DJANGO_SETTINGS_MODULE"] = "miniMES.settings"

import django
django.setup()

from Product.models import Product
from Material.models import Material
from Production.models import BOM, BOMItem

products = list(Product.objects.all())
materials = list(Material.objects.all())
if not products or not materials:
    raise SystemExit("Need at least 1 Product and 1 Material")

# Build 6 deterministic BOMs from first 6 products if available
boms = []
for idx, product in enumerate(products[:6]):
    bom, _ = BOM.objects.get_or_create(
        product=product,
        version="1.0",
        defaults={
            "description": f"Auto-seeded BOM for {product.name}",
            "is_active": True,
        },
    )
    boms.append(bom)

# Seed 1-3 items per BOM from available materials
for i, bom in enumerate(boms):
    existing = BOMItem.objects.filter(bom=bom).count()
    if existing:
        continue
    # pick a few materials deterministically
    picks = [materials[(i + j) % len(materials)] for j in range(3)]
    for seq, material in enumerate(picks, start=1):
        BOMItem.objects.create(
            bom=bom,
            component=material,
            quantity=seq * 2,
            unit="PCS",
            notes="seeded",
        )

print(f"Created/ensured {len(boms)} BOM(s).")
print("BOMItem counts:", {bom.product.name: BOMItem.objects.filter(bom=bom).count() for bom in boms})

from tcgdexsdk import TCGdex, Language
import pandas as pd
import os

tcgdex = TCGdex() # Initialize with default language (English)

# Or using the Language enum
tcgdex = TCGdex(Language.EN)

serie = tcgdex.serie.getSync('tcgp')

for set in serie.sets:
    set = tcgdex.set.getSync(set.id)
    cards = []

    if os.path.isfile(f'./cards/{set.name}.json'):
        print(f'{set.name} already imported, skip')
    else:
        for card in set.cards:
            card = tcgdex.card.getSync(card.id)

            packs = [b.name for b in card.boosters] if card.boosters is not None else []
            pack = None
            if len(packs) > 0:
                pack = packs[0]

            card = {
                "id": card.id.lower().replace('p-a', 'pa'),
                "name": card.name,
                "element": card.types[0] if card.types is not None else None,
                "type": card.category,
                "subtype": card.stage,
                "health": card.hp,
                "set": f'{card.set.name} ({set.id})',
                "pack": pack if pack is not None else "All",
                "attacks": [{
                    "name": a.name,
                    "effect": a.effect,
                    "damage": a.damage,
                    "cost": a.cost
                } for a in card.attacks] if card.attacks is not None else [],
                "weakness": card.weaknesses[0].type if card.weaknesses is not None else None,
                "abilities": [{
                    "name": a.name,
                    "effect": a.effect,
                } for a in card.abilities] if card.abilities is not None else [],
                "evolvesFrom": card.evolvesFrom,
                "rarity": card.rarity
            }

            cards.append(card)

            df = pd.DataFrame(cards)
            df.to_json(f'./cards/{set.name}.json', orient="records", force_ascii=False)




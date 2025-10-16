import http.server
import socketserver
import pandas as pd
import threading
import webbrowser
from os import walk
import warnings
import json
import os
import urllib.request
import re
from unidecode import unidecode
# https://pocket.limitlesstcg.com/cards/A4b/1

set_id = 'A4b'
set_name = 'Deluxe Pack: ex (A4b)'
pack='Pikachu'







final_result = None

card_id = 1
# while i <= max_card_id:

contents = urllib.request.urlopen(f'https://pocket.limitlesstcg.com/cards/{set_id}/{card_id}/').read().decode('utf-8')
contents = contents.replace('\r', '').replace('\n', '')

print(contents)

print(f'{set_id}-{"{:03d}".format(card_id)}'.lower().strip())
print(re.findall(f'<span class="card-text-name"><a href="/cards/{set_id}/{card_id}">(.*)</a></span>', contents)[0].strip())
print(re.findall(f'</a></span>(.*)</p>', contents)[0].split('-')[1].strip())
print(unidecode(re.findall(f'<p class="card-text-type">(.*)</p>', contents)[0].split('-')[0].split('<')[0].strip()))

# {
#     "id": card.id.lower().replace('p-a', 'pa'),
#     "name": card.name,
#     "element": card.types[0] if card.types is not None else None,
#     "type": card.category,

#     "subtype": card.stage,
#     "health": card.hp,
#     "set": f'{card.set.name} ({set.id})',
#     "pack": pack if pack is not None else "All",
#     "attacks": [{
#         "name": a.name,
#         "effect": a.effect,
#         "damage": a.damage,
#         "cost": a.cost
#     } for a in card.attacks] if card.attacks is not None else [],
#     "weakness": card.weaknesses[0].type if card.weaknesses is not None else None,
#     "abilities": [{
#         "name": a.name,
#         "effect": a.effect,
#     } for a in card.abilities] if card.abilities is not None else [],
#     "evolvesFrom": card.evolvesFrom,
#     "rarity": card.rarity
# }





# result = re.findall("<a  href=\"/cards/(.*)\" >", contents)
# result = result[0].split('/')

# origin_id = f'{result[0]}-{"%03d" % (int(result[1]),)}'.lower()

# print()

# if final_result is None: 
#     final_result = card
# else:
#     final_result = pd.concat([final_result, card], ignore_index=True, axis=0)
# i = i + 1




# print(final_result)

# final_result.to_json(f'./cards/Deluxe Pack Ex.json', orient="records", force_ascii=False)
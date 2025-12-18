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
import json
# https://pocket.limitlesstcg.com/cards/A4b/1

set_id = 'B1a'
set_title = 'Crimson Blaze'
set_name = 'Crimson Blaze (B1a)'

i = 1
max_card_id = 103

shiniy_limit = 88

def getType(character):
    match character:
        case "G":
            return "Grass"
        case "F":
            return "Fire"
        case "W":
            return "Water"
        case "L":
            return "Lightning"
        case "P":
            return "Psychic"
        case "F":
            return "Fighting"
        case "D":
            return "Darkness"
        case "M":
            return "Metal"
        case _:
            return "Colorless"

def getCosts(typeString):
    cost = []
    for energy in typeString:
        cost.append(getType(energy))

    return cost

def getAttacks(contents):
    attacks = re.findall(f'<div class="card-text-attack">(.*)</div>', contents)[0].split('<div class="card-text-attack">')
    index = 1

    result = []

    for attack in attacks:
        if index == len(attacks):
            attack = attack.split('</div>')[0]
        attack = attack.strip()

        name = re.sub('[\\+x0-9]', '', attack.split('</span>')[1].split('</p>')[0]).strip()
        effect = attack.split('<p class="card-text-attack-effect">')[1].split('</p>')[0].strip()
        damage = re.sub('[A-Za-z\\-]', '', attack.split('</span>')[1].split('</p>')[0]).strip()
        cost = attack.split('<span class="ptcg-symbol">')[1].split('</span>')[0].strip()
        result.append({
            "name": name,
            "effect": None if effect == '' else effect,
            "damage": damage,
            "cost": getCosts(cost)
        })

        index = index + 1

    return result

def getAbility(content):
    if len(content) > 0:
        name = content[0].split('Ability:')[1].split('</p>')[0].strip()
        effect = content[0].split('<p class="card-text-ability-effect">')[1].split('</p>')[0].strip()


        effect = re.sub('<[^<]+?>', '', effect).replace("[G]", "Grass").replace("[F]", "Fire").replace("[W]", "Water").replace("[L]", "Lightning").replace("[P]", "Psychic").replace("[D]", "Darkness").replace("[M]", "Metal").replace("[C]", "Grass").replace("[G]", "Colorless")

        return [{
            "name": name,
            "effect": effect,
        }]

    else:
        return []

def getEvolvesFrom(content):
    if content == 'text':
        return None
    else:
        content = re.sub('<[^<]+?>', '', content).split('from')[1].split('<div')[0].strip()
        return content

def getRarity(rarity, index):
    match rarity:
        case "◊":
            return "One Diamond"
        case "◊◊":
            return "Two Diamond"
        case "◊◊◊":
            return "Three Diamond"
        case "◊◊◊◊":
            return "Four Diamond"
        case "☆":
            return "One Star" if index < shiniy_limit else "One Shiny"
        case "☆☆":
            return "Two Star" if index < shiniy_limit else "Two Shiny"
        case "☆☆☆":
            return "Three Star"
        case "Crown Rare":
            return "Crown"
        case _:
            return "unknown"

def getPack(value):
    if len(value) > 2:
        return value[2].split('</span>')[0].split('pack')[0].strip()
    else:
        return 'All'

newSet = []

while i <= max_card_id:
    print(i)


    contents = urllib.request.urlopen(f'https://pocket.limitlesstcg.com/cards/{set_id}/{i}/').read().decode('utf-8')
    contents = contents.replace('\r', '').replace('\n', '')

    card_type = unidecode(re.findall(f'<p class="card-text-type">(.*)</p>', contents)[0].split('-')[0].split('<')[0].strip())
    card = {
        "id": f'{set_id.replace('-', '')}-{"{:03d}".format(i)}'.lower().strip(),
        "name": re.findall(f'<span class="card-text-name"><a href="/cards/{set_id}/{i}">(.*)</a></span>', contents)[0].strip(),
        "element": re.findall(f'</a></span>(.*)</p>', contents)[0].split('-')[1].strip() if card_type != 'Trainer' else None,
        "type": card_type,
        "subtype": unidecode(re.findall(f'<p class="card-text-type">(.*)</p>', contents)[0].split('-')[1].split('<')[0].strip()) if card_type != 'Trainer' else None,
        "health": float(re.findall(f'</a></span>(.*)</p>', contents)[0].split('-')[2].split('<')[0].strip().split(' ')[0]) if card_type != 'Trainer' else None,
        "set": set_name,
        "pack": "All" if "Promo" in set_title else getPack(re.findall(f'<div class="prints-current-details">.*<span class="text-lg">(.*)</div>', contents)[0].split('·')),
        "attacks": getAttacks(contents) if card_type != 'Trainer' else [],
        "weakness": re.findall(f'<p class="card-text-wrr">(.*)</p>', contents)[0].split('Weakness:')[1].split('<br>')[0].strip() if card_type != 'Trainer' else None,
        "abilities": getAbility(re.findall(f'<div class="card-text-ability">(.*)</p>', contents)) if card_type != 'Trainer' else [],
        "evolvesFrom": getEvolvesFrom(unidecode(re.findall(f'<p class="card-text-type">(.*)</p>', contents)[0].split('-')[2].strip())) if card_type != 'Trainer' else None,
        "rarity": getRarity(re.findall(f'<div class="prints-current-details">.*<span class="text-lg">(.*)</div>', contents)[0].split('·')[1].split('</span>')[0].strip(), i)
    }

    newSet.append(card)

    i = i + 1


newSetContent = json.dumps(newSet)

with open(f"./cards/{set_title}.json", "w") as text_file:
    text_file.write(newSetContent)





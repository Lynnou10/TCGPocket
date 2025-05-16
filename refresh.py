import pandas as pd
from os import walk
from os import remove
import warnings
import json 
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter(action='ignore', category=DeprecationWarning)
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)
 
pd.set_option("display.max_rows", 500)

# active_extention = 'Celestial Guardians (A3)'
active_extention = 'Unknown'

with open("./utils/french.json", encoding="utf-8") as f:
    french = json.load(f)
with open("./utils/english.json") as f:
    english = json.load(f)


def manageRegionalName(name):
    isEx = False
    if(' ex' in name):
        isEx = True
        name = name.replace(" ex", "")
    if('Paldean ' in name):
        name = f'{name.replace("Paldean ", "")} de Paldéa'
    if('Alolan ' in name):
        name = f'{name.replace("Alolan ", "")} d\'Alola'
    if('Origin Forme ' in name):
        name = f'{name.replace("Origin Forme ", "")} Forme Originelle'
    if(isEx):
        name = f'{name} EX'
    return name

def translateName(name):
    if(name == -1):
        return 'No Data'

    selectedEnglishName = name
    selectedIndex = -1
    prio = False
    for index, englishName in enumerate(english):
        if englishName in name and prio == False:
            selectedEnglishName = englishName
            selectedIndex = index
        if englishName == name:
            selectedEnglishName = englishName
            selectedIndex = index
            prio = True
    if(index != -1):
        return manageRegionalName(name.replace(selectedEnglishName, french[selectedIndex]))
    else:
        return manageRegionalName(name)

def getRarity():
    rarity = pd.read_json('./utils/rarity.json')
    return rarity

def mapPowerName(powers):
    response = []
    for power in powers:
        response.append(power['name'])
    return ','.join(response)

def getCards():
    cards = []
    files = next(walk('./cards'), (None, None, []))[2]
    for file in files:
       cards.append(pd.read_json(f'./cards/{file}'))
    cards = pd.concat(cards)
    cards['set_id'] = cards['id'].str.split("-").str[0].str.upper()
    cards['card_id'] = cards['id'].str.split("-").str[1].str.lstrip('0').astype('int64')
    cards['attacks'] = cards['attacks'].map(mapPowerName)
    cards['abilities'] = cards['abilities'].map(mapPowerName)
    cards = cards.rename(columns={"rarity": "rarityCode"})
    cards = cards.drop(columns=['id', 'evolvesFrom', "type"])
    return cards

def getCollection():
    collection = []
    files = next(walk('./collection'), (None, None, []))[2]
    for file in files:
        collection.append(pd.read_csv(f'./collection/{file}'))
    collection = pd.concat(collection)
    collection['set_id'] = collection['set_id'].str.upper()
    collection['set_id'] = collection['set_id'].str.replace('P-A', 'PA')
    return collection.drop_duplicates()

def groupMissingCards(cards):
    value = cards[cards['rarityOrder']==cards['rarityOrder'].min()]
    if(value['quantity'].sum().astype(int) == 0):
        value['quantity'] = 0
    else:
        value['quantity'] = cards['quantity'].sum()
    return value

def getMissingCards(collection):
    missingCards = collection.groupby(by=["name", "element", "subtype", "health", "attacks", "retreatCost", "weakness", "abilities"], as_index=False).apply(groupMissingCards)
    missingCards = missingCards.reset_index()[['set_id', 'card_id', 'set', 'name', 'pack','quantity', 'rarity', 'rarityOrder']]
    missingCards = missingCards.query(f'quantity < 2 and rarityOrder < 5 and rarity != -1 and set != "{active_extention}"').sort_values(by=['quantity', 'rarity', 'set', 'card_id'], ascending=[True, False, True, True])
    try:
        remove('./output/missing_cards.csv')
    except OSError as error:
        print(error)
        print("File path can not be removed")
    print(f'NUMBER OF MISSING CARDS: {missingCards["set_id"].count()}')
    missingCards = missingCards.replace(-1, 'No Data').drop(columns=['set_id', 'rarityOrder'])
    missingCards.to_csv('./output/missing_cards.csv', index=False, encoding='utf-8')
    missingCards.to_json('./output/missing_cards.json', orient="records", force_ascii=False)

def getRecycleCards(collection):
    recycleCards = collection.query('quantity > 2 and set_id != "PA" and rarityOrder > 2')
    recycleCards['quantity'] = recycleCards['quantity'] - 2
    recycleCards['total'] = recycleCards['quantity'] * recycleCards['recycle']
    recycleCards = recycleCards.sort_values(by=['total', 'rarityOrder', 'set_id', 'card_id'], ascending=[False, False, True, True])
    recycleCards = recycleCards[['card_id', 'name', 'set', 'quantity', 'rarity', 'recycle', 'total']]
    print(f'TOTAL TRADING POINTS AVAILABLE: {recycleCards["total"].sum()}')
    try:
        remove('./output/recycle_cards.csv')
    except OSError as error:
        print(error)
        print("File path can not be removed")
    recycleCards.to_csv('./output/recycle_cards.csv', index=False, encoding='utf-8')

def groupTradeCards(cards):
    cardQuantity = cards['quantity'].sum()
    cardNumber = cards['quantity'].count()
    subtract = 2
    if(cardNumber > 1):
        subtract = 1

    if(cardQuantity > 2):
        cards['quantity'] = cards['quantity'] - subtract
        return cards

def getTradeCards(collection):
    tradeCards = collection.groupby(by=["name", "element", "subtype", "health", "attacks", "retreatCost", "weakness", "abilities"], as_index=False).apply(groupTradeCards)
    tradeCards = tradeCards.query(f'quantity > 0 and rarityOrder > 2 and rarityOrder < 6 and set_id != "PA" and set != "{active_extention}"')
    tradeCards = tradeCards.sort_values(by=['rarityOrder', 'quantity', 'set_id', 'card_id'], ascending=[False, False, True, True])
    try:
        remove('./output/trade_cards.csv')
    except OSError as error:
        print(error)
        print("File path can not be removed")
    print(f'NUMBER OF TRADE CARDS: {tradeCards["set_id"].count()}')
    tradeCards.drop(columns=['set_id', 'rarityOrder', 'recycle', 'pack', 'element', 'subtype', 'health', 'attacks', 'retreatCost', 'weakness', 'abilities', 'card_name']).to_csv('./output/trade_cards.csv', index=False, encoding='utf-8')

# GET COLLECTION
cards = getCards()
rarity = getRarity()
collection = getCollection()
collection = pd.merge(collection, cards, left_on=['set_id', 'card_id'], right_on=['set_id', 'card_id'], how='left')
collection = pd.merge(collection, rarity, left_on=['rarityCode'], right_on=['code'], how='left').drop(columns=['rarityCode', 'code'])
collection.fillna(-1, inplace = True)
collection['name'] = collection['name'].map(translateName)
print(f'NUMBER OF CARDS: {collection["quantity"].sum()}')

# GET MISSING CARDS
getMissingCards(collection)

# GET RECYCLE CARDS
getRecycleCards(collection)

# GET TRADE CARDS
getTradeCards(collection)


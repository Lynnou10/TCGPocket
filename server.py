import http.server
import socketserver
import pandas as pd
from os import walk
from os import remove
import warnings
import json 
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter(action='ignore', category=DeprecationWarning)
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)
 
pd.set_option("display.max_rows", 500)

# 8652622458979642
# active_extention = 'Celestial Guardians (A3)'
active_extention = 'Unknown'
trade_rarity_threshold = 6

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
    
    if(name == 'All'):
        return name

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
    if(selectedIndex != -1):
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
    collection = pd.read_csv(f'./collection/collection.csv')
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
    missingCards = missingCards.reset_index()[['set_id', 'card_id', 'set', 'name', 'french_name', 'pack', 'pack_french_name','quantity', 'rarity', 'rarityOrder', 'tradeCost', 'pointCost']]
    missingCards = missingCards.query(f'quantity < 2 and rarityOrder < 5 and rarity != -1 and set != "{active_extention}"').sort_values(by=['quantity', 'rarity', 'set', 'card_id'], ascending=[True, False, True, True])
    oneStarMissing = collection.query(f'quantity == 0 and rarityOrder == 5 and rarity != -1 and set != "{active_extention}"')[['set_id', 'card_id', 'set', 'name', 'french_name', 'pack', 'pack_french_name', 'quantity', 'rarity', 'rarityOrder', 'tradeCost', 'pointCost']]
    missingCards = pd.concat([missingCards, oneStarMissing])
    try:
        remove('./csv_output/missing_cards.csv')
    except OSError as error:
        print(error)
        print("File path can not be removed")
    print(f'NUMBER OF MISSING CARDS: {missingCards["set_id"].count()}')
    missingCards = missingCards.replace(-1, 'No Data').drop(columns=['set_id'])
    missingCards.to_csv('./csv_output/missing_cards.csv', index=False, encoding='utf-8')
    missingCards.sort_values(by=['card_id']).to_json('./output/missing_cards.json', orient="records", force_ascii=False)

def getRecycleCards(collection, tradeCards):
    recycleCards = collection.query('quantity > 2 and set_id != "PA" and rarityOrder > 2')
    recycleCards['quantity'] = recycleCards['quantity'] - 2
    recycleCards['total'] = recycleCards['quantity'] * recycleCards['recycle']
    recycleCards = recycleCards.sort_values(by=['total', 'rarityOrder', 'set_id', 'card_id'], ascending=[False, False, True, True])
    recycleCards = recycleCards[['card_id', 'name', 'french_name', 'pack', 'pack_french_name', 'set', 'quantity', 'rarity', 'rarityOrder', 'recycle', 'total']]
    recycleCards = pd.merge(recycleCards, tradeCards, left_on=['set', 'card_id'], right_on=['set', 'card_id'], how='left')
    recycleCards = recycleCards.rename(columns={"quantity_x": "quantity", "quantity_y": "trade_quantity"})
    print(f'TOTAL TRADING POINTS AVAILABLE: {recycleCards["total"].sum()}')
    try:
        remove('./csv_output/recycle_cards.csv')
    except OSError as error:
        print(error)
        print("File path can not be removed")
    recycleCards.to_csv('./csv_output/recycle_cards.csv', index=False, encoding='utf-8')
    recycleCards.sort_values(by=['card_id']).to_json('./output/recycle_cards.json', orient="records", force_ascii=False)

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
    tradeCards = collection[collection['quantity'] > 0]
    tradeCards = tradeCards.groupby(by=["name", "element", "subtype", "health", "attacks", "retreatCost", "weakness", "abilities"], as_index=False).apply(groupTradeCards)
    tradeCards = tradeCards.query(f'quantity > 0 and rarityOrder > 2 and rarityOrder < {trade_rarity_threshold} and set_id != "PA" and set != "{active_extention}"')
    tradeCards = tradeCards.sort_values(by=['rarityOrder', 'quantity', 'set_id', 'card_id'], ascending=[False, False, True, True])
    try:
        remove('./csv_output/trade_cards.csv')
    except OSError as error:
        print(error)
        print("File path can not be removed")
    print(f'NUMBER OF TRADE CARDS: {tradeCards["set_id"].count()}')
    tradeCards = tradeCards.drop(columns=['set_id', 'recycle', 'pack', 'element', 'subtype', 'health', 'attacks', 'retreatCost', 'weakness', 'abilities'])
    tradeCards.to_csv('./csv_output/trade_cards.csv', index=False, encoding='utf-8') 
    tradeCards.sort_values(by=['card_id']).to_json('./output/trade_cards.json', orient="records", force_ascii=False)
    return tradeCards


def refreshAppData():
    # GET COLLECTION
    cards = getCards()
    collection = getCollection()
    collection = pd.merge(collection, cards, left_on=['set_id', 'card_id'], right_on=['set_id', 'card_id'], how='left')
    collection.fillna(-1, inplace = True)
    collection.replace({'pack': -1}, 'All', inplace=True)
    collection['french_name'] = collection['name'].map(translateName)
    collection['pack_french_name'] = collection['pack'].map(translateName)

    # EXPORT COLLECTION DATA
    collection[['set_id', 'card_id', 'set', 'name', 'french_name', 'quantity']].sort_values(by=['card_id']).to_json('./output/collection.json', orient="records", force_ascii=False)

    # PREPARE DATA TO CALCULATE
    rarity = getRarity()
    collectionWithInfo = pd.merge(collection, rarity, left_on=['rarityCode'], right_on=['code'], how='left').drop(columns=['rarityCode', 'code'])
    collectionWithInfo.fillna(-1, inplace = True)
    collectionWithInfo = collectionWithInfo[(collectionWithInfo['name'] != 'Old Amber') | (collectionWithInfo['set_id'] == 'A1')]
    print(f'NUMBER OF CARDS: {collectionWithInfo["quantity"].sum()}')

    # GET MISSING CARDS
    getMissingCards(collectionWithInfo)

    # GET TRADE CARDS
    tradeCards = getTradeCards(collectionWithInfo)

    # GET RECYCLE CARDS
    getRecycleCards(collectionWithInfo, tradeCards[['card_id', 'set', 'quantity']])

class ServerRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = 'index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)


        # UPDATE COLLECTION
        newCollection = pd.DataFrame(json.loads(post_data.decode('utf-8')))[["set_id", "card_id" , "quantity"]]
        newCollection.to_csv('./collection/collection.csv', index=False, encoding='utf-8')
        
        refreshAppData()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len("OK")))
        self.end_headers()
        self.wfile.write("OK".encode('utf-8'))

# Create an object of the above class
handler = ServerRequestHandler

PORT = 8000
server = socketserver.TCPServer(("", PORT), handler)

# Star the server
server.serve_forever()
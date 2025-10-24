import http.server
import socketserver
import pandas as pd
import threading
import webbrowser
from os import walk
import warnings
import json
import os
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter(action='ignore', category=DeprecationWarning)
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)
 
pd.set_option("display.max_rows", 500)

promo_sets = ['PA']
trade_rarity_threshold = 9
pull_shinies_rarity_threshold = 8
excluded_packs = ['All']

with open("./utils/french.json", encoding="utf-8") as f:
    french = json.load(f)
with open("./utils/english.json") as f:
    english = json.load(f)
with open("./collection/collections.json") as f:
    collection_names = json.load(f)

def init(collectionName):
    collectionDirectory = './collection'
    outputDirectory = './output'
    if not os.path.exists(collectionDirectory):
        os.mkdir(collectionDirectory)

    if not os.path.exists(f'{collectionDirectory}/collection_{collectionName}.csv'):
        collection = pd.DataFrame(columns=['set_id', 'card_id' ,'quantity'])
        collection.to_csv(f'./collection/collection_{collectionName}.csv', index=False, encoding='utf-8')

    if not os.path.exists(outputDirectory):
        os.mkdir(outputDirectory)

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
    cards.loc[cards['set'].str.contains("Promo"), 'rarityCode'] = 'Promo'
    cards = cards.drop(columns=['id', 'evolvesFrom', "type"])
    return cards

def getCollection(collectionName):
    collection = pd.read_csv(f'./collection/collection_{collectionName}.csv')
    return collection.drop_duplicates()

def groupMissingCards(cards):
    value = cards[cards['rarityOrder']==cards['rarityOrder'].min()]
    if(value['quantity'].sum().astype(int) == 0):
        value['quantity'] = 0
    else:
        value['quantity'] = cards['quantity'].sum()
    return value

def getMissingCards(collection, collectionName, fullCollection):
    missingCards = collection.groupby(by=["name", "element", "subtype", "health", "attacks", "weakness", "abilities"], as_index=False).apply(groupMissingCards)
    deluxeExCards = fullCollection.query(f'set_id == "A4B" and quantity < 2 and rarityOrder < 5 and rarity != -1').sort_values(by=['quantity', 'rarity', 'set', 'card_id'], ascending=[True, False, True, True])
    if not missingCards.empty:
        missingCards = missingCards.reset_index()
        missingCards = missingCards[['set_id', 'card_id', 'set', 'name', 'french_name', 'pack', 'pack_french_name','quantity', 'rarity', 'rarityOrder', 'tradeCost', 'pointCost']]
        missingCards = missingCards.query(f'quantity < 2 and rarityOrder < 5 and rarity != -1').sort_values(by=['quantity', 'rarity', 'set', 'card_id'], ascending=[True, False, True, True])
        oneStarMissing = collection.query(f'quantity == 0 and rarityOrder == 5 and rarity != -1')[['set_id', 'card_id', 'set', 'name', 'french_name', 'pack', 'pack_french_name', 'quantity', 'rarity', 'rarityOrder', 'tradeCost', 'pointCost']]
        missingCards = pd.concat([missingCards, oneStarMissing, deluxeExCards])
        missingCards = missingCards.drop_duplicates(subset=['set_id', 'card_id'])
        missingCards = missingCards.replace(-1, 'No Data').drop(columns=['set_id'])
        missingCards.sort_values(by=['card_id']).to_json(f'./output/missing_cards_{collectionName}.json', orient="records", force_ascii=False)

        return missingCards
    else:
        emptyMissingCards = pd.DataFrame(columns=["card_id", "set", "name", "french_name" ,"pack", "pack_french_name", "quantity", "rarity", "rarityOrder", "tradeCost", "pointCost"])
        emptyMissingCards.to_json(f'./output/missing_cards_{collectionName}.json', orient="records", force_ascii=False)
        return emptyMissingCards

def getRecycleCards(collection, tradeCards, collectionName):
    recycleCards = collection.query('quantity > 2 and set_id != "PA" and rarityOrder > 2')
    recycleCards['quantity'] = recycleCards['quantity'] - 2
    recycleCards['total'] = recycleCards['quantity'] * recycleCards['recycle']
    recycleCards = recycleCards.sort_values(by=['total', 'rarityOrder', 'set_id', 'card_id'], ascending=[False, False, True, True])
    recycleCards = recycleCards[['card_id', 'name', 'french_name', 'pack', 'pack_french_name', 'set', 'quantity', 'rarity', 'rarityOrder', 'recycle', 'total']]
    recycleCards = pd.merge(recycleCards, tradeCards, left_on=['set', 'card_id'], right_on=['set', 'card_id'], how='left')
    recycleCards = recycleCards.rename(columns={"quantity_x": "quantity", "quantity_y": "trade_quantity"})
    recycleCards.sort_values(by=['card_id']).to_json(f'./output/recycle_cards_{collectionName}.json', orient="records", force_ascii=False)

def groupTradeCards(cards):
    cardQuantity = cards['quantity'].sum()
    cardNumber = cards['quantity'].count()
    subtract = 2
    if(cardNumber > 1):
        subtract = 1

    if(cardQuantity > 2):
        cards['quantity'] = cards['quantity'] - subtract
        return cards

def getTradeCards(collection, collectionName):
    tradeCards = collection[collection['quantity'] > 0]
    tradeCards = tradeCards.groupby(by=["name", "element", "subtype", "health", "attacks", "weakness", "abilities"], as_index=False).apply(groupTradeCards)
    if not tradeCards.empty:
        tradeCards = tradeCards.query(f'quantity > 0 and rarityOrder < {trade_rarity_threshold}')
        tradeCards = tradeCards.sort_values(by=['rarityOrder', 'quantity', 'set_id', 'card_id'], ascending=[False, False, True, True])
        tradeCards = tradeCards.drop(columns=['set_id', 'recycle', 'pack', 'element', 'subtype', 'health', 'attacks', 'weakness', 'abilities'])
        tradeCards.sort_values(by=['card_id']).to_json(f'./output/trade_cards_{collectionName}.json', orient="records", force_ascii=False)
        return tradeCards
    else:
        emptyTradeCards = pd.DataFrame(columns=["card_id","quantity","name","set","french_name","pack_french_name","rarity","rarityOrder","tradeCost","pointCost"])
        emptyTradeCards.to_json(f'./output/trade_cards_{collectionName}.json', orient="records", force_ascii=False)
        return emptyTradeCards

def getPackPull(collection, missingCards, collectionName):
    sets = collection['set_id'].unique()
    sets = [s for s in sets if s not in promo_sets]

    pullData = [['set', 'pack', 'value']]

    for s in sets:
        setCards = collection[collection['set_id'] == s]

        packs = setCards['pack'].unique()
        packs = [pack for pack in packs if pack not in excluded_packs]

        for pack in packs:
            packCards = setCards[(setCards['pack'] == pack) | (setCards['pack'].isin(excluded_packs))]
            contains_shinies = packCards[packCards['rarityOrder'] > pull_shinies_rarity_threshold]['set_id'].count() > 0

            packCardsCount = packCards.groupby(['rarityOrder'])['set_id'].count()
            packCards['fullid'] = packCards['set'].astype(str).add('-' + packCards['card_id'].astype(str))

            possessedPackCardsCount = packCards[packCards['quantity'] > 0]
            if missingCards is not None:
                missingCards['fullid'] = missingCards['set'].astype(str).add('-' + missingCards['card_id'].astype(str))
                possessedPackCardsCount = packCards[
                    (
                        (packCards['rarityOrder'] < trade_rarity_threshold) & 
                        (~packCards['fullid'].isin(missingCards['fullid'].values.tolist()))
                    ) |
                    (
                        (packCards['rarityOrder'] >= trade_rarity_threshold) & 
                        (packCards['quantity'] > 0)
                    )
                ]
            
            possessedPackCardsCount = possessedPackCardsCount.groupby(['rarityOrder'])['set_id'].count()

            packCardsCount = pd.merge(packCardsCount, possessedPackCardsCount, left_on=['rarityOrder'], right_on=['rarityOrder'], how='left').reset_index()
            packCardsCount = packCardsCount.rename(columns={'set_id_x': 'total', 'set_id_y': 'owned'})
            packCardsCount.fillna(0, inplace = True)

            pullRates = pd.read_csv(f'./utils/pulls.csv')

            if(contains_shinies):
                pullRates = pd.read_csv(f'./utils/pulls_shiny.csv')

            packCardsCount = pd.merge(packCardsCount, pullRates, left_on=['rarityOrder'], right_on=['rarityOrder'], how='left').reset_index()
        
            packCardsCount['New-Card_1-3'] = (packCardsCount['1'] / packCardsCount['total'])*packCardsCount['owned']/100
            packCardsCount['New-Card_4'] = (packCardsCount['4'] / packCardsCount['total'])*packCardsCount['owned']/100
            packCardsCount['New-Card_5'] = (packCardsCount['5'] / packCardsCount['total'])*packCardsCount['owned']/100
            packCardsCount = packCardsCount.sum()

            chanceNewCard = round((1 - ( packCardsCount['New-Card_1-3'] * packCardsCount['New-Card_4'] * packCardsCount['New-Card_5'])) * 100, 1)

            pullData.append([s, pack, chanceNewCard])
    
    pullData = pd.DataFrame(pullData)
    pullData.columns = pullData.iloc[0]
    pullData = pullData.iloc[1:]
    pullData['pack_french_name'] = pullData['pack'].map(translateName)

    if missingCards is not None:
        pullData.to_json(f'./output/pulls_full_{collectionName}.json', orient="records", force_ascii=False)
    else:
        pullData.to_json(f'./output/pulls_{collectionName}.json', orient="records", force_ascii=False)

def getDecks(missingCards, fullCollection, collectionWithInfo, collectionName):
    decks = []
    files = next(walk('./decks'), (None, None, []))[2]
    for file in files:
       with open(f'./decks/{file}', encoding="utf-8") as f:
            deck = json.load(f)

            def groupRarityCards(cards):
                value = cards[cards['rarityOrder']==cards['rarityOrder'].min()]
                value['quantity'] = cards['quantity'].sum()
                return value

            collectionWithRare = collectionWithInfo.groupby(by=["name", "element", "subtype", "health", "attacks", "weakness", "abilities"], as_index=False).apply(groupRarityCards)

            deckCards = []

            for card in deck["cards"]:
                card_info = fullCollection.query(f'card_id == {card['card_id']} and set == "{card['set']}"')[["card_id", "set", "set_id", "name", "french_name", "pack", "pack_french_name"]].to_dict('records')[0]
                missingCard = missingCards.query(f'card_id == {card['card_id']} and set == "{card['set']}"')
                card_info["count"] = card["quantity"]
                if missingCard.empty:
                    card_info["quantity"] = card["quantity"]
                    deckCards.append(card_info)
                else:
                    cardWithRareCount = collectionWithRare[(collectionWithRare["set"] == card["set"]) & (collectionWithRare["card_id"] == card["card_id"])]
                    card_info["quantity"] = cardWithRareCount["quantity"].values[0].tolist()
                    deckCards.append(card_info)

            decks.append({
                "name": deck["name"],
                "french_name": deck["french_name"],
                "cards": deckCards
            })
    
    with open(f"./output/decks_{collectionName}.json", "w", encoding='utf-8') as f:
        json.dump(decks, f, ensure_ascii=False)

def filterPackDuplicates(collectionWithInfo):
    with open("./utils/duplicates.json", encoding="utf-8") as f:
        duplicates = json.load(f)

    pack_exclusion = []
    for duplicate_list in duplicates:
        duplicate_list.pop(0)
        for duplicate in duplicate_list:
            duplicate['set_id'] = duplicate['set_id'].upper()
            pack_exclusion.append(duplicate)

    for exclusion in pack_exclusion:
        collectionWithInfo = collectionWithInfo[(collectionWithInfo['card_id'] != exclusion["card_id"]) | (collectionWithInfo['set_id'] != exclusion["set_id"])]

    return collectionWithInfo

def refreshAppData(collectionName):
    print(f'START REFRESH COLLECTION: {collectionName}')
    init(collectionName)

    # GET COLLECTION
    cards = getCards()
    collection = getCollection(collectionName)
    rarity = getRarity()

    # EXPORT DECK CARDS DATA
    decksCards = pd.merge(cards, rarity, left_on=['rarityCode'], right_on=['code'], how='left').drop(columns=['rarityCode', 'code'])
    decksCards = decksCards.query(f'rarityOrder < 5 or set.str.contains("Promo")')
    decksCards['french_name'] = decksCards['name'].map(translateName)
    decksCards[['set_id', 'card_id', 'set', 'name', 'french_name']].sort_values(by=['card_id']).to_json(f'./output/deck_cards_{collectionName}.json', orient="records", force_ascii=False)

    # EXPORT COLLECTION DATA
    fullCollection = pd.merge(cards, collection, left_on=['set_id', 'card_id'], right_on=['set_id', 'card_id'], how='left')
    fullCollection = pd.merge(fullCollection, rarity, left_on=['rarityCode'], right_on=['code'], how='left').drop(columns=['code'])
    fullCollection['quantity'] = fullCollection['quantity'].astype(float).fillna(value=0)
    fullCollection.fillna(-1, inplace = True)
    fullCollection.replace({'pack': -1}, 'All', inplace=True)
    fullCollection['french_name'] = fullCollection['name'].map(translateName)
    fullCollection['pack_french_name'] = fullCollection['pack'].map(translateName)
    fullCollection[['set_id', 'card_id', 'set', 'name', 'french_name', 'quantity', 'rarityOrder']].sort_values(by=['card_id']).to_json(f'./output/collection_{collectionName}.json', orient="records", force_ascii=False)

    # PREPARE COLLECTION FOR CALCULATION
    collection = pd.merge(collection, cards, left_on=['set_id', 'card_id'], right_on=['set_id', 'card_id'], how='left')
    collection.fillna(-1, inplace = True)
    collection.replace({'pack': -1}, 'All', inplace=True)
    collection['french_name'] = collection['name'].map(translateName)
    collection['pack_french_name'] = collection['pack'].map(translateName)

    # PREPARE DATA TO CALCULATE
    collectionWithInfo = pd.merge(collection, rarity, left_on=['rarityCode'], right_on=['code'], how='left').drop(columns=['rarityCode', 'code'])
    collectionWithInfo.fillna(-1, inplace = True)
    fullCollectionWithInfo = pd.merge(collection, rarity, left_on=['rarityCode'], right_on=['code'], how='left').drop(columns=['rarityCode', 'code'])
    fullCollectionWithInfo.fillna(-1, inplace = True)

    # FILTER PACK DUPLICATE CARDS
    collectionWithInfo = filterPackDuplicates(collectionWithInfo)

    # GET MISSING CARDS
    missingCards = getMissingCards(collectionWithInfo, collectionName, fullCollectionWithInfo)

    # GET DECKS
    getDecks(missingCards, fullCollection, collectionWithInfo, collectionName)

    # GET TRADE CARDS
    tradeCards = getTradeCards(collectionWithInfo, collectionName)

    # GET RECYCLE CARDS
    getRecycleCards(collectionWithInfo, tradeCards[['card_id', 'set', 'quantity']], collectionName)

    #GET PACKS PULLS
    getPackPull(collectionWithInfo, None, collectionName)
    getPackPull(collectionWithInfo, missingCards, collectionName)

    print(f'END REFRESH COLLECTION: {collectionName}')

def refreshGlobalAppData(collection_name):
    if collection_name == 'ALL':
        for collection in collection_names:
            refreshAppData(collection["name"])
    else:
        refreshAppData(collection_name)

refreshGlobalAppData('ALL')

class ServerRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = 'index.html'

        for name in [collection["name"] for collection in collection_names]:
            if self.path == f'/{name}':
                self.path = 'app.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        if self.path == '/deck':
            # ADD NEW DECK
            deck = json.loads(post_data.decode('utf-8'))
            with open(f'./decks/{deck["name"]}.json', 'w') as d:
                json.dump(deck, d)
            refreshGlobalAppData('ALL')

        elif '/collection' in self.path :
            # UPDATE COLLECTION
            collection_name = self.path.replace("/collection/", "")
            print(f'SAVE COLLECTION: {collection_name}')
            newCollection = pd.DataFrame(json.loads(post_data.decode('utf-8')))[["set_id", "card_id" , "quantity"]]
            newCollection.to_csv(f'./collection/collection_{collection_name}.csv', index=False, encoding='utf-8')
        
            refreshGlobalAppData(collection_name)

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len("OK")))
        self.end_headers()
        self.wfile.write("OK".encode('utf-8'))

# Create an object of the above class
handler = ServerRequestHandler

PORT = 80
server = socketserver.TCPServer(("", PORT), handler)

# Star the server

threading.Thread(target=server.serve_forever).start()

webbrowser.open('http://localhost', new=2)
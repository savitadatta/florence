from difflib import SequenceMatcher
from triples import call_stanford_nlp, run

# def similarity(a, b):
#     # https://stackoverflow.com/questions/17388213/find-the-similarity-metric-between-two-strings
#     return SequenceMatcher(None, a, b).ratio()

user = "user"

def get_location_triples(input, relation, keyword, pos):
    results = []
    analysis = run(input)
    
    if len(analysis) < 1:
        sentenceJson = call_stanford_nlp(input, ['ner'])
        entities = sentenceJson['sentences'][0]['entitymentions']
        for e in entities:
            if 'LOCATION' in e["nerConfidences"].keys() and e["nerConfidences"]['LOCATION'] > 0.5:
                results.append((user, relation, e['text']))
        return results
    else:
        locations = []
        noLocation = []
        full = []
        partial = []
        for result in analysis:
            negation = any(neg in result[1] for neg in ["not", "n't", "never"])
            joined = ''.join(["not_" if negation else "", relation]).strip()
            rel = relation.replace('_', ' ')

            if any(keyword in part for part in result):
                replaced = result[pos].replace(rel + ' ', '')

                sentenceJson = call_stanford_nlp(result[2], ['ner'])
                entities = sentenceJson['sentences'][0]['entitymentions']
                somethingAdded = False

                for e in entities:
                    if 'LOCATION' in e["nerConfidences"].keys() and e["nerConfidences"]['LOCATION'] > 0.5:
                        suggestion = (result[0], joined, e['text'])
                        locations.append(suggestion)
                        if result not in locations:
                            locations.append(result)
                        somethingAdded = True
                if len(entities) == 0 or not somethingAdded:
                    suggestion = (result[0], joined, result[2] if pos == 1 else replaced)
                    noLocation.append(suggestion)
                    noLocation.append(result)
            else:
                if all([len(part) > 0 for part in result]):
                    full.append(result)
                else:
                    partial.append(result)
        # print("RES locations: ", str(locations))
        # print("CLA no locations found: ", str(noLocation))
        # print("CLA full triples: ", str(full))
        # print("ERR partial triples: ", str(partial))
        return locations + noLocation + full

def call_location(input, relation, keyword, pos):
    print("input:", input)
    result = get_location_triples(input, relation, keyword, pos)
    if result:
        print(str(result) + "\n")
    else:
        print("no results\n")
    return result

def live_in(input):
    call_location(input, "live_in", "live", 1)

def born_in(input):
    call_location(input, "born_in", "born", 2)

born = [
    "Logan",
    "I was born in Hong Kong",
    "I was born in Hong Kong but my sister was born in Logan",
    "I was born in a town out west",
    "I'd like to do some gardening now",
    "I don't remember",
    "I was not born in Brisbane"
]
live = [
    "I live in Logan",
    "I don't live in Brisbane",
    "I live between Brisbane and the Gold Coast",
    "I live with my family just outside Brisbane",
    "I spend part of my week in Brisbane and the other part on the Granite Belt",
    "My parents live in Dalveen, which is near Stanthorpe and Warwick",
    "They used to live here in Logan but now they're out in the country",
    "I live with my dog Speedy",
]

# init_names()
for s in born:
    born_in(s)
for s in live:
    live_in(s)

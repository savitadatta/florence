from triples_module import run, call_annotator, split_input

user = 'user'
{
# def get_triples_time(input, relation, keyword, pos):
#     results = []
#     analysis = run(input)
    
#     if len(analysis) < 1:
#         sentenceJson = call_stanford_nlp(input, ['ner'])
#         sentenceJson = sentenceJson['sentences'][0]
#         entities = sentenceJson['entitymentions']
#         for e in entities:
#             if e['ner'] in ['NUMBER', 'TIME']:
#                 results.append((user, relation, e['text']))
#         return results
#     else:
#         for result in analysis:
#             negation = any(neg in result[1] for neg in ["not", "n't", "never"])
#             joined = ''.join(["not_" if negation else "", relation]).strip()
#             rel = relation.replace('_', ' ')

#             if any(keyword in part for part in result):
#                 replaced = result[pos].replace(rel + ' ', '')

#                 if not result[2]:
#                     print("no third part")
#                     results.append(result)
#                     continue
#                 sentenceJson = call_stanford_nlp(result[2], ['ner'])
#                 entities = sentenceJson['sentences'][0]['entitymentions']
#                 somethingAdded = False

#                 for e in entities:
#                     if e['ner'] in ['NUMBER', 'TIME']:
#                         suggestion = (result[0], joined, e['normalizedNER'])
#                         results.append(suggestion)
#                         somethingAdded = True
#                 if len(entities) == 0 or not somethingAdded:
#                     suggestion = (result[0], joined, result[2] if pos == 1 else replaced)
#                     results.append(suggestion)
#                     results.append(result)
#             else:
#                 if all([len(part) > 0 for part in result]):
#                     results.append(result)
#                 else:
#                     print("ERR ", str(result))
#                     results.append(result)
#         return results
}

def only_complement(triple):
    return len(triple[0]) == 0 and len(triple[1]) == 0 and len(triple[2]) != 0

def times(input, relation, keywords):
    CATEGORIES = ['NUMBER', 'TIME']
    number = []
    keyword = []
    other = []
    subj = ''
    rel = ''
    
    phrases = split_input(input)

    for phrase in phrases:
        entities = call_annotator(phrase, ['ner'], 'entitymentions')
        analysis = run(phrase)

        if len(analysis) == 1:
            # this should be true
            analysis = analysis[0]
        else:
            # an error has occurred
            continue
        
        if len(analysis[0]) == 0:
            if len(subj) == 0:
                subj = user
        else:
            subj = analysis[0]

        if len(analysis[0]) == 0:
            if len(rel) == 0:
                rel = relation
        else:
            rel = analysis[1]

        if any([word in phrase for word in keywords]):
            hasNumbers = [e for e in entities if e['ner'] in CATEGORIES]
            for e in hasNumbers:
                suggestions = [
                    (subj, relation, e['normalizedNER']),
                    # (subj, rel, e['normalizedNER']),
                    (subj, rel, analysis[2])
                    ]
                for s in suggestions:
                    if s not in number:
                        number.append(s)
            if len(hasNumbers) == 0:
                keyword.append((subj, rel, analysis[2]))
        else:
            hasNumbers = []
            if only_complement(analysis):
                hasNumbers = [e for e in entities if e['ner'] in CATEGORIES]
                for e in hasNumbers:
                    suggestions = [
                        (subj, relation, e['normalizedNER']),
                        # (subj, rel, e['normalizedNER']),
                        # (subj, rel, analysis[2])
                        ]
                    for s in suggestions:
                        if s not in number:
                            number.append(s)
            if len(hasNumbers) == 0:
                other.append((subj, rel, analysis[2]))
    return number + keyword + other

def call_times(input, relation, keywords):
    print("input: ", input)
    result = times(input, relation, keywords)
    if result:
        print(str(result) + "\n")
    else:
        print("no results\n")
    return result

def wake_at(input):
    return call_times(input, "wake_at", ["wake", "get up", "woken"])

def eat_at(input):
    return call_times(input, "eat_at", ["eat", "breakfast", "lunch", "dinner", "supper", "snack"])

def sleep_at(input):
    return call_times(input, "sleep_at", ["sleep", "to bed", "asleep"])

wake = [
    "7am",
    "she likes to wake up around 7",
    "I like to get up around 7 o'clock",
    "He doesn't like being woken up before 8am",
    "I like to wake up between 6 and 8 o'clock",
    "She goes to work by 7 but I work at home so I can wake up at quarter to 7",
    "I like to wake up pretty early",
    "I wake up around 7 but my sister likes to wake up at 6am",
    "If I'm going into the office I'll wake up at 6, because I have to leave the house by 7",
    "I go to bed at 11pm",
    "I have three cats",
    "She goes to work by 7 but I work at home",
    "They both go to work by bus",
    "I wake my dogs",
    "I wake my 3 dogs",
    "At 7 I get up and water my three rose bushes"
]

eat = [
    "I like to have breakfast at 7am",
    "My sister will often have dinner around 9pm",
    "I eat lunch whenever I feel like it",
    "I eat breakfast around 8",
    "My dog has 2 meals a day",
    "We used to have four chickens",
    "I like to eat breakfast foods",
    "I like to have breakfast around 8 but I'll have lunch whenever the mood strikes",
    "I like to have breakfast around 8 and I'll usually have lunch about 1pm"
]

sleep = [
    "I try to go to sleep around 11pm",
    "I get out of bed at 7am",
    "She goes to bed at 9",
    "I try to get 7 and a half hours of sleep a night",
    "My dog likes to be asleep before midnight",
    "I sleep with 3 pillows",
    "I like to sleep"
]

for s in wake:
    wake_at(s)
for s in eat:
    eat_at(s)
for s in sleep:
    sleep_at(s)

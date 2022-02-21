from triples_module import find_subject_phrase, run, call_stanford_nlp, call_annotator, split_input

user = 'user'

def get_triples_time(input, relation, keyword, pos):
    results = []
    analysis = run(input)
    
    if len(analysis) < 1:
        sentenceJson = call_stanford_nlp(input, ['ner'])
        sentenceJson = sentenceJson['sentences'][0]
        entities = sentenceJson['entitymentions']
        for e in entities:
            if e['ner'] in ['NUMBER', 'TIME']:
                results.append((user, relation, e['text']))
        return results
    else:
        for result in analysis:
            negation = any(neg in result[1] for neg in ["not", "n't", "never"])
            joined = ''.join(["not_" if negation else "", relation]).strip()
            rel = relation.replace('_', ' ')

            if any(keyword in part for part in result):
                replaced = result[pos].replace(rel + ' ', '')

                if not result[2]:
                    print("no third part")
                    results.append(result)
                    continue
                sentenceJson = call_stanford_nlp(result[2], ['ner'])
                entities = sentenceJson['sentences'][0]['entitymentions']
                somethingAdded = False

                for e in entities:
                    if e['ner'] in ['NUMBER', 'TIME']:
                        suggestion = (result[0], joined, e['normalizedNER'])
                        results.append(suggestion)
                        somethingAdded = True
                if len(entities) == 0 or not somethingAdded:
                    suggestion = (result[0], joined, result[2] if pos == 1 else replaced)
                    results.append(suggestion)
                    results.append(result)
            else:
                if all([len(part) > 0 for part in result]):
                    results.append(result)
                else:
                    print("ERR ", str(result))
                    results.append(result)
        return results


def only_complement(triple):
    return len(triple[0]) == 0 and len(triple[1]) == 0 and len(triple[2]) != 0

def times(input, relation, keywords, pos):
    phrases = split_input(input)
    subj = ''
    rel = ''
    CATEGORIES = ['NUMBER', 'TIME']
    number = []
    keyword = []
    other = []

    for phrase in phrases:
        print("phrase: " + phrase)
        entities = call_annotator(phrase, ['ner'], 'entitymentions')
        analysis = run(phrase)

        if len(analysis) == 1:
            # this should be true
            analysis = analysis[0]
        else:
            # an error has occurred
            continue
        
        if len(analysis[0]) == 0 and len(analysis[1]) == 0:
            if len(subj) == 0 and len(rel) == 0:
                subj = user
                rel = relation
        else:
            subj = analysis[0]
            rel = analysis[1]

        if any([word in phrase for word in keywords]):
            hasNumbers = [e for e in entities if e['ner'] in CATEGORIES]
            for e in hasNumbers:
                suggestions = [
                    (subj, relation, e['normalizedNER']),
                    # (subj, rel, e['normalizedNER']),
                    # (subj, rel, analysis[2])
                    ]
                for s in suggestions:
                    # print("keyword number " + str(s))
                    if s not in number:
                        number.append(s)
            if len(hasNumbers) == 0:
                # print("keyword " + str((subj, rel, analysis[2])))
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
                        # print("number " + str(s))
                        if s not in number:
                            number.append(s)
            if len(hasNumbers) == 0:
                # print("other " + str((subj, rel, analysis[2])))
                other.append((subj, rel, analysis[2]))
    print(str(number + keyword + other) + "\n")



sentences = [
    "7am",
    "she likes to wake up around 7",
    "I like to get up around 7 o'clock",
    "He doesn't like being woken up before 8am",
    "I like to wake up between 6 and 8",
    "I like to wake up between 6 and 8 o'clock",
    "She goes to work by 7 but I work at home so I can wake up at quarter to 7",
    "I like to wake up pretty early",
    "I wake up around 7 but my sister likes to wake up at 6am",
    "If I'm going into the office I'll wake up at 6, because I have to leave the house by 7",
    "I go to bed at 11pm",
    "I have three cats"
]

for s in sentences:
    times(s, "wake_at", ["wake", "get up", "woken"], 1)
#     print("\n" + s)
#     print(get_triples_time(s, "wake_at", "wake", 1))

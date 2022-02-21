import string
from stanza.server import CoreNLPClient
from parse_tree import split_sentence
import nltk.data
from test_sentences import *


def call_stanford_nlp(text, annotators):
    ann = ",".join(annotators)
    with CoreNLPClient( start_server="DONT_START", endpoint='https://corenlp.uqcloud.net:443') as client:
        props = {'annotators': ann,
                 'pipelineLanguage': 'en', 'outputFormat': 'json'}
        ann = client.annotate(text, username='corenlp', password='8zIJDWrMGTck', properties=props)
    return ann


def get_dependencies(json, word, startsWith, exclude=[]):
    """
    Returns a list of tokens with a dependency on the token defined in <startsWith>.
    :param json: dictionary of CoreNLP basic dependencies
    :param word: the word whose dependencies are being sought
    :param startsWith: <List> of acceptable category prefixes (e.g. nsubj, obj, obl, etc.)
    :param exclude: <List> of category prefixes to exclude (e.g. nsubj, obj, obl, etc.)
    :return: <List> of (index, word) tuples of words governed by <startsWith>
    """
    result = []
    result.extend([(w["dependent"], w["dependentGloss"]) for w in json \
        if w["governorGloss"] == word and \
            ((w["dep"]).startswith(tuple(startsWith)) and not (w["dep"]).startswith(tuple(exclude)))])
    if len(result) == 0:
        return None
    
    if len(result) == 1 and result[0][1] == word:
        return result

    add = []
    for w in result:
        dep = get_dependencies(json, w[1], startsWith)
        if dep:
            add.extend(dep)

    result.extend(add)
    return result

def find_subject(basicDependencies, rootPos):
    """
    Determines the first part of a triple - the subject of the sentence.
    :param basicDependencies: dictionary of CoreNLP basic dependencies
    :param rootPos: index of the root of this clause
    :return: <str> of the first part of the triple
    """
    subj_root = None
    for word in basicDependencies:
        if word["governor"] == rootPos and (word["dep"]).startswith("nsubj"):
            subj_root = (word["dependent"], word["dependentGloss"])
            break

    if not subj_root:
        return None

    subject = [subj_root]
    toAdd = get_dependencies(basicDependencies, subj_root[1], [""])
    if toAdd:
        subject.extend(toAdd)
    subject.sort()
    result = " ".join([tok[1] for tok in subject])
    return result

def find_verb_phrase(basicDependencies, tokens, rootPos):
    """
    Determines the second part of a triple - the relation, or verb phrase.
    :param basicDependencies: dictionary of CoreNLP basic dependencies
    :param tokens: dictionary of CoreNLP data about each token in the sentence
    :param rootPos: index of the root of this clause
    :return: <str> of the second part of the triple
    """
    isY = None
    for word in basicDependencies:
        if word["dep"] in ["aux:pass", "cop"] and word["governor"] == rootPos:
            isY = word["dependent"], word["dependentGloss"]

    result = []
    [root] = [(word["dependent"], word["dependentGloss"]) for word in basicDependencies \
        if word["dependent"] == rootPos]
    if isY:
        result = [isY]
    else:
        if not tokens[root[0] - 1]["pos"].startswith(("N", "CD")):
            result = [(root[0], root[1])]
    toAdd = get_dependencies(basicDependencies, root[1],
        ["dep", "aux", "neg", "advmod", "xcomp", "ccomp", "mark", "case", "nummod"])
    if toAdd:
        result.extend(toAdd)

    if len(result) == 1 and tokens[result[0][0] - 1]["pos"] == "CD":
        result = []
    else:
        result = list(dict.fromkeys(result))
        result.sort()
    if len(result) == 0:
        vpos = -1
    else:
        vpos = result[-1][0]

    joined = " ".join([tok[1] for tok in result])
    joined = joined.replace("'m", "am")
    joined = joined.replace("wo n't", "will not")
    joined = joined.replace("ca n't", "cannot")
    joined = joined.replace("n't", "not")
    return joined, vpos

def find_final_part(basicDependencies, rootPos, startIndex, endIndex):
    """
    Determines the final part of a triple - the object, prepositional phrase, or other auxiliary information.
    :param basicDependencies: dictionary of CoreNLP basic dependencies
    :param rootPos: index of the root of this clause
    :param startIndex: index of the position before the first word of this clause
    :param endIndex: index of the position after the last word of this clause
    :return: <str> of the third part of the triple
    """
    [root] = [(word["dependent"], word["dependentGloss"]) for word in basicDependencies \
        if word["dependent"] == rootPos]
    result = [root]
    toAdd = get_dependencies(basicDependencies, root[1], string.ascii_letters)
    if toAdd:
        result.extend(toAdd)

    newResult = filter(lambda word: (startIndex < word[0] < endIndex), result)
    result = list(dict.fromkeys(newResult))
    result.sort()
    return " ".join([word[1] for word in result])

def separate_sentence(basicDependencies):
    """
    Splits a sentence based on the locations of the conjunctions between clauses.
    :param basicDependencies: dictionary of CoreNLP basic dependencies
    :return: tuple of root and conjunction index lists for each clause
    """
    [root] = [(w["dependent"], w["dependentGloss"]) for w in basicDependencies if w["dep"] == "ROOT"]
    connections = [root[0]] + [w["dependent"] for w in basicDependencies \
        if w["governor"] == root[0] and w["dep"] == "conj"]
    andIndex = len(basicDependencies) + 1
    return connections, andIndex

def handle_sentence(sentence):
    result = []
    verb = ''

    # print("\nsentence: ", sentence)

    splitWords = [' and ', ' but ', ' because ', ', so ']
    for word in splitWords:
        sentence = sentence.replace(word, ' CONJ ')
    sentences = sentence.split(' CONJ ')

    for sentence in sentences:
        sentenceJson = call_stanford_nlp(sentence, ['depparse'])
        sentenceJson = sentenceJson["sentences"][0]
        basicDependencies = sentenceJson["basicDependencies"]
        roots, conj = separate_sentence(basicDependencies)

        for i in range(len(roots)):
            root = roots[i]
            subject = find_subject(basicDependencies, root)

            oldVerb = verb
            try:
                newVerb, vpos = find_verb_phrase(basicDependencies, sentenceJson["tokens"], root)
            except RecursionError:
                continue
            if not newVerb:
                newVerb = verb
            else:
                verb = newVerb
            # if not newVerb:
            #     continue

            try:
                end = conj
                if len(roots) > i + 1:
                    end = min(conj, roots[i + 1])
                part3 = find_final_part(basicDependencies, root, vpos, end)
                if not part3:
                    part3 = " ".join(tok["word"] for tok in sentenceJson["tokens"] if vpos + 1 < tok["index"] < conj)
            except RecursionError:
                part3 = " ".join(tok["word"] for tok in sentenceJson["tokens"] if vpos + 1 < tok["index"] < conj)
            # if len(part3) == 0 and len(oldVerb) > 0:
            #     result.extend([(subject, oldVerb, verb)])
            # else:
            if not subject and not verb:
                return None
            result.extend([(subject, verb, part3)])
            oldVerb = verb

    return result

def run(input):
    inferences = []
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    input = input.translate(str.maketrans(';','.'))
    sentences = tokenizer.tokenize(input)
    oldSubj = ''
    subj = ''
    oldVerb = ''
    verb = ''

    for sentence in sentences:
        sentence = sentence.translate(str.maketrans('', '', '.'))
        result = handle_sentence(sentence)
        if result:
            for res in result:
                subj, verb = res[0], res[1]
                
                if not subj:
                    subj = oldSubj
                if not verb:
                    verb = oldVerb
                
                res = (subj, verb, res[2])
                if res not in inferences:
                    inferences.append(res)
                oldSubj = subj
                oldVerb = verb

    # print(inferences)
    return inferences

# for s in split_sentences:
#     print(run(s))

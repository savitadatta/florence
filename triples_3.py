from test_sentences import *
from stanza.server import CoreNLPClient
import nltk.data
import string

def call_stanford_nlp(text):
    '''
    Fetch the results from corenlp.
    (Existing code from the Florence project)
    param:
        <str> text to analyse
    returns:
        <str> json result
    '''
    with CoreNLPClient( start_server="DONT_START", endpoint='https://corenlp.uqcloud.net:443') as client:
        props = {'annotators': 'openie,sentiment,depparse',
                 'pipelineLanguage': 'en', 'outputFormat': 'json'}
        ann = client.annotate(text, username='corenlp', password='8zIJDWrMGTck', properties=props)
    return ann

def get_dependencies(json, word, startsWith):
    """
    Returns a list of tokens with a dependency on the token defined in <startsWith>.
    :param json: dictionary of CoreNLP basic dependencies
    :param word: the word whose dependencies are being sought
    :param startsWith: <List> of acceptable category prefixes (e.g. nsubj, obj, obl, etc.)
    :return: <List> of (index, word) tuples of words governed by <startsWith>
    """
    result = []
    result.extend([(w["dependent"], w["dependentGloss"]) for w in json \
        if w["governorGloss"] == word and (w["dep"]).startswith(tuple(startsWith))])
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
        if not tokens[root[0] - 1]["pos"].startswith("N"):
            result = [(root[0], root[1])]
    toAdd = get_dependencies(basicDependencies, root[1],
        ["dep", "aux", "neg", "advmod"])
    if toAdd:
        result.extend(toAdd)
    result = list(dict.fromkeys(result))
    result.sort()

    joined = " ".join([tok[1] for tok in result])
    return joined, result[-1][0]

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
    ands = [w["dependent"] for w in basicDependencies \
        if w["governor"] in [conn for conn in connections] and w["dep"] == "cc"]
    ands.append(len(basicDependencies) + 1)
    return connections, ands

def handle_sentence(sentence):
    """
    Takes a sentence and tries to extract triples.
    :param sentence: input sentence to extract triples from
    :return: <List> of triples
    """
    sentenceJson = call_stanford_nlp(sentence)
    sentenceJson = sentenceJson["sentences"][0]
    basicDependencies = sentenceJson["basicDependencies"]
    tripleOutput = []
    subject = ''

    roots, conjunctions = separate_sentence(basicDependencies)

    for i in range(len(roots)):
        root = roots[i]
        conj = conjunctions[i]
        
        newSubject = find_subject(basicDependencies, root)
        if not newSubject:
            newSubject = subject
        else:
            subject = newSubject
        verb, vpos = find_verb_phrase(basicDependencies, sentenceJson["tokens"], root)
        try:
            part3 = find_final_part(basicDependencies, root, vpos, conj)
        except RecursionError:
            end = conjunctions[i]
            part3 = " ".join(tok["word"] for tok in sentenceJson["tokens"] if vpos + 1 < tok["index"] < end)
        tripleOutput.extend([(subject, verb, part3)])

    return tripleOutput

def main(input):
    inferences = []
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    sentences = tokenizer.tokenize(input)

    for sentence in sentences:
        result = handle_sentence(sentence)
        for res in result:
            if res not in inferences:
                inferences.append(res)
    print(inferences)
    return inferences


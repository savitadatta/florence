import string
from stanza.server import CoreNLPClient
import nltk.data
from test_sentences import *

def call_stanford_nlp(text, annotators):
    ann = ",".join(annotators)
    with CoreNLPClient( start_server="DONT_START", endpoint='https://corenlp.uqcloud.net:443') as client:
        props = {'annotators': ann,
                 'pipelineLanguage': 'en', 'outputFormat': 'json'}
        ann = client.annotate(text, username='corenlp', password='8zIJDWrMGTck', properties=props)
    return ann

def call_annotator(text, annotators, key):
    sentenceJson = call_stanford_nlp(text, annotators)
    sentenceJson = sentenceJson["sentences"][0]
    return sentenceJson.get(key)

def get_dependencies(json, index, startsWith=[""], exclude=[]):
    """
    Returns a list of tokens with a dependency on the token defined in <startsWith>.
    :param json: dictionary of CoreNLP basic dependencies
    :param word: the index of the word whose dependencies are being sought
    :param startsWith: <List> of acceptable category prefixes (e.g. nsubj, obj, obl, etc.)
    :param exclude: <List> of category prefixes to exclude (e.g. nsubj, obj, obl, etc.)
    :return: <List> of (index, word) tuples of words governed by <startsWith>
    """
    result = []
    result.extend([(w["dependent"], w["dependentGloss"]) for w in json \
        if w["governor"] == index and \
            ((w["dep"]).startswith(tuple(startsWith)) and not (w["dep"]).startswith(tuple(exclude)))])
    if len(result) == 0:
        return None
    
    if len(result) == 1 and result[0][0] == index:
        return result

    add = []
    for w in result:
        dep = get_dependencies(json, w[0], startsWith, exclude)
        if dep:
            add.extend(dep)

    result.extend(add)
    return result

def split_input(input):
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    input = input.translate(str.maketrans(';', '.'))
    sentences = tokenizer.tokenize(input)

    all = []
    for sentence in sentences:
        sentence = sentence.translate(str.maketrans('', '', '.'))
        splitWords = [' and ', ' but ', ' because ', ', so ']
        for word in splitWords:
            sentence = sentence.replace(word, ' CONJ ')
        split = sentence.split(' CONJ ')
        all.extend(split)
    return all

def get_root(basicDependencies):
    [root] = [(w["dependent"], w["dependentGloss"]) for w in basicDependencies if w["dep"] == "ROOT"]
    return root

def join(listOfTuples):
    result = " ".join([tok[1] for tok in listOfTuples])
    return result

def get_indices(listOfTuples):
    return [tok[0] for tok in listOfTuples]

def remove_contractions(listOfTuples):
    joined = join(listOfTuples)
    joined = joined.replace("'m", "am")
    joined = joined.replace("wo n't", "won't")
    joined = joined.replace("ca n't", "can't")
    joined = joined.replace("n't", "not")
    return joined


def find_subject(basicDependencies, rootPos):
    """
    Determines the first part of a triple - the subject of the sentence.
    :param basicDependencies: dictionary of CoreNLP basic dependencies
    :param rootPos: index of the root of this clause
    :return: List<Tuple<int, str>> of the first part of the triple
    """
    subj_root = None
    for word in basicDependencies:
        if word["governor"] == rootPos \
                and (word["dep"]).startswith("nsubj"):
            subj_root = (word["dependent"], word["dependentGloss"])
    if not subj_root:
        return None

    subject = [subj_root]
    toAdd = get_dependencies(basicDependencies, subj_root[0])
    
    if toAdd:
        subject.extend(toAdd)
    subject.sort()
    return subject

def find_subject_phrase(sentence):
    json = call_annotator(sentence, ['depparse'], 'basicDependencies')
    try:
        result = join(find_subject(json, get_root(json)))
    except Exception:
        return ""
    return result

def find_verb(basicDependencies, tokens, rootPos):
    """
    Determines the second part of a triple - the relation, or verb phrase.
    :param basicDependencies: dictionary of CoreNLP basic dependencies
    :param tokens: dictionary of CoreNLP data about each token in the sentence
    :param rootPos: index of the root of this clause
    :return: List<Tuple<int, str>> of the second part of the triple
    """
    isY = None
    for word in basicDependencies:
        if word["dep"] in ["aux:pass", "cop"] and word["governor"] == rootPos:
            isY = word["dependent"], word["dependentGloss"]

    result = []
    [root] = [(word["dependent"], word["dependentGloss"]) \
        for word in basicDependencies if word["dependent"] == rootPos]
    if isY:
        result = [isY]
    else:
        if not tokens[root[0] - 1]["pos"].startswith(("N", "CD")):
            result = [root]
    
    toAdd = get_dependencies(basicDependencies, root[0],
        ["dep", "aux", "neg", "advmod", "xcomp", "ccomp", "mark", "case", "nummod"])
    if toAdd:
        result.extend(toAdd)

    if len(result) == 1 and tokens[result[0][0] - 1]["pos"] == "CD":
        result = []
    else:
        result = list(dict.fromkeys(result))
        result.sort()
    # if len(result) == 0:
    #     vpos = -1
    # else:
    #     vpos = result[-1][0]
    return result

def find_verb_phrase(sentence):
    json = call_stanford_nlp(sentence, ['depparse'])
    try:
        result = join(find_verb(json['basicDependencies'], json['tokens'], get_root(json['basicDependencies'])))
    except Exception:
        return ""
    return result

def find_complement(basicDependencies, rootPos, subjIndices, verbIndices):
    """
    Determines the final part of a triple - the object, prepositional phrase, or other auxiliary information.
    :param basicDependencies: dictionary of CoreNLP basic dependencies
    :param rootPos: index of the root of this clause
    :param startIndex: index of the position before the first word of this clause
    :param endIndex: index of the position after the last word of this clause
    :return: List<Tuple<int, str>> of the third part of the triple
    """
    [root] = [(word["dependent"], word["dependentGloss"]) for word in basicDependencies \
        if word["dependent"] == rootPos]
    result = [root]

    toAdd = get_dependencies(basicDependencies, root[0])
    if toAdd:
        result.extend(toAdd)

    newResult = filter(lambda word: (
        all(word[0] > subj for subj in subjIndices) and
        word[0] not in subjIndices + verbIndices), result)
    result = list(dict.fromkeys(newResult))
    result.sort()
    return result


def run(input):
    result = []
    sentences = split_input(input)
    oldSubject = ''
    oldVerb = ''

    for sentence in sentences:
        sentenceJson = call_stanford_nlp(sentence, ['depparse'])
        sentenceJson = sentenceJson["sentences"][0]
        basicDependencies = sentenceJson['basicDependencies']
        tokens = sentenceJson["tokens"]
        root = get_root(basicDependencies)[0]

        subj = find_subject(basicDependencies, root)
        verb = find_verb(basicDependencies, tokens, root)

        if not subj:
            subjPhrase = oldSubject
            subjIndices = [-1]
        else:
            subjPhrase = join(subj)
            subjIndices = get_indices(subj)
        if not verb:
            verbPhrase = oldVerb
            verbIndices = [-1]
        else:
            verbPhrase = join(verb)
            verbIndices = get_indices(verb)

        comp = join(
            find_complement(basicDependencies, root, subjIndices, verbIndices))
        result.append((subjPhrase, verbPhrase, comp))
        oldSubject = subjPhrase
        oldVerb = verbPhrase
    return result

# for s in split_sentences:
#     print(run(s))


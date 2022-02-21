from stanza.server import CoreNLPClient
from parse_tree import split_sentence
from test_sentences import *
import nltk.data
import string

from triples_3 import find_subject, find_verb_phrase, find_final_part


def call_stanford_nlp(text, annotators):
    ann = ",".join(annotators)
    with CoreNLPClient( start_server="DONT_START", endpoint='https://corenlp.uqcloud.net:443') as client:
        props = {'annotators': ann,
                 'pipelineLanguage': 'en', 'outputFormat': 'json'}
        ann = client.annotate(text, username='corenlp', password='8zIJDWrMGTck', properties=props)
    return ann

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

    conjunctions = []
    for i in range(len(connections)):
        if ands[i] >= connections[i]:
            conjunctions.append(ands[i])
        else:
            conjunctions.append(ands[i + 1])
    return connections, conjunctions

def handle_sentence(sentence):
    sentenceJson = call_stanford_nlp(sentence, ['parse'])
    sentenceJson = sentenceJson["sentences"][0]
    result = []
    subject = ''
    
    print("\nsentence: " + sentence)
    
    parts = split_sentence(sentenceJson)
    if len(parts) == 0:
        parts = [sentence]

    for clause in parts:
        clauseJson = call_stanford_nlp(clause, ['depparse'])
        basicDependencies = clauseJson['sentences'][0]['basicDependencies']
        roots, conjunctions = separate_sentence(basicDependencies)

        for i in range(len(roots)):
            root = roots[i]
            conj = conjunctions[i]
            
            newSubject = find_subject(basicDependencies, root)
            if not newSubject:
                newSubject = subject
            else:
                subject = newSubject
            
            if not newSubject:
                continue
            verb, vpos = find_verb_phrase(basicDependencies, sentenceJson["tokens"], root)

            try:
                part3 = find_final_part(basicDependencies, root, vpos, conj)
                if not part3 or len(part3) == 0:
                    end = conjunctions[i]
                    part3 = " ".join(tok["word"] for tok in sentenceJson["tokens"] if vpos + 1 < tok["index"] < end)
            except RecursionError:
                end = conjunctions[i]
                part3 = " ".join(tok["word"] for tok in sentenceJson["tokens"] if vpos + 1 < tok["index"] < end)
            result.extend([(subject, verb, part3)])

    return result

def run(input):
    inferences = []
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    input = input.translate(str.maketrans(';','.'))
    sentences = tokenizer.tokenize(input)

    for sentence in sentences:
        sentence = sentence.translate(str.maketrans('', '', '.'))
        result = handle_sentence(sentence)
        for res in result:
            if res not in inferences:
                inferences.append(res)
    # print(inferences)
    return inferences

# for s in neg_input:
#     run(s)
# run("I don't have grandchildren but I'd like to be called Grandpa")
# run("At the moment we have a dog called Speedy and a Bird , which we didn't get around to naming")
# run("And at the moment I'm getting a little bit into capoeira ; not very good at it at the moment, though")

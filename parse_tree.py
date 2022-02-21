from sys import maxsize
from test_sentences import *
from stanza.server import CoreNLPClient
import nltk.data
import string
import re

###
### Adapted from https://github.com/rahulkg31/sentence-to-clauses/blob/master/sent_to_clauses.py
###

def call_stanford_nlp(text):
    with CoreNLPClient( start_server="DONT_START", endpoint='https://corenlp.uqcloud.net:443') as client:
        props = {'annotators': 'openie,sentiment,depparse,parse',
                 'pipelineLanguage': 'en', 'outputFormat': 'json'}
        ann = client.annotate(text, username='corenlp', password='8zIJDWrMGTck', properties=props)
    return ann

def get_verb_phrases(tree):
    result = []
    num_children = len(tree)
    num_VP = sum(1 if tree[i].label() == "VP" else 0 for i in range(0, num_children))

    if tree.label() != "VP":
        for i in range(0, num_children):
            if tree[i].height() > 2:
                result.extend(get_verb_phrases(tree[i]))
    elif tree.label() == "VP" and num_VP > 1:
        for i in range(0, num_children):
            if tree[i].label() == "VP":
                if tree[i].height() > 2:
                    result.extend(get_verb_phrases(tree[i]))
    else:
        result.append(' '.join(tree.leaves()))

    return result

def get_pos(tree):
    vp_pos = []
    sub_conj_pos = []
    num_children = len(tree)
    children = [tree[i].label() for i in range(0,num_children)]

    flag = re.search(r"(S|SBAR|SBARQ|SINV|SQ)", ' '.join(children))

    if "VP" in children:
        for i in range(0, num_children):
            if tree[i].label() == "VP":
                vp_pos.append(tree[i].treeposition())
    elif not "VP" in children:
        for i in range(0, num_children):
            if tree[i].height() > 2:
                temp1,temp2 = get_pos(tree[i])
                vp_pos.extend(temp1)
                sub_conj_pos.extend(temp2)
    # comment this "else" part, if want to include subordinating conjunctions
    # else:
    #     for i in range(0, num_children):
    #         if tree[i].label() in ["S","SBAR","SBARQ","SINV","SQ"]:
    #             temp1, temp2 = get_pos(tree[i])
    #             vp_pos.extend(temp1)
    #             sub_conj_pos.extend(temp2)
    #         else:
    #             sub_conj_pos.append(tree[i].treeposition())

    return (vp_pos,sub_conj_pos)

def split_sentence(sentenceJson):
    tree = nltk.tree.ParentedTree.fromstring(sentenceJson["parse"])
    # tree.pretty_print()
    
    clause_trees = []
    for subtree in reversed(list(tree.subtrees())):
        if subtree.label() in ["S"]:
            if len(subtree) <= 1:
                continue

            if all(s.label().startswith(("CC", "WHADVP")) for s in subtree):
                del tree[subtree.treeposition()]
                continue

            clause_trees.append(subtree)
            if not (len(subtree) == 2 and any(s.label().startswith("ADJP") for s in subtree)):
                del tree[subtree.treeposition()]
        elif subtree.label().startswith("SBAR"):
            if len(subtree) == 1 and subtree[0].label() in ["WHNP"]:
                continue
            if len(subtree) == 1 and subtree[0].label() in ["IN"]:
                del tree[subtree.treeposition()]
            elif any(s.label().startswith(("CC", "WHADVP")) for s in subtree.subtrees()):
                del tree[subtree.treeposition()]
        
    clause_list = []
    for t in clause_trees:
        verb_phrases = get_verb_phrases(t)
        verb_phrases.reverse()
        vp_pos,sub_conj_pos = get_pos(t)

        for i in vp_pos:
            del t[i]
        for i in sub_conj_pos:
            del t[i]

        subject_phrase = ' '.join(t.leaves())

        for i in verb_phrases:
            if i in subject_phrase:
                continue
            clause_list.append(subject_phrase + " " + i)

    clause_list.reverse()
    return clause_list

def handle_sentence(sentence):
    sentenceJson = call_stanford_nlp(sentence)
    sentenceJson = sentenceJson["sentences"][0]
    
    print("\nsentence: " + sentence)
    parts = split_sentence(sentenceJson)
    return parts

# def main(input):
#     inferences = []
#     tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
#     sentences = tokenizer.tokenize(input)

#     for sentence in sentences:
#         result = handle_sentence(sentence)
#         print(str(result))
#         # for res in result:
#         #     if res not in inferences:
#         #         inferences.append(res)
#     # print(inferences)
#     return inferences

# for s in split_sentences:
#     main(s)

# main("I like to write and she loves to read and he enjoys patting dogs")
# main("I take my dog for a walk, make some tea, and spend some time with people I care about")
# main("There's lots of foods I don't like, that mushrooms would have to be at the top of the list")

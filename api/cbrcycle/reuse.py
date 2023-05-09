# Reuse functions
import requests
import config as cfg


def getSimilaritySemanticSBERT(text1, text2):
  """
  Calls an external service to get the similarity between a pair of texts.
  """
  url = cfg.sbert_similarity
  res = requests.post(url, json={'text1': text1, 'text2': text2, 'access_key': cfg.vectoriser_access_key})
  res_dictionary = res.json()
  return res_dictionary['similarity']

def get_from_id(id, lst):
    for k in lst:
        if k['id'] == id:
            return k
    return None

def get_index_in_list(pref_list, entry_id):
    # find index of entry_id in pref_list
    for index, val in enumerate(pref_list):
        if val['id'] == entry_id:
            return index
    return None

def get_cumulative_case_questions(nearest_neighbours, idx):
    lst = []
    for i in range(idx):
        case_id = i
        if 'id' in nearest_neighbours[i]:  # use case_id if it's available
            case_id = nearest_neighbours[i]['id']
        for index, value in enumerate(nearest_neighbours[i]['UserQuestion']):
            obj = {'id': str(case_id)+'_'+str(index), 'k': i, 'intent': nearest_neighbours[i]['UserIntent'], 'question': value}
            lst.append(obj)
    return lst

def get_case_questions(nearest_neighbours, idx):
    lst = []
    for index, value in enumerate(nearest_neighbours[idx]['UserQuestion']):
        obj = {'id': str(idx)+str(index), 'k': idx, 'intent': nearest_neighbours[idx]['UserIntent'], 'question': value}
        lst.append(obj)
    return lst

def get_intent_overlap(query_list, nn_list, pairings):
    count = 0
    match = 0
    for k,v in pairings.items():
        count += 1
        query_intent = get_from_id(k, query_list)['intent']
        case_intent = None
        if v is not None:
            case_intent = get_from_id(v, nn_list)['intent']
        if query_intent == case_intent:
            match += 1
    if count == 0:
        return 0.0
    return float(match)/count

def generate_preference_dict(men, women):
    """
    Generates a preference dictionary based on the semantic similarity of names using the S-Bert model.

    Arguments:
    names -- a list of names

    Returns:
    A dictionary mapping each name to a list of names in order of preference
    """
    pref_dict = {}
    for man in men:
        # Calculate the semantic similarity between the current name and all other names
        distances = [(woman, getSimilaritySemanticSBERT(man['question'], woman['question'])) for woman in women]

        # Sort the distances in descending order and convert to a list of items
        preferences = [item for item, distance in sorted(distances, key=lambda x: x[1], reverse=True)]

        pref_dict[man['id']] = preferences
    return pref_dict

def stable_marriage(men, women):
    """
    Returns a stable matching between men and women using the Gale-Shapley algorithm,
    where preferences are determined by the semantic similarity of names using S-Bert.

    Arguments:
    men -- a list of men's names
    women -- a list of women's names

    Returns:
    A dictionary mapping men's names to their matched partners' names
    """
    # Generate preference dictionaries based on the similarity of names
    men_prefs = generate_preference_dict(men, women)
    women_prefs = generate_preference_dict(women, men)

    # Initialize all men and women to be free and without partners
    free_men = set([x['id'] for x in men])
    free_women = set([x['id'] for x in women])
    matches = {}

    while free_men:
        # Choose a free man
        man = free_men.pop()

        # Get the man's preference list of women
        preferences = men_prefs[man]
        
        # Loop through the man's preferences and propose to the highest-ranked woman who is still free
        for woman in preferences:
            if woman['id'] in free_women:
                matches[man] = woman['id']
                free_women.remove(woman['id'])
                break
            else:
                # If the woman is not free, check if she prefers the man over her current partner
                current_partner = [k for k,v in matches.items() if v == woman['id']][0]  # get the woman's current partner
                if get_index_in_list(women_prefs[woman['id']], man) < get_index_in_list(women_prefs[woman['id']], current_partner):
                    matches[man] = woman['id']
                    matches[current_partner] = None
                    free_men.add(current_partner)
                    break
    return matches

def match(men, women):
    """
    Returns pairings of two lists using a stable marriage algo. and the average similarity of the pairings
    """
    pairings = stable_marriage(men, women)
    score = 0.0
    counter = 0
    total = 0.0
    for k,v in pairings.items():
        if k is not None:
            counter += 1
            if v is not None:
                total += getSimilaritySemanticSBERT(get_from_id(k, men)['question'],get_from_id(v, women)['question'])
    if counter > 0:
        score = total / counter
    return pairings, score

def MATCH(cq, nn, i, alpha=0.8):
    """
    Recursion returns the first pairing between 'cq' and 'nn' whose average similarity score is above 'alpha'.
    Matching starts from the 'i'th entry in 'nn' and increases 'i' in each iteration until 'alpha' is exceeded
    or 'nn' is exhausted. Use 'i = 1' to start matching from the first entry in 'nn'.
    """
    nn_lst = get_cumulative_case_questions(nn, i)
    pairings, score = match(cq, nn_lst)
#     print(i, score, pairings)
    if score>alpha or i==len(nn):
        return pairings, score, i, get_intent_overlap(cq, nn_lst, pairings), nn_lst
    else:
        return MATCH(cq, nn, i+1, alpha)


def custom_reuse_isee(input=None):
    """
    Reuse operation that requires certain attributes to be present in the cases.
    Each case requires an 'UserIntent' string and 'UserQuestion' array.

    @param input should include the query case (dict) that needs a solution (query_case) and
    an ordered list of cases (list of dict) from which a solution is constructed (neighbours).
    "acceptance_threshold" which determines cutoff for average similarity and "verbose" are 
    optional parameters. 
    """
    # print(input)
    if input is None:
        return {}
    
    query_case = input.get("query_case")
    neighbours = input.get("neighbours")
    acceptance_threshold = input.get("acceptance_threshold", 0.8)  # default as 0.8
    verbose = input.get("verbose", True)

    if query_case is None or neighbours is None:
        return {}
    
    query_questions = []
    for index, value in enumerate(query_case['UserQuestion']):
            obj = {'id': str(index), 'k': -1, 'intent': query_case['UserIntent'], 'question': value}
            query_questions.append(obj)
    pairings, score, neighbours_considered, intent_overlap, case_questions = MATCH(query_questions, neighbours, 1, acceptance_threshold)
    if verbose:
        # get details of pairings
        res = []
        for k,v in pairings.items():
            pair_obj = {}
            query_side = get_from_id(k, query_questions)
            if v is not None:
                case_side = get_from_id(v, case_questions)
                pair_obj['query'] = query_side
                pair_obj['case'] = case_side
                res.append(pair_obj)
        pairings = res
    return pairings, score, neighbours_considered, intent_overlap

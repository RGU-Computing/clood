# Reuse functions
import requests
import config as cfg
import uuid


def reuse(input=None):
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
    acceptance_threshold = input.get(
        "acceptance_threshold", 0.8)  # default as 0.8
    verbose = input.get("verbose", True)

    if query_case is None or neighbours is None:
        return {}

    query_questions = []
    for index, value in enumerate(query_case['UserQuestion']):
        obj = {'id': str(index), 'k': -1,
               'intent': query_case['UserIntent'], 'question': value}
        query_questions.append(obj)
    pairings, score, neighbours_considered, intent_overlap, case_questions = MATCH(
        query_questions, neighbours, 1, acceptance_threshold)
    if verbose:
        # get details of pairings
        res = []
        for k, v in pairings.items():
            pair_obj = {}
            query_side = get_from_id(k, query_questions)
            if v is not None:
                case_side = get_from_id(v, case_questions)
                pair_obj['query'] = query_side
                pair_obj['case'] = case_side
                res.append(pair_obj)
        pairings = res
        adapted_solution = adapt_solution(pairings, neighbours)
    return pairings, score, neighbours_considered, intent_overlap, adapted_solution

def getSimilaritySemanticSBERT(text1, text2):
    """
    Calls an external service to get the similarity between a pair of texts.
    """
    url = cfg.sbert_similarity
    res = requests.post(url, json={
                        'text1': text1, 'text2': text2, 'access_key': cfg.vectoriser_access_key})
    res_dictionary = res.json()
    return res_dictionary['similarity']

def get_from_id(id, lst):
    """
    Returns the first list entry with id that matches 'id'.
    """
    for k in lst:
        if k['id'] == id:
            return k
    return None

def get_from_id_key(_id, lst, key):
    for k in [l for l in lst if type(l) is dict]:
        if key in k and int(k[key]['id']) == _id:
            return k
    return None

def get_index_in_list(pref_list, entry_id):
    # find index of entry_id in pref_list
    for index, val in enumerate(pref_list):
        if val['id'] == entry_id:
            return index
    return None

def get_cumulative_case_questions(nearest_neighbours, idx):
    """
    Returns all the list entries up to index 'idx'. Returned items are transformed into a uniform format.
    """
    lst = []
    for i in range(idx):
        case_id = i
        if 'id' in nearest_neighbours[i]:  # use case_id if it's available
            case_id = nearest_neighbours[i]['id']
        for index, value in enumerate(nearest_neighbours[i]['UserQuestion']):
            obj = {'id': str(case_id)+'_'+str(index), 'k': i,
                   'intent': nearest_neighbours[i]['UserIntent'], 'question': value}
            lst.append(obj)
    return lst

def get_intent_overlap(query_list, nn_list, pairings):
    """
    Measures intent overlap
    """
    count = 0
    match = 0
    for k, v in pairings.items():
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

def get_nodes(current_node, nodes, node_list):
    node_list.append(current_node)
    # if a composite node with children
    children = current_node['firstChild'] if 'firstChild' in current_node else None
    while children:
        # find node
        child_id = children['Id']
        temp_node = [nodes[nkey]
                     for nkey in list(nodes.keys()) if nkey == child_id][0]
        get_nodes(temp_node, nodes, node_list)
        children = children['Next'] if 'Next' in children else None
    return node_list

def question_match(q, q_list):
    # multiple questions split by ;
    if ";" in q_list:
        return q in q_list.split(";")
    # single question
    else:
        return q == q_list

def empty_solution(c):
    empty_solution = c.copy()
    # leave only one tree in tree list
    empty_solution['trees'] = [t for t in empty_solution['trees'] if t['id'] == empty_solution['selectedTree']]
    selected_tree = empty_solution['trees'][0]
    # new tree id
    tree_id = str(uuid.uuid4())
    selected_tree['id'] = tree_id
    empty_solution['selectedTree'] = tree_id
    # new root node id
    root_id = str(uuid.uuid4())
    current_root_id = selected_tree['root']
    root_node = [selected_tree['nodes'][nkey]
                 for nkey in list(selected_tree['nodes'].keys()) if (nkey == current_root_id)][0]
    # remove children of the root Sequence Node
    temp_child = {
        "Id": "",
        "Next": None
    }
    root_node['id'] = root_id
    selected_tree['root'] = root_id
    root_node['firstChild'] = temp_child
    # remove all nodes except the root sequence node
    empty_solution['trees'][0]['nodes'] = {root_id: root_node}
    return empty_solution

def generate_next(template, ids, idx):
    template['Id'] = ids[idx]
    template['Next'] = None if idx+1 >= len(ids) else generate_next(template.copy(), ids, idx+1)
    return template

def generate_solution(c, sub_trees):
    # if no solutions found
    if not sub_trees:
        return c
    # otherwise
    c_nodes = c['trees'][0]['nodes']
    c_root_node = c['trees'][0]['nodes'][c['trees'][0]['root']]
    temp_child = c_root_node['firstChild'].copy()
    roots = []
    # add nodes in each sub-tree to the empty solution
    for sub_tree in sub_trees:
        root_node_id = sub_tree[1]
        nodes = sub_tree[0]
        for node in nodes:
            c_nodes[node['id']] = node
        roots.append(root_node_id)
    c['trees'][0]['nodes'] = c_nodes
    # on the root, recursively create the references to top level children
    idx = 0
    temp_child['Id'] = roots[idx]
    temp_child['Next'] = generate_next(temp_child.copy(), roots, idx+1)
    first_child = temp_child
    c_root_node['firstChild'] = first_child
    c['trees'][0]['nodes'][c['trees'][0]['root']] = c_root_node
    # updated solution tree
    return c

def replace_references_in_dict(_dict, p_id, n_id):
    for _key in _dict:
        if type(_dict[_key]) is dict:
            _dict[_key] = replace_references_in_dict(_dict[_key], p_id, n_id)
        # dont replace if its 'id'
        if _dict[_key] == p_id and _key != 'id':
            _dict[_key] = n_id
    return _dict

def replace_references_in_list(_list, p_id, n_id):
    new_list = []
    for node in _list:
        new_node = replace_references_in_dict(node, p_id, n_id)
        new_list.append(new_node)
    return new_list

def clean_uuid(nodes, root_id):
    new_nodes = []
    for node in nodes:
        previous_id = node['id']
        new_id = str(uuid.uuid4())
        if previous_id == root_id:
            #update root id
            root_id = new_id
        nodes = replace_references_in_list(nodes, previous_id, new_id)
        node['id'] = new_id
        new_nodes.append(node)
    return new_nodes, root_id

def adapt_solution(pairs, neighbours):
    sub_trees = []
    for idx in range(len(pairs)):
        matched_pair = get_from_id_key(idx, pairs, 'query')
        q_q = matched_pair['query']['question']
        c_q = matched_pair['case']['question']
        c_idx = matched_pair['case']['k']
        c_solution = neighbours[c_idx]['Solution']
        # solution tree
        c_sol_tree = [t for t in c_solution['trees']
                      if t['id'] == c_solution['selectedTree']][0]
        # all priority nodes
        c_sol_subs = [c_sol_tree['nodes'][nkey] for nkey in list(
            c_sol_tree['nodes'].keys()) if c_sol_tree['nodes'][nkey]['Concept'] == 'Priority']
        # priority nodes where the first child is a User Question Node and the question text matches the case question
        for a_sub in c_sol_subs:
            first_child = a_sub['firstChild']['Id']
            first_child_type = [c_sol_tree['nodes'][nkey] for nkey in list(c_sol_tree['nodes'].keys()) if (nkey == first_child
                                                                                                           and c_sol_tree['nodes'][nkey]['Concept'] == 'User Question'
                                                                                                           and question_match(c_q, c_sol_tree['nodes'][nkey]['params']['Question']['value']))]
            # first node is a User Question Node and question is c_q
            # also there are only two children in the sub tree: User Question and Explanation Strategy
            if first_child_type and not a_sub['firstChild']['Next']['Next']:
                # get the explainer strategy sibling
                es_sub_id = a_sub['firstChild']['Next']['Id']
                es_sub_node = [c_sol_tree['nodes'][nkey] for nkey in list(
                    c_sol_tree['nodes'].keys()) if nkey == es_sub_id][0]
                # collect all children
                node_list = []
                node_list = get_nodes(
                    es_sub_node, c_sol_tree['nodes'], node_list)
                # create a new sub tree with q_q
                temp_question_node = first_child_type[0].copy()
                temp_question_node['params']['Question']['value'] = q_q+';'
                node_list.append(temp_question_node)
                node_list.append(a_sub)
                node_list, root_node_id = clean_uuid(node_list, a_sub['id'])
                sub_trees.append([node_list, root_node_id])
    adaptedSolution = generate_solution(empty_solution(neighbours[0]['Solution']), sub_trees)
    return adaptedSolution

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
        distances = [(woman, getSimilaritySemanticSBERT(
            man['question'], woman['question'])) for woman in women]

        # Sort the distances in descending order and convert to a list of items
        preferences = [item for item, distance in sorted(
            distances, key=lambda x: x[1], reverse=True)]

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
                # get the woman's current partner
                current_partner = [
                    k for k, v in matches.items() if v == woman['id']][0]
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
    for k, v in pairings.items():
        if k is not None:
            counter += 1
            if v is not None:
                total += getSimilaritySemanticSBERT(get_from_id(
                    k, men)['question'], get_from_id(v, women)['question'])
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
    if score > alpha or i == len(nn):
        return pairings, score, i, get_intent_overlap(cq, nn_lst, pairings), nn_lst
    else:
        return MATCH(cq, nn, i+1, alpha)

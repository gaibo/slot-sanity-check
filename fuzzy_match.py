from collections import Counter
from typing import Callable, List, Set


def fuzzy_match_heuristic(element_1: str, element_2: str) -> float:
    """ Simple heuristic to compare similarity of two strings - [0: no matching letters, 1: anagram]
    :param element_1: string 1
    :param element_2: string 2
    :return: float in range [0, 1]
    """
    if len(element_1) > len(element_2):
        long, short = element_1, element_2
    else:
        short, long = element_1, element_2
    counter_long, counter_short = Counter(long), Counter(short)
    acc = 0     # Tally total number of common letters
    for char in counter_short.keys():
        acc += min(counter_long.get(char, 0), counter_short[char])  # min is what they have in commmon
    return acc / len(long)  # Heuristic


def fuzzy_matches(element: str, knowledge_bank: Set[str], threshold: float = 0.75,
                  heuristic: Callable[[str, str], float] = fuzzy_match_heuristic) -> List[str]:
    """ Return sorted list of known things with highest fuzzy match heuristic to element (past threshold)
    :param element: new thing to match
    :param knowledge_bank: known things to match to
    :param threshold: heuristic numerical threshold [0, 1] to register as a "match"
    :param heuristic: heuristic function whose value is compared to threshold
    :return: (ordered) list of known things
    """
    match_dict = {knowledge: heuristic(element, knowledge)
                  for knowledge in knowledge_bank if heuristic(element, knowledge) >= threshold}
    sorted_matches = sorted(match_dict.items(), key=lambda kv: kv[1], reverse=True)     # Intermediate state
    return list(map(lambda kv: kv[0], sorted_matches))  # Return just the "knowledge" strings, not their scores

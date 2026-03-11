import sys
sys.path.insert(0, '..')
from matcher import Matcher
from board import Action, ActionType

def test_matcher():
    req = input("Please input: ")

    action = Action(
        type=ActionType.OPERATION,
        request=req,
        operation=req
    )
    matcher = Matcher(action)
    if matcher.match():
        print(matcher.run())
    else:
        print("need further analysis")

if __name__ == "__main__":
    test_matcher()

from calcifer.partial import Partial

def run_policy(policy_rule, obj=None):
    if obj is None:
        obj = {}

    if 'context' not in obj:
        obj['context'] = []
    if 'errors' not in obj:
        obj['errors'] = []

    partial = Partial.from_obj(obj)
    _, policy_final = policy_rule.run(partial)[0]
    return policy_final.root

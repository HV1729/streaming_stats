import json
import math
import numpy as np
import random
import requests
from scipy import stats

class ApiTasks(object):
    def on_start(self):
        # Implement login logic once you have integrated tornado auth module
        pass

    def push_and_check_stats(self):
        ITEM_COUNT = 200
        account_name = 'testaccount'
        stats_name = 'teststat' + str(int(random.random() * ITEM_COUNT))

        #values = map(lambda each: each + 1, range(ITEM_COUNT))
        #values = map(lambda each: random.random() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.uniform(1, ITEM_COUNT), range(ITEM_COUNT))
        values = map(lambda each: random.triangular(0.01, ITEM_COUNT), range(ITEM_COUNT))
        #values = map(lambda each: random.betavariate() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.expovariate() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.gammavariate() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.gauss() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.lognormvariate() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.normalvariate() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.vonmisesvariate() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.paretovariate() * ITEM_COUNT, range(ITEM_COUNT))
        #values = map(lambda each: random.weibullvariate() * ITEM_COUNT, range(ITEM_COUNT))

        #hostname = 'http://127.0.0.1:8000'
        hostname = 'https://online-stats.herokuapp.com'
        result = requests.get(hostname + '/stats/exists?account_name=%s&stats_name=%s'\
                                    % (account_name, stats_name)).text
        exists = json.loads(result)
        values = list(values)
        correct_stats ={
                        'count': len(values),
                        'mean': np.mean(values),
                        'variance': np.var(values),
                        'std': np.std(values),
                        'skewness': stats.skew(values) ,
                        'kurtosis': stats.kurtosis(values),
                        }
        import pdb; pdb.set_trace()  # XXX BREAKPOINT
        if not exists:
            requests.post(hostname + '/stats/init?account_name=%s&stats_name=%s'\
                                    % (account_name,stats_name))
            for value in values:
                requests.post(hostname + '/stats?account_name=%s&stats_name=%s&value=%s'\
                                        % (account_name, stats_name, value))
            streamed_stats = requests.get(hostname + '/stats?account_name=%s&stats_name=%s'\
                                             % (account_name, stats_name))
            if streamed_stats:
                streamed_stats = json.loads(streamed_stats.text)

            print("Actual values:", values)
            print("calculated stats:", correct_stats)
            print("streamed_stats:", streamed_stats)
            for k,v in correct_stats.items():
                print(k, "Is equal(as per math.isclose): ", math.isclose(streamed_stats[k], v))
            requests.delete(hostname + '/stats?account_name=%s&stats_name=%s'\
                                        % (account_name, stats_name))
if __name__ == '__main__':
    a = ApiTasks()
    a.push_and_check_stats()


import datetime
import json
import logging
import math
import os
import psycopg2
import redis
import sys
import tornado
import tornado.httpserver
import tornado.ioloop
import urllib

from tornado.options import define, options
from tornado.web import RequestHandler, Application

define('debug', default=1, help='hot deployment. use in dev only', type=int)
define('port', default=8000, help='run on the given port', type=int)

MIN_EXP_TIME = 30 * 24 * 60 * 60     # Expire after 30 days

STATS_KEY = 'online:stats'


redistogo_url = os.getenv('REDISTOGO_URL')
assert redistogo_url, 'No redis To Go URL set'

redisToGoConn = redis.from_url(redistogo_url)
db_conn = psycopg2.connect("dbname=statsmechanic user=statsmechanic password='gauss'")

#logger = logging.getLogger()
#LOG_FILENAME = 'example.log'
#logger.level = logging.DEBUG
#handler = logging.handlers.RotatingFileHandler(LOG_FILENAME,
#                                               maxBytes=10000,
#                                               backupCount=3)
#logger.addHandler(handler)
#redisToGoConn = redis.Redis()
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

#TODO: fix that new key value defaulting to 0. That causes errors when actual first value sent is 0.
# you need a better way of dealing with default value and first time stats creation.

#TODO:
class OnlineStats(object):

    def __init__(self, sample=False, sample_type=None):
        self.redis = redisToGoConn
        self.postgres=db_conn
        self.postgres.autocommit = True
        if sample:
            assert sample_type
            self.is_sample = sample
            self.sample_type = sample_type if sample_type else 'reservoir'

    def init_account(self, account):
        self.stats_key_prefix = STATS_KEY + ':' + account
        #self.redis.exists(self.stats_key_prefix)

    def is_gamma(self, account_name, stats_name):
        """
        #TODO: To really try to say anything about is_gamma or not,
            we need to know the histogram/bin-wise frequency of the original data
        #Setup bin ranges and counters and track that too for extra price
        """
        from scipy.stats.distributions import gamma
        m1, m2, m3, m4 = getMoments(account_name, stats_name)
        alpha_mom = (m1 ** 2)/m2
        beta_mom =  m2/m1
        plt.plot(np.linspace(0,10), gamma.pdf(np.linspace(0,10), alpha_mom[0], beta_mom[0]))
        pass

    def is_normal(self):
        pass

    def is_poisson(self):
        pass

    def is_binomial(self):
        pass

    def is_chi_square(self):
        pass

    def delete_stat(self, account_name, stats_name):
        self.stats_key_prefix = STATS_KEY + ':' + account_name
        with self.postgres.cursor() as cursor:
            result = cursor.execute("DELETE * FROM streamedstats WHERE accountname='%s'\
                                                            and statsname='%s';" \
                                                            % (account_name, stats_name))
            self.postgres.commit()
        return json.dumps(result)

    def add_stat(self, account_name, stats_name):
        with self.postgres.cursor() as cursor:
            cursor.execute("INSERT INTO streamedstats (accountname, statsname) \
                                    values (%s, %s);", (account_name, stats_name))
            result = cursor.rowcount
            self.postgres.commit()
        return {'status': result}

    def stat_exists(self, account_name, stats_name):
        stats_key_prefix = STATS_KEY + ':' + account_name
        count_key = stats_key_prefix + ':' + stats_name + ':count'
        with self.postgres.cursor() as cursor:
            result=cursor.execute("SELECT  * FROM streamedstats WHERE accountname='%s' \
                                  AND statsname='%s'"%\
                                  (account_name, stats_name))
            #return bool(self.redis.get(count_key))
            return bool(result)

    def check_outlier(self, stats_name, value):
        # TODO: Implemnent a simple calculation to guess/predict the new value's probability of
        # being a outlier
        pass

    def update_stats(self, account_name, stats_name, value):
        assert stats_name
        assert value

        with self.postgres.cursor() as cursor:
            # Check if already a value is present if not calculate new moments
            cursor.execute("SELECT (count, m1, m2, m3, m4) FROM streamedstats WHERE \
                                    accountname='%s' and statsname='%s'"% (account_name, stats_name))
            result = cursor.fetchall()
        curr_count, curr_m1, curr_m2, curr_m3, curr_m4 = eval(result[0][0])


        # This logic/approximation is copied from
        # http://www.johndcook.com/blog/skewness_kurtosis/
        n = curr_count + 1
        # Do the difference calculus  based finite approximations
        delta = value - curr_m1
        delta_n = delta /n
        delta_n2=delta_n * delta_n
        term1 = delta * delta_n * curr_count
        m1 = curr_m1 + delta_n
        m2 = curr_m2 + term1
        m3 = curr_m3 + term1 * delta_n * (n-2) -3 * delta_n *curr_m2
        m4 = curr_m4 + term1 * delta_n2 * (n*n -3*n +3) + 6*delta_n2* curr_m2 -4*delta_n *curr_m3
        with self.postgres.cursor() as cursor:
            cursor.execute("UPDATE streamedstats SET (count, m1, m2, m3, m4) \
                           = (%f, %f, %f, %f, %f) WHERE\
                           accountname='%s' AND statsname='%s';"%\
                           (n, m1, m2, m3, m4, account_name,\
                            stats_name))
            result = cursor.rowcount
            #self.postgres.commit()
        res = {'status': result
                }
        return res

    def retrieve_stats(self, account_name, stats_name):
        assert self.stats_key_prefix
        print(account_name, stats_name)
        with self.postgres.cursor() as cursor:
            cursor.execute("SELECT (count, m1, m2, m3, m4) FROM streamedstats WHERE \
                                       accountname='%s' and statsname='%s'"% (account_name, stats_name))

            result = cursor.fetchall()
        assert result
        res = eval(result[0][0])
        count, m1, m2, m3, m4 = res

        res = {'count': count,
               'mean': m1,
               'variance': m2 / (count-1.0) if count > 1 else 'NA',
               'std': math.sqrt(m2/(count-1.0)) if count > 1 else 'NA',
               'skewness': math.sqrt(count) * m3/math.pow(m2, 1.5) if count > 1 else 'NA',
               'kurtosis': count*m4 /(m2*m2) - 3.0 if count > 1 else 'NA'
               }
        return res

class AddStatHandler(RequestHandler):
    def post(self):
        account_name = self.get_arguments('account_name')[0]
        stats_name = self.get_arguments('stats_name')[0]
        assert account_name
        assert stats_name
        ols = OnlineStats()
        ols.init_account(account_name)
        result = ols.add_stat(account_name, stats_name)
        self.finish(json.dumps(result))


class StatsHandler(RequestHandler):
    def delete(self):
        account_name = self.get_arguments('account_name')[0]
        stats_name = self.get_arguments('stats_name')[0]
        assert account_name
        assert stats_name
        ols = OnlineStats()
        ols.delete_stat(account_name, stats_name)
        self.finish()

    def get(self):
        account_name = self.get_arguments('account_name')[0]
        stats_name = self.get_arguments('stats_name')[0]
        assert account_name
        assert stats_name
        ols = OnlineStats()
        ols.init_account(account_name)
        result = ols.retrieve_stats(account_name, stats_name)
        self.finish(json.dumps(result))

    def post(self):
        account_name = self.get_arguments('account_name')[0]
        stats_name = self.get_arguments('stats_name')[0]
        value = float(self.get_arguments('value')[0])
        assert account_name
        assert stats_name
        assert value and isinstance(value, float)

        #self.collector = Collector()
        #self.collector.start()

        ols = OnlineStats()
        ols.init_account(account_name)
        result = ols.update_stats(account_name, stats_name, value)
        self.finish(json.dumps(result))

class StatsExistsHandler(RequestHandler):
    def get(self):
        account_name = self.get_arguments('account_name')[0]
        stats_name = self.get_arguments('stats_name')[0]
        assert account_name
        assert stats_name
        ols = OnlineStats()
        result = bool(ols.stat_exists(account_name, stats_name))
        self.finish(json.dumps(result))

class Application(Application):
    """
    >>> import requests
    >>> requests.post("/stats", params={"account_name":"test",
                                        "stats_name": "teststat", "value": 43.5})
    >>> resp = requests.get("/stats", params={"account_name":"test",
                                        "stats_name": "teststat", "value": 43.5})
    """
    def __init__(self):
        handlers = [
                (r'/stats/exists',StatsExistsHandler),
                (r'/stats',StatsHandler),
                (r'/stats/init', AddStatHandler),
                ]
        settings = dict(
            autoescape=None,  # tornado 2.1 backward compatibility
            debug=options.debug,
            gzip=True,
            )
        settings.update({'static_path':'./static'})
        tornado.web.Application.__init__(self, handlers, **settings)

def main():
    tornado.options.parse_command_line()
    app = Application()
    httpServer = tornado.httpserver.HTTPServer(app)
    port = os.getenv('PORT') or options.port
    httpServer.listen(address='0.0.0.0', port=port)
    tornado.ioloop.IOLoop.instance().start()
    #inst.set_blocking_signal_threshold(seconds=0.50, action=inst.log_stack)
    #inst.start()

if __name__ == '__main__':
    main()

#!/usr/bin/env python2

import threading
from threading import Timer
from collections import defaultdict
import time
import logging


"""
references:
 - http://blog.ianbicking.org/good-catch-all-exceptions.html
"""


class LeakingErrorCounter():
    """A leaky bucket type of exception counter

    @param decay_rate decay rate of errors in Hz, e.g. 2 means after 0.5
        seconds the error count decayed to zero
    @param error_limit the error limit after which the exception should not be
        catched and ignored but re-raised
    @param ignore a list of exceptions which should not be catched but
        immediately re-raised, i.e. 'MemoryError' or something like that

    Instantiate the error counter and call the 'handle_exception' method on
    each exception or just the ones that should not immediately be re-raised.
    After the same type of exception was encountered more than 'error_limit'
    times in a short time interval, i.e. before the error ocurrences have
    decayed away, the exception is re-raised.

    This class should be especially useful as a 'last resort' catcher if
    continuity is preferred over integrity of the running program. An example
    would be if the user of the program is not interested in program bugs but
    it works Good Enough (tm) in most cases.
    """
    def __init__(self, decay_rate=2, error_limit=10, ignore=[]):
        self.errorcnt = defaultdict(int)
        self.decay_rate  = decay_rate
        self.error_limit = error_limit
        self.ignore = ignore
        self.decay_thread = threading.Thread(target=self.run)
        self.decay_thread.setDaemon(True)
        self.decay_thread.start()

    def run(self):
        while True:
            time.sleep(1.0 / self.decay_rate)
            self.decay()

    def decay(self, decrement=1):
        for k in self.errorcnt.keys():
            if self.errorcnt[k] > 0:
                self.errorcnt[k] -= 1

    def handle_exception(self, e):
        for i in self.ignore:
            if isinstance(e, i):
                raise(e)
        k = str(e)
        self.errorcnt[k] += 1
        logging.debug("exception: %s, errorcount: %u" % (k, self.errorcnt[k]))
        if self.errorcnt[k] > self.error_limit:
            logging.error("error limit hit for exception %s, reraising" % k)
            raise(e)
        else:
            #logging.exception(e)
            logging.info("Exception %s encountered, error count increased" % e)


def continous_run_with_leaky_error_counter(fun, instance=LeakingErrorCounter(), run_condition=True):
    while run_condition:
        try:
            fun()
        except Exception as e:
            instance.handle_exception(e)


def test_fails_after_too_many_errors_in_too_short_time():
    """This test throws one of two errors until too many have been encountered of one type"""
    import random
    def error_thrower(yield_list=[Exception("generic error"), Exception("other error")]):
        time.sleep(0.1)
        logging.debug("throwing_error")
        raise yield_list[random.randint(0,1)]
    continous_run_with_leaky_error_counter(error_thrower)

if __name__ == "__main__":
    logging.root.setLevel(logging.DEBUG)
    test_fails_after_too_many_errors_in_too_short_time()
    logging.debug("program exited successful")

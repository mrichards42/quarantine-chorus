"""Background processing for wxEventHandler-derived classes"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import wx
import wx.lib.newevent


(FutureCompleteEvent, EVT_FUTURE_COMPLETE) = wx.lib.newevent.NewEvent()


class ThreadPool:
    def __init__(self, target, max_workers=8):
        self.target = target
        self.pool = ThreadPoolExecutor(max_workers=max_workers)
        target.Bind(EVT_FUTURE_COMPLETE, self.OnFutureComplete)

    def shutdown(self, *args, **kwargs):
        self.pool.shutdown(*args, **kwargs)

    def run(self, f, *args, callback=None, **kwargs):
        def wrapper(*args, **kwargs):
            try:
                start = time.time()
                fn_name = '.'.join(filter(None, (f.__module__, f.__qualname__)))
                fn_args = ', '.join((*map(repr, args),
                                     *(f'{k}={v!r}' for k,v in kwargs.items())))
                logging.info("Background function %s start with args (%s)",
                             fn_name, fn_args)
                ret = f(*args, **kwargs)
                logging.info("Background function %s took %0.3f seconds.",
                             fn_name, time.time() - start)
                return ret
            except Exception:
                logging.exception("Exception in background thread %s", fn_name)
                raise
        future = self.pool.submit(wrapper, *args, **kwargs)
        if callback:
            future.add_done_callback(partial(self.post_future_event, callback))

    def post_future_event(self, callback, future):
        wx.PostEvent(self.target,
                     FutureCompleteEvent(callback=callback,
                                         result=future.result()))

    def OnFutureComplete(self, evt):
        evt.callback(evt.result)

"""Background processing for wxEventHandler-derived classes"""
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
        future = self.pool.submit(f, *args, **kwargs)
        if callback:
            future.add_done_callback(partial(self.post_future_event, callback))

    def post_future_event(self, callback, future):
        wx.PostEvent(self.target,
                     FutureCompleteEvent(callback=callback,
                                         result=future.result()))

    def OnFutureComplete(self, evt):
        evt.callback(evt.result)

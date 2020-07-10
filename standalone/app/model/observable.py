import wx
import wx.lib.newevent


class Observable:
    def __init__(self):
        self._subscriptions = {}
        self._SubReadyEvent, self._EVT_SUB_READY = wx.lib.newevent.NewEvent()
        self._in_tx = False

    def value(self, **kwargs):
        raise NotImplementedError()

    def subscribe(self, target, f, **kwargs):
        if target not in self._subscriptions:
            target.Bind(self._EVT_SUB_READY, self.OnSubscriptionReady)
            self._subscriptions[target] = []
        self._subscriptions[target].append({'handler': f, 'kwargs': kwargs})

    def OnSubscriptionReady(self, evt):
        for h in evt.handlers:
            f = h['handler']
            kwargs = h['kwargs']
            value = self.value(**kwargs)
            f(value)

    def notify(self):
        if self._in_tx:
            self._notify_called = True
        for target, handlers in self._subscriptions.items():
            event = self._SubReadyEvent(handlers=handlers)
            wx.PostEvent(target, event)

    # Context manager for transactions

    def transaction(self):
        return self

    def __enter__(self):
        self._in_tx = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._in_tx = False
        if self._notify_called:
            self._notify_called = False
            self.notify()

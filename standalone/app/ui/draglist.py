import wx
import wx.lib.newevent

(BeginDragEvent, EVT_BEGIN_DRAG) = wx.lib.newevent.NewEvent()
(DraggingEvent, EVT_DRAGGING) = wx.lib.newevent.NewEvent()
(EndDragEvent, EVT_END_DRAG) = wx.lib.newevent.NewEvent()


class ListDragger:
    """A class that implements drag events for a wxListCtrl.

    dragger = draglist.ListDragger(myList)
    myList.Bind(draglist.EVT_BEGIN_DRAG, myList.OnDragBegin)
    myList.Bind(draglist.EVT_DRAGGING, myList.OnDragging)
    myList.Bind(draglist.EVT_END_DRAG, myList.OnDragEnd)
    """
    def __init__(self, _list, target=None):
        self.list = _list
        self.target = target or _list
        self.list.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnDragBegin)
        self.list.Bind(wx.EVT_MOTION, self.OnMotion)
        self.list.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.dragging = False
        self.beginIdx = None
        self.prevIdx = None

    IGNORE_FLAGS = wx.LIST_HITTEST_TOLEFT | wx.LIST_HITTEST_TORIGHT
    ABOVE_FLAGS = wx.LIST_HITTEST_ABOVE
    BELOW_FLAGS = wx.LIST_HITTEST_BELOW | wx.LIST_HITTEST_NOWHERE

    def HitTest(self, pos):
        idx, flags = self.list.HitTest(pos)
        if flags & wx.LIST_HITTEST_ONITEM:
            return idx
        else:
            return -1

    def OnDragBegin(self, evt):
        self.beginIdx = evt.GetIndex()
        self.dragging = True
        wx.PostEvent(self.target, BeginDragEvent(index=self.beginIdx))
        evt.Skip()

    def OnMotion(self, evt):
        if self.dragging:
            idx = self.HitTest(evt.GetPosition())
            if idx > -1 and idx != self.prevIdx:
                self.prevIdx = idx
                wx.PostEvent(self.target, DraggingEvent(index=idx))
        evt.Skip()

    def OnLeftUp(self, evt):
        if self.dragging:
            idx = self.HitTest(evt.GetPosition())
            if idx == -1:
                idx = self.prevIdx
            wx.PostEvent(self.target, EndDragEvent(index=idx))
            self.dragging = False
            self.beginIdx = None
            self.prevIdx = None
        evt.Skip()

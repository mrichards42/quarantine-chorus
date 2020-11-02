import wx


def file_dialog(parent, **kwargs):
    with wx.FileDialog(parent, **kwargs) as dlg:
        if dlg.ShowModal() == wx.ID_CANCEL:
            return
        if kwargs.get('style', 0) & wx.FD_MULTIPLE:
            return dlg.GetPaths()
        else:
            return dlg.GetPath()

class AllowedCharsValidator(wx.Validator):
    def __init__(self, allowed_chars):
        wx.Validator.__init__(self)
        self.allowed_chars = set(allowed_chars)
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return AllowedCharsValidator(self.allowed_chars)

    def Validate(self, parent):
        value = self.GetWindow().GetValue()
        for c in value:
            if c not in self.allowed_chars:
                return False
        return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

    def OnChar(self, event):
        # logic mostly from https://github.com/wxWidgets/wxWidgets/blob/b6cff426ce40a5bd8e0e51c6ad2f26d9510a597e/src/common/valtext.cpp#L275
        event.Skip()
        keyCode = event.GetKeyCode()
        # we don't filter special keys and delete
        if keyCode < wx.WXK_SPACE or keyCode == wx.WXK_DELETE:
            return
        if chr(keyCode) in self.allowed_chars:
            return
        if not self.IsSilent():
            wx.Bell()
        event.Skip(False)


def GetFloatFromUser(message, caption, value, min=0, max=100, parent=None, pos=wx.DefaultPosition):
    """Like wx.GetNumberFromUser but for floats"""
    dlg = wx.TextEntryDialog(parent, message, caption, str(value))
    # https://github.com/wxWidgets/wxWidgets/blob/b6cff426ce40a5bd8e0e51c6ad2f26d9510a597e/src/generic/textdlgg.cpp#L48
    text = dlg.FindWindowById(3000)
    text.SetValidator(AllowedCharsValidator('1234567890.'))
    if dlg.ShowModal() == wx.ID_OK:
        val = dlg.GetValue()
        if val:
            return float(val)

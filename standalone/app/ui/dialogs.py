import wx


def file_dialog(parent, **kwargs):
    with wx.FileDialog(parent, **kwargs) as dlg:
        if dlg.ShowModal() == wx.ID_CANCEL:
            return
        if kwargs.get('style', 0) & wx.FD_MULTIPLE:
            return dlg.GetPaths()
        else:
            return dlg.GetPath()

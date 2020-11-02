# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version Oct 26 2018)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class Frame
###########################################################################

class Frame ( wx.Frame ):

    def __init__( self, parent ):
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"Video Aligner", pos = wx.DefaultPosition, size = wx.Size( 860,520 ), style = wx.DEFAULT_FRAME_STYLE|wx.RESIZE_BORDER|wx.TAB_TRAVERSAL )

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

        bSizer6 = wx.BoxSizer( wx.VERTICAL )

        self.m_panel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        self.m_sizer = wx.BoxSizer( wx.VERTICAL )

        bSizer7 = wx.BoxSizer( wx.HORIZONTAL )


        bSizer7.Add( ( 0, 0), 1, wx.EXPAND, 5 )

        self.m_openBtn = wx.Button( self.m_panel, wx.ID_ANY, u"Open", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer7.Add( self.m_openBtn, 0, wx.ALL, 5 )

        self.m_previewAudioBtn = wx.Button( self.m_panel, wx.ID_ANY, u"Preview Audio", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer7.Add( self.m_previewAudioBtn, 0, wx.ALL, 5 )

        self.m_previewVideoBtn = wx.Button( self.m_panel, wx.ID_ANY, u"Preview Video", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer7.Add( self.m_previewVideoBtn, 0, wx.ALL, 5 )

        self.m_exportBtn = wx.Button( self.m_panel, wx.ID_ANY, u"Export to Shotcut", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer7.Add( self.m_exportBtn, 0, wx.ALL, 5 )


        self.m_sizer.Add( bSizer7, 0, wx.EXPAND, 5 )


        self.m_panel.SetSizer( self.m_sizer )
        self.m_panel.Layout()
        self.m_sizer.Fit( self.m_panel )
        bSizer6.Add( self.m_panel, 1, wx.EXPAND, 5 )


        self.SetSizer( bSizer6 )
        self.Layout()
        self.m_menubar1 = wx.MenuBar( 0 )
        self.m_fileMenu = wx.Menu()
        self.m_fileOpenItem = wx.MenuItem( self.m_fileMenu, wx.ID_OPEN, wx.EmptyString, wx.EmptyString, wx.ITEM_NORMAL )
        self.m_fileMenu.Append( self.m_fileOpenItem )

        self.m_fileExportItem = wx.MenuItem( self.m_fileMenu, wx.ID_SAVE, u"Export to Shotcut", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_fileMenu.Append( self.m_fileExportItem )

        self.m_logItem = wx.MenuItem( self.m_fileMenu, wx.ID_SAVE, u"View logs", wx.EmptyString, wx.ITEM_NORMAL )
        self.m_fileMenu.Append( self.m_logItem )

        self.m_menubar1.Append( self.m_fileMenu, u"&File" )

        self.SetMenuBar( self.m_menubar1 )


        self.Centre( wx.BOTH )

        # Connect Events
        self.m_openBtn.Bind( wx.EVT_BUTTON, self.OnFileOpen )
        self.m_previewAudioBtn.Bind( wx.EVT_BUTTON, self.OnPreviewAudio )
        self.m_previewVideoBtn.Bind( wx.EVT_BUTTON, self.OnPreviewVideo )
        self.m_exportBtn.Bind( wx.EVT_BUTTON, self.OnExportShotcut )
        self.Bind( wx.EVT_MENU, self.OnFileOpen, id = self.m_fileOpenItem.GetId() )
        self.Bind( wx.EVT_MENU, self.OnExportShotcut, id = self.m_fileExportItem.GetId() )
        self.Bind( wx.EVT_MENU, self.OnViewLogs, id = self.m_logItem.GetId() )

    def __del__( self ):
        pass


    # Virtual event handlers, overide them in your derived class
    def OnFileOpen( self, event ):
        event.Skip()

    def OnPreviewAudio( self, event ):
        event.Skip()

    def OnPreviewVideo( self, event ):
        event.Skip()

    def OnExportShotcut( self, event ):
        event.Skip()



    def OnViewLogs( self, event ):
        event.Skip()


###########################################################################
## Class TrackListPanel
###########################################################################

class TrackListPanel ( wx.Panel ):

    def __init__( self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.TAB_TRAVERSAL, name = wx.EmptyString ):
        wx.Panel.__init__ ( self, parent, id = id, pos = pos, size = size, style = style, name = name )

        sbSizer1 = wx.StaticBoxSizer( wx.StaticBox( self, wx.ID_ANY, u"Track List" ), wx.VERTICAL )

        self.m_listButtonSizer = wx.BoxSizer( wx.HORIZONTAL )

        self.m_deleteBtn = wx.Button( sbSizer1.GetStaticBox(), wx.ID_ANY, u"Delete", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_listButtonSizer.Add( self.m_deleteBtn, 0, wx.ALL, 5 )

        self.m_alignBtn = wx.Button( sbSizer1.GetStaticBox(), wx.ID_ANY, u"Align", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_listButtonSizer.Add( self.m_alignBtn, 0, wx.ALL, 5 )

        self.m_normalizeBtn = wx.Button( sbSizer1.GetStaticBox(), wx.ID_ANY, u"Normalize", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_listButtonSizer.Add( self.m_normalizeBtn, 0, wx.ALL, 5 )

        self.m_fadeOutBtn = wx.Button( sbSizer1.GetStaticBox(), wx.ID_ANY, u"Fade out", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_listButtonSizer.Add( self.m_fadeOutBtn, 0, wx.ALL, 5 )


        sbSizer1.Add( self.m_listButtonSizer, 0, wx.ALL|wx.EXPAND, 5 )

        self.m_listCtrl = wx.ListCtrl( sbSizer1.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LC_REPORT )
        sbSizer1.Add( self.m_listCtrl, 1, wx.ALL|wx.EXPAND, 5 )


        self.SetSizer( sbSizer1 )
        self.Layout()

        # Connect Events
        self.m_deleteBtn.Bind( wx.EVT_BUTTON, self.OnDeleteTracks )
        self.m_alignBtn.Bind( wx.EVT_BUTTON, self.OnAlign )
        self.m_normalizeBtn.Bind( wx.EVT_BUTTON, self.OnNormalize )
        self.m_fadeOutBtn.Bind( wx.EVT_BUTTON, self.OnFadeOut )
        self.m_listCtrl.Bind( wx.EVT_LIST_COL_END_DRAG, self.OnListHeaderResized )
        self.m_listCtrl.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.OnListSelectionChanged )
        self.m_listCtrl.Bind( wx.EVT_LIST_ITEM_SELECTED, self.OnListSelectionChanged )
        self.m_listCtrl.Bind( wx.EVT_RIGHT_DOWN, self.OnListRightDown )
        self.m_listCtrl.Bind( wx.EVT_UPDATE_UI, self.OnListUpdateUI )

    def __del__( self ):
        pass


    # Virtual event handlers, overide them in your derived class
    def OnDeleteTracks( self, event ):
        event.Skip()

    def OnAlign( self, event ):
        event.Skip()

    def OnNormalize( self, event ):
        event.Skip()

    def OnFadeOut( self, event ):
        event.Skip()

    def OnListHeaderResized( self, event ):
        event.Skip()

    def OnListSelectionChanged( self, event ):
        event.Skip()


    def OnListRightDown( self, event ):
        event.Skip()

    def OnListUpdateUI( self, event ):
        event.Skip()


###########################################################################
## Class LayoutPanel
###########################################################################

class LayoutPanel ( wx.Panel ):

    def __init__( self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.TAB_TRAVERSAL, name = wx.EmptyString ):
        wx.Panel.__init__ ( self, parent, id = id, pos = pos, size = size, style = style, name = name )

        self.m_sizer = wx.StaticBoxSizer( wx.StaticBox( self, wx.ID_ANY, u"Layout" ), wx.HORIZONTAL )

        bSizer7 = wx.BoxSizer( wx.VERTICAL )

        self.m_staticText4 = wx.StaticText( self.m_sizer.GetStaticBox(), wx.ID_ANY, u"Video Size (width x height)", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText4.Wrap( -1 )

        bSizer7.Add( self.m_staticText4, 0, wx.ALL, 5 )

        m_videoSizeChoices = [ u"1280x720 (16:9)", u"1920x1080 (16:9)", u"2560x1440 (16:9)" ]
        self.m_videoSize = wx.ComboBox( self.m_sizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, m_videoSizeChoices, 0 )
        self.m_videoSize.SetSelection( 1 )
        bSizer7.Add( self.m_videoSize, 0, wx.ALL, 5 )


        self.m_sizer.Add( bSizer7, 0, wx.EXPAND, 5 )


        self.SetSizer( self.m_sizer )
        self.Layout()

        # Connect Events
        self.m_videoSize.Bind( wx.EVT_COMBOBOX, self.OnVideoSizeUpdated )
        self.m_videoSize.Bind( wx.EVT_KILL_FOCUS, self.OnVideoSizeUpdated )

    def __del__( self ):
        pass


    # Virtual event handlers, overide them in your derived class
    def OnVideoSizeUpdated( self, event ):
        event.Skip()



###########################################################################
## Class LayoutDialog
###########################################################################

class LayoutDialog ( wx.Dialog ):

    def __init__( self, parent ):
        wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Advanced Layout", pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.DEFAULT_DIALOG_STYLE )

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

        bSizer4 = wx.BoxSizer( wx.VERTICAL )

        self.m_panel1 = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        fgSizer1 = wx.FlexGridSizer( 2, 3, 0, 0 )
        fgSizer1.AddGrowableRow( 0 )
        fgSizer1.SetFlexibleDirection( wx.BOTH )
        fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

        self.m_layoutCropSlider = wx.Slider( self.m_panel1, wx.ID_ANY, 0, 0, 100, wx.DefaultPosition, wx.Size( -1,-1 ), wx.SL_INVERSE|wx.SL_VERTICAL )
        fgSizer1.Add( self.m_layoutCropSlider, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 5 )

        self.m_layoutIterationsSlider = wx.Slider( self.m_panel1, wx.ID_ANY, 40, 1, 100, wx.DefaultPosition, wx.DefaultSize, wx.SL_INVERSE|wx.SL_VERTICAL )
        fgSizer1.Add( self.m_layoutIterationsSlider, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 5 )

        self.m_layoutTemperatureSlider = wx.Slider( self.m_panel1, wx.ID_ANY, 40, 1, 100, wx.DefaultPosition, wx.DefaultSize, wx.SL_INVERSE|wx.SL_VERTICAL )
        fgSizer1.Add( self.m_layoutTemperatureSlider, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 5 )

        self.m_layoutCropLabel = wx.StaticText( self.m_panel1, wx.ID_ANY, u"Crop\nTolerance", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTER_HORIZONTAL )
        self.m_layoutCropLabel.Wrap( -1 )

        self.m_layoutCropLabel.SetToolTip( u"Higher = more cropping allowed, more compact layout\nLower = less cropping allowed, less compact layout" )

        fgSizer1.Add( self.m_layoutCropLabel, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5 )

        self.m_layoutIterationsLabel = wx.StaticText( self.m_panel1, wx.ID_ANY, u"Iterations", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTER_HORIZONTAL )
        self.m_layoutIterationsLabel.Wrap( -1 )

        self.m_layoutIterationsLabel.SetToolTip( u"Number of layout iterations to run" )

        fgSizer1.Add( self.m_layoutIterationsLabel, 0, wx.ALL, 5 )

        self.m_layoutTemperatureLabel = wx.StaticText( self.m_panel1, wx.ID_ANY, u"Temperature", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTER_HORIZONTAL )
        self.m_layoutTemperatureLabel.Wrap( -1 )

        self.m_layoutTemperatureLabel.SetToolTip( u"Higher = more initial randomization\nLower = more conservative layouts" )

        fgSizer1.Add( self.m_layoutTemperatureLabel, 0, wx.ALL, 5 )


        self.m_panel1.SetSizer( fgSizer1 )
        self.m_panel1.Layout()
        fgSizer1.Fit( self.m_panel1 )
        bSizer4.Add( self.m_panel1, 1, wx.EXPAND |wx.ALL, 5 )


        self.SetSizer( bSizer4 )
        self.Layout()
        bSizer4.Fit( self )

        self.Centre( wx.BOTH )

        # Connect Events
        self.m_layoutIterationsSlider.Bind( wx.EVT_COMMAND_SCROLL_THUMBTRACK, self.OnLayoutIterationsChanged )

    def __del__( self ):
        pass


    # Virtual event handlers, overide them in your derived class
    def OnLayoutIterationsChanged( self, event ):
        event.Skip()


###########################################################################
## Class LogDialog
###########################################################################

class LogDialog ( wx.Dialog ):

    def __init__( self, parent ):
        wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Log", pos = wx.DefaultPosition, size = wx.Size( 455,280 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

        bSizer5 = wx.BoxSizer( wx.VERTICAL )

        self.m_text = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL|wx.TE_DONTWRAP|wx.TE_MULTILINE|wx.TE_READONLY )
        self.m_text.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString ) )

        bSizer5.Add( self.m_text, 1, wx.ALL|wx.EXPAND, 5 )


        self.SetSizer( bSizer5 )
        self.Layout()

        self.Centre( wx.BOTH )

    def __del__( self ):
        pass



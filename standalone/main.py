from app.App import App

# Hidden imports for pyinstaller
import scipy.special.cython_special

if __name__ == '__main__':
    app = App()
    app.MainLoop()

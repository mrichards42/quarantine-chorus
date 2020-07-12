import app.popen  # Popen monkey patch # noqa F401
from app.App import App

if __name__ == '__main__':
    app = App()
    app.MainLoop()

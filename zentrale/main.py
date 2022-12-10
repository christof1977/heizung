from app import app, steuerung
import threading

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run().start())
    steuerung.run()


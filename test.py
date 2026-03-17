from db import runde_hinzufuegen, get_fastest

if __name__ == '__main__':
    runde_hinzufuegen("1001")
    print(get_fastest())
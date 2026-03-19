import requests


def safe_get_json(url):
    """Sicheres GET mit JSON-Parsing."""
    try:
        r = requests.get(url, verify=False, timeout=1.5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"⚠️ Fehler bei Request {url}: {e}")
        return None


if __name__ == '__main__':
    while True:
        scan_all = safe_get_json(f"https://192.168.178.40:5000/api/scan_status_all/")
        print(scan_all)
        scanner = scan_all.get("scanner")
        print(scanner)
        for i in range(1,4):
            print(scanner[str(i)])
            if scanner[str(i)]:
                print("on: "+str(i))

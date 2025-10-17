
<augment_code_snippet mode="EXCERPT">
````python
import urllib.request

def check_llama_health(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/health") as r:
            return r.status == 200
    except Exception:
        return False
````
</augment_code_snippet>


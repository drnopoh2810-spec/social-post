"""إصلاح سريع لـ PythonAnywhere — git pull + reload"""
import requests, time

username = input("PythonAnywhere username: ").strip()
token    = input("API Token: ").strip()
headers  = {"Authorization": f"Token {token}"}
app_dir  = f"/home/{username}/social-post"

def console_run(cmd, wait=30):
    r = requests.post(
        f"https://www.pythonanywhere.com/api/v0/user/{username}/consoles/",
        headers=headers,
        data={"executable": "bash", "working_directory": f"/home/{username}"}
    )
    if r.status_code not in (200, 201):
        print(f"Console error: {r.text[:100]}"); return ""
    try:
        cid = r.json()["id"]
    except Exception:
        print(f"Console parse error: {r.text[:100]}"); return ""
    time.sleep(3)
    requests.post(
        f"https://www.pythonanywhere.com/api/v0/user/{username}/consoles/{cid}/send_input/",
        headers=headers, data={"input": cmd + "\n"}
    )
    time.sleep(wait)
    out = requests.get(
        f"https://www.pythonanywhere.com/api/v0/user/{username}/consoles/{cid}/get_latest_output/",
        headers=headers
    )
    requests.delete(
        f"https://www.pythonanywhere.com/api/v0/user/{username}/consoles/{cid}/",
        headers=headers
    )
    try:
        return out.json().get("output", "")
    except Exception:
        return ""

print("\n1. git pull...")
out = console_run(f"cd {app_dir} && git pull origin main && echo GIT_OK", wait=30)
print("✅ git pull OK" if "GIT_OK" in out else f"⚠️ {out[-200:]}")

print("\n2. تثبيت المتطلبات...")
out = console_run(
    f"cd {app_dir} && source venv/bin/activate && pip install -q -r requirements.txt && echo PIP_OK",
    wait=90
)
print("✅ pip OK" if "PIP_OK" in out else f"⚠️ {out[-200:]}")

print("\n3. Reload webapp...")
domain = f"{username}.pythonanywhere.com"
r = requests.post(
    f"https://www.pythonanywhere.com/api/v0/user/{username}/webapps/{domain}/reload/",
    headers=headers
)
print("✅ Reload OK" if r.ok else f"⚠️ {r.text[:100]}")

print(f"\n🌐 https://{domain}")

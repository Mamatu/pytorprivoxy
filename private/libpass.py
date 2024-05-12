_password = "1234567890"

def get_password():
    global _password
    return _password

def remove_whitespaces(txt):
    import re
    pattern = re.compile(r'\s+')
    txt = re.sub(pattern, '', txt)
    txt = txt.strip()
    return txt

def get_hashed_password(remove_prefix = False):
    _pass = get_password()
    print(_pass)
    import subprocess
    process = subprocess.Popen(["tor", "--hash-password", f"\"{_pass}\""], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    _hashed_pass = process.stdout.readline()
    process.stdout.close()
    process.stderr.close()
    from private import libterminate
    libterminate.terminate_subprocess(process)
    _hashed_pass = _hashed_pass.decode("utf-8")
    _hashed_pass = remove_whitespaces(_hashed_pass)
    if remove_prefix:
        idx = _hashed_pass.index(":")
        _hashed_pass = _hashed_pass[idx+1:]
    print(_hashed_pass)
    return _hashed_pass

#def load_password_from_file(filepath):
#    with open(filepath, "r") as f:
#        _pass = f.read()
#        global _passowrd
#        _password = remove_whitespaces(_pass)
